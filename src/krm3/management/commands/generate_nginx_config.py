"""Generate nginx configuration based on Django URL patterns."""

from __future__ import annotations

from pathlib import Path

import djclick as click
from django.conf import settings
from django.urls import get_resolver

from krm3.config.environ import env


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


def generate_nginx_config(output_path: str | None = None) -> str:
    """Generate nginx configuration file.

    Args:
        output_path: Path where to write the nginx config file

    Returns:
        str: Generated nginx configuration

    """
    # Get URL resolver
    resolver = get_resolver()

    # Extract first-level paths
    django_paths = extract_first_level_paths(resolver.url_patterns)

    # Get static and media URLs to exclude from Django routing
    static_url_path = settings.STATIC_URL.strip('/')
    media_url_path = settings.MEDIA_URL.strip('/')

    # Filter out paths that should be served as static files
    django_paths = sorted([p for p in django_paths if not should_exclude_path(p, static_url_path, media_url_path)])

    # Get paths from Django settings (which use environ with proper defaults)
    # Strip quotes that might be in the environment variables
    static_root = env.str('STATIC_ROOT').strip('"').strip("'")
    media_root = env.str('MEDIA_ROOT').strip('"').strip("'")
    private_media_root = env.str('PRIVATE_MEDIA_ROOT').strip('"').strip("'")
    static_url = settings.STATIC_URL.rstrip('/')
    media_url = settings.MEDIA_URL.rstrip('/')
    private_media_url = env.str('PRIVATE_MEDIA_URL').strip('"').strip("'").rstrip('/')

    # Build nginx location pattern for Django routes
    # Escape special nginx characters and format as regex alternatives
    escaped_paths = []
    for p in django_paths:
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

    # Generate nginx configuration
    config = f"""# Auto-generated nginx configuration for KRM3
# Generated by: django-admin generate_nginx_config
# Do not edit manually - changes will be overwritten

upstream django {{
    server 127.0.0.1:8000;
}}

server {{
    listen 80;
    server_name _;

    client_max_body_size 100M;

    # Logging
    access_log /var/log/nginx/krm3_access.log;
    error_log /var/log/nginx/krm3_error.log;

    # Static files
    location {static_url}/ {{
        alias {static_root}/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}

    # Media files
    location {media_url}/ {{
        alias {media_root}/;
        expires 7d;
        add_header Cache-Control "public";
    }}

    # Private media files (internal only - served via X-Accel-Redirect)
    location {private_media_url}/ {{
        internal;
        alias {private_media_root}/;
    }}

    # Django application routes (auto-detected)
    location ~ ^({django_routes_pattern})$ {{
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }}

    # Frontend SPA - serve index.html for all other routes
    location / {{
        root {static_root};
        index index.html;
        try_files $uri $uri/ /index.html =404;
    }}
}}
"""

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(config)

    return config


@click.command()
@click.option(
    '--output',
    '-o',
    default='/etc/nginx/sites-enabled/krm3.conf',
    help='Output path for nginx configuration file',
    show_default=True,
)
@click.option(
    '--dry-run',
    is_flag=True,
    default=False,
    help='Print configuration to stdout instead of writing to file',
    show_default=True,
)
@click.option(
    '--verbose',
    is_flag=True,
    default=False,
    help='Enable verbose output',
    show_default=True,
)
def command(output: str, dry_run: bool, verbose: bool) -> None:
    """Generate nginx configuration based on Django URL patterns."""
    try:
        config = generate_nginx_config(output_path=None if dry_run else output)

        if dry_run:
            click.echo(config)
        elif verbose:
            click.secho(f'Generated nginx configuration at: {output}', fg='green')

            # Show detected routes
            resolver = get_resolver()
            all_paths = extract_first_level_paths(resolver.url_patterns)

            # Get static and media URLs for filtering
            static_url_path = settings.STATIC_URL.strip('/')
            media_url_path = settings.MEDIA_URL.strip('/')

            filtered_paths = sorted(
                [p for p in all_paths if not should_exclude_path(p, static_url_path, media_url_path)]
            )

            click.echo('\nDetected Django routes (will be proxied to Django):')
            for path in filtered_paths:
                # Remove leading slash for display since we add it in the format
                display_path = path.lstrip('/')
                click.echo(f'  - /{display_path}/')
    except Exception as e:
        click.secho(f'Error generating nginx configuration: {e}', fg='red')
        raise
