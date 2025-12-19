"""Management command to migrate files from MEDIA_ROOT to PRIVATE_MEDIA_ROOT."""

from __future__ import annotations

import shutil
from pathlib import Path

import djclick as click
from django.conf import settings
from django_simple_dms.models import Document

from krm3.core.models import Contract
from krm3.core.models.missions import Expense


@click.command()
@click.option(
    '--dry-run',
    is_flag=True,
    default=False,
    help='Show what would be migrated without actually moving files',
    show_default=True,
)
@click.option(
    '--model',
    type=click.Choice(['all', 'document', 'expense', 'contract'], case_sensitive=False),
    default='all',
    help='Specify which model to migrate',
    show_default=True,
)
@click.option(
    '--skip-missing',
    is_flag=True,
    default=False,
    help='Skip files that do not exist in source location',
    show_default=True,
)
def command(dry_run: bool, model: str, skip_missing: bool) -> None:
    """Migrate files from MEDIA_ROOT to PRIVATE_MEDIA_ROOT.

    This command copies files from the public MEDIA_ROOT to the private
    PRIVATE_MEDIA_ROOT for models with FileFields:
    - Document (django_simple_dms)
    - Expense (image field)
    - Contract (document field)

    Files are COPIED (not moved) to preserve data integrity and allow rollback.
    The relative file paths in the database remain unchanged.
    Files maintain the same directory structure in PRIVATE_MEDIA_ROOT.

    Example:
        Source:      MEDIA_ROOT/missions/expenses/R1/M2/receipt.jpg
        Destination: PRIVATE_MEDIA_ROOT/missions/expenses/R1/M2/receipt.jpg
        DB path:     missions/expenses/R1/M2/receipt.jpg (unchanged)

    """
    media_root = Path(settings.MEDIA_ROOT)
    private_media_root = Path(settings.PRIVATE_MEDIA_ROOT)

    click.secho('\n=== File Migration to Private Media ===\n', fg='cyan', bold=True)
    click.echo(f'Source (MEDIA_ROOT):      {media_root}')
    click.echo(f'Destination (PRIVATE):    {private_media_root}')
    click.echo(f'Dry run:                  {dry_run}')
    click.echo(f'Skip missing:             {skip_missing}')
    click.echo(f'Model filter:             {model}\n')

    if dry_run:
        click.secho('DRY RUN MODE - No files will be modified\n', fg='yellow', bold=True)

    stats = {
        'total': 0,
        'copied': 0,
        'skipped': 0,
        'errors': 0,
        'already_exists': 0,
    }

    # Migrate each model
    if model in ('all', 'document'):
        click.secho('\n--- Migrating Document files (django_simple_dms) ---', fg='blue', bold=True)
        _migrate_documents(media_root, private_media_root, dry_run, skip_missing, stats)

    if model in ('all', 'expense'):
        click.secho('\n--- Migrating Expense images ---', fg='blue', bold=True)
        _migrate_expenses(media_root, private_media_root, dry_run, skip_missing, stats)

    if model in ('all', 'contract'):
        click.secho('\n--- Migrating Contract documents ---', fg='blue', bold=True)
        _migrate_contracts(media_root, private_media_root, dry_run, skip_missing, stats)

    # Print summary
    click.secho('\n=== Migration Summary ===', fg='cyan', bold=True)
    click.echo(f'Total files processed:    {stats["total"]}')
    click.secho(f'Successfully copied:      {stats["copied"]}', fg='green')
    click.secho(f'Already exist:            {stats["already_exists"]}', fg='yellow')
    click.secho(f'Skipped (missing):        {stats["skipped"]}', fg='yellow')
    if stats['errors'] > 0:
        click.secho(f'Errors:                   {stats["errors"]}', fg='red', bold=True)
    else:
        click.secho(f'Errors:                   {stats["errors"]}', fg='green')

    if dry_run:
        click.secho('\nDRY RUN COMPLETE - No files were actually modified', fg='yellow', bold=True)
    else:
        click.secho('\nMIGRATION COMPLETE', fg='green', bold=True)
        click.echo('\nNext steps:')
        click.echo('1. Update models to use PrivateMediaStorage backend')
        click.echo('2. Create protected views for Expense and Contract models')
        click.echo('3. Update frontend to use protected URLs')
        click.echo('4. Test file access through protected endpoints')


