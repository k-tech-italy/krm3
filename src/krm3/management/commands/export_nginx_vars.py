"""Export Django configuration as shell variables for nginx templating."""

from __future__ import annotations

import tempfile
from pathlib import Path

import djclick as click
from django.conf import settings
from django.urls import get_resolver


def should_exclude_path(path: str, static_url_path: str = 'static', media_url_path: str = 'media') -> bool:
    """Check if a path should be excluded from Django routing."""
    # Remove leading/trailing slashes and backslash-escapes for comparison
    path_clean = path.strip('/').replace('\\', '')

    # Exclude empty paths
    if not path_clean:
        return True

    # Exclude static and media URL paths
    if path_clean in (static_url_path, media_url_path):
        return True

    # Exclude paths starting with a dot (regex artifacts)
    if path_clean.startswith('.'):
        return True

    # Exclude PWA-related files that should be served as static files
    # These paths exist in Django URLs but we want nginx to serve them from static/
    pwa_files = {
        'manifest.json',
        'serviceworker.js',
        'offline',
        'offline.html',
    }

    # Check if the cleaned path matches any PWA file
    if path_clean in pwa_files:
        return True

    # Also check if the path ends with these filenames (e.g., /path/to/manifest.json)
    return any(path_clean.endswith(pwa_file) for pwa_file in pwa_files)


def extract_first_level_paths(urlpatterns: list, prefix: str = '') -> set[str]:
    """Extract first-level URL patterns from Django URL configuration.

    Args:
        urlpatterns: Django URL patterns
        prefix: Current URL prefix for nested patterns

    Returns:
        Set of first-level URL paths

    """
    paths = set()

    for pattern in urlpatterns:
        # Get the pattern string
        pattern_str = str(pattern.pattern)

        # Skip empty patterns and regex patterns starting with ^
        if not pattern_str or pattern_str == '^':
            # If this is an include, process nested patterns
            if hasattr(pattern, 'url_patterns'):
                paths.update(extract_first_level_paths(pattern.url_patterns, prefix))
            continue

        # Remove leading ^ and trailing $ from regex patterns
        pattern_str = pattern_str.lstrip('^').rstrip('$')

        # Build full path with prefix
        full_path = f'{prefix}/{pattern_str}'.replace('//', '/')

        # Extract first-level path (everything before the first dynamic part)
        # Handle both path() style and re_path() style patterns
        if '/' in full_path:
            first_level = full_path.split('/')[0] if not full_path.startswith('/') else '/' + full_path.split('/')[1]
        else:
            first_level = full_path

        # Clean up the path
        first_level = first_level.split('<')[0].split('(')[0].rstrip('/')

        # Skip paths that are just dots or special regex patterns
        if first_level and first_level != '/' and not first_level.startswith('.'):
            paths.add(first_level)

        # Process nested URL includes
        if hasattr(pattern, 'url_patterns'):
            if first_level:
                paths.update(extract_first_level_paths(pattern.url_patterns, first_level))
            else:
                paths.update(extract_first_level_paths(pattern.url_patterns, prefix))

    return paths


def export_nginx_vars(output_path: str | None = None) -> tuple[str, list[str]]:
    """Export Django configuration as shell environment variables.

    Args:
        output_path: Path where to write the shell script with exported variables

    Returns:
        tuple: (shell_script_content, filtered_django_paths)
            - shell_script_content: Generated shell script with export statements
            - filtered_django_paths: Sorted list of Django paths that will be proxied

    """
    # Get URL resolver
    resolver = get_resolver()

    # Extract first-level paths
    django_paths = extract_first_level_paths(resolver.url_patterns)

    # Get static and media URLs to exclude from Django routing
    static_url_path = settings.STATIC_URL.strip('/')
    media_url_path = settings.MEDIA_URL.strip('/')

    # Filter out paths that should be served as static files
    filtered_paths = sorted([p for p in django_paths if not should_exclude_path(p, static_url_path, media_url_path)])

    # Get URLs from Django settings
    static_url = settings.STATIC_URL.rstrip('/')
    media_url = settings.MEDIA_URL.rstrip('/')
    private_media_url = settings.PRIVATE_MEDIA_URL.rstrip('/')

    # Build nginx location pattern for Django routes
    # Escape special nginx characters and format as regex alternatives
    escaped_paths = []
    for p in filtered_paths:
        # Escape special nginx regex characters
        escaped = p.replace('.', r'\.')
        # Remove leading slash if present (we'll add it in the pattern)
        escaped = escaped.lstrip('/')
        # Only add non-empty paths
        if escaped:
            escaped_paths.append(escaped)

    # Create regex pattern: /path/.* for each route
    # If no paths, create a pattern that will never match
    if escaped_paths:
        django_routes_pattern = '|'.join([f'/{p}/.*' for p in escaped_paths])
    else:
        # No Django routes to proxy - use a pattern that never matches
        django_routes_pattern = '^/this-path-will-never-match-anything$'

    # Generate shell script with exported variables
    # Use single quotes to prevent shell expansion and escape single quotes in content
    shell_script = f"""#!/bin/bash
# Auto-generated environment variables for nginx configuration
# Generated by: django-admin export_nginx_vars
# Source this file to load variables into your shell environment

export DJANGO_ROUTES_PATTERN='{django_routes_pattern.replace("'", "'\"'\"'")}'
export STATIC_URL='{static_url.replace("'", "'\"'\"'")}'
export MEDIA_URL='{media_url.replace("'", "'\"'\"'")}'
export PRIVATE_MEDIA_URL='{private_media_url.replace("'", "'\"'\"'")}'
"""

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(shell_script)
        # Make the file executable
        output_file.chmod(0o755)

    return shell_script, filtered_paths


@click.command()
@click.option(
    '--output',
    '-o',
    default=None,
    help='Output path for shell script with exported variables (defaults to secure temp file)',
    show_default=True,
)
@click.option(
    '--dry-run',
    is_flag=True,
    default=False,
    help='Print shell script to stdout instead of writing to file',
    show_default=True,
)
@click.option(
    '--verbose',
    is_flag=True,
    default=False,
    help='Enable verbose output',
    show_default=True,
)
def command(output: str | None, dry_run: bool, verbose: bool) -> None:
    """Export Django configuration as shell variables for nginx templating."""
    try:
        # Determine output path
        if dry_run:
            output_path = None
        elif output:
            output_path = output
        else:
            # Use secure temporary file with proper permissions
            # Create with delete=False so we can return the path
            # We intentionally don't use a context manager because we need the file to persist
            temp_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
                mode='w',
                prefix='nginx_env_',
                suffix='.sh',
                delete=False,
                dir=tempfile.gettempdir()
            )
            output_path = temp_file.name
            temp_file.close()

        # Export nginx variables and get filtered paths
        shell_script, filtered_paths = export_nginx_vars(output_path=output_path)

        if verbose and not dry_run:
            click.secho('Detected Django routes (will be proxied to Django):', fg='green', err=True)
            for path in filtered_paths:
                # Remove leading slash for display since we add it in the format
                display_path = path.lstrip('/')
                click.echo(f'  - /{display_path}/', err=True)

        if dry_run:
            click.echo(shell_script)
        else:
            # Print the output path to stdout for scripts to capture
            # All other output goes to stderr when verbose
            click.echo(output_path)
            if verbose:
                click.secho(f'Generated shell variables at: {output_path}', fg='green', err=True)
    except Exception as e:
        click.secho(f'Error exporting nginx variables: {e}', fg='red')
        raise
