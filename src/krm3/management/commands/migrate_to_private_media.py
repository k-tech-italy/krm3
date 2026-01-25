"""Management command to migrate media files to private media storage.

This command copies files from MEDIA_ROOT to PRIVATE_MEDIA_ROOT for models
that require protected media access via nginx X-Accel-Redirect.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import djclick as click
from django.conf import settings

from krm3.missions.media import CONTRACT_DOCUMENT_PREFIX, EXPENSES_IMAGE_PREFIX

logger = logging.getLogger(__name__)

# Directory prefixes to migrate (relative to MEDIA_ROOT)
PATHS_TO_MIGRATE = [
    EXPENSES_IMAGE_PREFIX,    # missions/expenses - Expense.image
    CONTRACT_DOCUMENT_PREFIX,  # contracts/documents - Contract.document
]


def copy_tree_with_logging(
    src: Path,
    dst: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[int, int, list[str]]:
    """Copy directory tree from src to dst with detailed logging.

    Args:
        src: Source directory path
        dst: Destination directory path
        dry_run: If True, only report what would be copied
        verbose: If True, log each file copied

    Returns:
        Tuple of (files_copied, files_skipped, errors)

    """
    files_copied = 0
    files_skipped = 0
    errors: list[str] = []

    if not src.exists():
        logger.warning(f'Source directory does not exist: {src}')
        return files_copied, files_skipped, errors

    for src_file in src.rglob('*'):
        if src_file.is_dir():
            continue

        relative_path = src_file.relative_to(src)
        dst_file = dst / relative_path

        if dst_file.exists():
            files_skipped += 1
            if verbose:
                logger.debug(f'Skipped (exists): {relative_path}')
            continue

        if dry_run:
            files_copied += 1
            if verbose:
                click.echo(f'  Would copy: {relative_path}')
            continue

        try:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            files_copied += 1
            if verbose:
                logger.info(f'Copied: {relative_path}')
        except OSError as e:
            error_msg = f'Failed to copy {relative_path}: {e}'
            errors.append(error_msg)
            logger.error(error_msg)

    return files_copied, files_skipped, errors


@click.command()
@click.option(
    '--dry-run',
    is_flag=True,
    default=False,
    help='Show what would be copied without actually copying files.',
)
@click.option(
    '--verbose',
    is_flag=True,
    default=False,
    help='Show detailed output for each file.',
)
def command(dry_run: bool, verbose: bool) -> None:
    """Migrate media files to private media storage.

    Copies files from MEDIA_ROOT to PRIVATE_MEDIA_ROOT for protected media
    serving via nginx X-Accel-Redirect. This command is idempotent - files
    that already exist in the destination are skipped.

    Migrated paths:
    - missions/expenses (Expense.image)
    - contracts/documents (Contract.document)
    """
    # Configure logging based on verbosity
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    media_root = Path(settings.MEDIA_ROOT)
    private_media_root = Path(settings.PRIVATE_MEDIA_ROOT)

    click.echo(f'Source:      {media_root}')
    click.echo(f'Destination: {private_media_root}')

    if dry_run:
        click.echo('\n[DRY RUN] No files will be copied.\n')

    total_copied = 0
    total_skipped = 0
    total_errors: list[str] = []

    for path_prefix in PATHS_TO_MIGRATE:
        src_path = media_root / path_prefix
        dst_path = private_media_root / path_prefix

        click.echo(f'Processing: {path_prefix}/')

        if not src_path.exists():
            click.echo('  Source directory not found, skipping.')
            continue

        copied, skipped, errors = copy_tree_with_logging(
            src_path,
            dst_path,
            dry_run=dry_run,
            verbose=verbose,
        )

        total_copied += copied
        total_skipped += skipped
        total_errors.extend(errors)

        copy_action = 'Would copy' if dry_run else 'Copied'
        skip_action = 'Would skip' if dry_run else 'Skipped'
        click.echo(f'  {copy_action}: {copied} files, {skip_action}: {skipped} files')

    click.echo('')
    click.echo('=' * 50)

    if dry_run:
        click.echo(f'[DRY RUN] Would copy {total_copied} files, Would skip {total_skipped} files.')
    else:
        click.echo(f'Copied {total_copied} files, Skipped {total_skipped} files.')

    if total_errors:
        click.echo(f'\nErrors ({len(total_errors)}):')
        for error in total_errors:
            click.echo(f'  - {error}')
        raise SystemExit(1)

    click.echo('\nDone.')