def _migrate_documents(
    media_root: Path, private_media_root: Path, dry_run: bool, skip_missing: bool, stats: dict
) -> None:
    """Migrate Document model files."""
    documents = Document.objects.all()
    count = documents.count()

    if count == 0:
        click.echo('No documents found.')
        return

    click.echo(f'Found {count} documents to process...\n')

    with click.progressbar(documents, label='Migrating documents', show_pos=True) as bar:
        for doc in bar:
            stats['total'] += 1

            if not doc.document:
                click.echo(f'  [SKIP] Document {doc.pk}: No file attached')
                stats['skipped'] += 1
                continue

            # Keep the same relative path
            relative_path = doc.document.name
            source_path = media_root / relative_path
            dest_path = private_media_root / relative_path

            _copy_file(relative_path, source_path, dest_path, dry_run, skip_missing, stats, f'Document {doc.pk}')


def _migrate_expenses(
    media_root: Path, private_media_root: Path, dry_run: bool, skip_missing: bool, stats: dict
) -> None:
    """Migrate Expense model files."""
    expenses = Expense.objects.exclude(image='')
    count = expenses.count()

    if count == 0:
        click.echo('No expenses with images found.')
        return

    click.echo(f'Found {count} expenses with images to process...\n')

    with click.progressbar(expenses, label='Migrating expense images', show_pos=True) as bar:
        for expense in bar:
            stats['total'] += 1

            # Keep the same relative path
            relative_path = expense.image.name
            source_path = media_root / relative_path
            dest_path = private_media_root / relative_path

            _copy_file(relative_path, source_path, dest_path, dry_run, skip_missing, stats, f'Expense {expense.pk}')


def _migrate_contracts(
    media_root: Path, private_media_root: Path, dry_run: bool, skip_missing: bool, stats: dict
) -> None:
    """Migrate Contract model files."""
    contracts = Contract.objects.exclude(document='')
    count = contracts.count()

    if count == 0:
        click.echo('No contracts with documents found.')
        return

    click.echo(f'Found {count} contracts with documents to process...\n')

    with click.progressbar(contracts, label='Migrating contract documents', show_pos=True) as bar:
        for contract in bar:
            stats['total'] += 1

            # Keep the same relative path
            relative_path = contract.document.name
            source_path = media_root / relative_path
            dest_path = private_media_root / relative_path

            _copy_file(
                relative_path, source_path, dest_path, dry_run, skip_missing, stats, f'Contract {contract.pk}'
            )


def _copy_file(  # noqa: PLR0913
    relative_path: str,
    source_path: Path,
    dest_path: Path,
    dry_run: bool,
    skip_missing: bool,
    stats: dict,
    label: str,
) -> None:
    """Copy a single file from source to destination preserving relative path.

    Args:
        relative_path: Relative path for display (e.g., 'missions/expenses/R1/M2/file.jpg')
        source_path: Absolute source path
        dest_path: Absolute destination path
        dry_run: If True, only simulate the copy
        skip_missing: If True, skip missing files without error
        stats: Statistics dictionary to update
        label: Label for logging (e.g., "Expense 123")

    """
    # Check if source exists
    if not source_path.exists():
        if skip_missing:
            click.echo(f'  [SKIP] {label}: Source file does not exist: {relative_path}')
            stats['skipped'] += 1
        else:
            click.secho(f'  [ERROR] {label}: Source file not found: {relative_path}', fg='red')
            stats['errors'] += 1
        return

    # Check if destination already exists
    if dest_path.exists():
        # Compare file sizes to see if they're the same
        source_size = source_path.stat().st_size
        dest_size = dest_path.stat().st_size

        if source_size == dest_size:
            # Files appear to be the same
            stats['already_exists'] += 1
            # Don't print for each file to keep output clean with progressbar
        else:
            click.secho(
                f'  [WARN] {label}: Destination exists but different size '
                f'(source: {source_size}, dest: {dest_size}): {relative_path}',
                fg='yellow',
            )
            stats['already_exists'] += 1
        return

    # Copy the file
    if dry_run:
        # Don't print for each file in dry-run to keep output clean
        stats['copied'] += 1
    else:
        try:
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file (copy2 preserves metadata like timestamps)
            shutil.copy2(source_path, dest_path)

            stats['copied'] += 1
        except OSError as e:
            click.secho(f'  [ERROR] {label}: Failed to copy {relative_path}: {e}', fg='red')
            stats['errors'] += 1
