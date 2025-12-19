# Migrate to Private Media Command

This document explains how to use the `migrate_to_private_media` management command to copy files from public `MEDIA_ROOT` to private `PRIVATE_MEDIA_ROOT`.

## Overview

The command copies files for these models:
- **Document** (django_simple_dms) - `document` FileField
- **Expense** - `image` FileField
- **Contract** - `document` FileField

Files are **COPIED** (not moved) to preserve data integrity and allow rollback if needed.

## Key Points

### File Paths Remain Unchanged

The relative file paths stored in the database **do not change**. Only the physical location changes:

```
Before:
├── Database: missions/expenses/R1/M2/receipt.jpg
└── File location: MEDIA_ROOT/missions/expenses/R1/M2/receipt.jpg

After:
├── Database: missions/expenses/R1/M2/receipt.jpg (UNCHANGED)
├── Old location: MEDIA_ROOT/missions/expenses/R1/M2/receipt.jpg (still exists)
└── New location: PRIVATE_MEDIA_ROOT/missions/expenses/R1/M2/receipt.jpg (copied)
```

### Directory Structure Preserved

The command maintains the same directory structure in `PRIVATE_MEDIA_ROOT`:

```
MEDIA_ROOT/
├── missions/expenses/R1/M2/receipt.jpg
├── contracts/documents/R5/C10/contract.pdf
└── documents/2025/01/19/invoice.pdf

PRIVATE_MEDIA_ROOT/  (after migration)
├── missions/expenses/R1/M2/receipt.jpg
├── contracts/documents/R5/C10/contract.pdf
└── documents/2025/01/19/invoice.pdf
```

## Usage

### 1. Dry Run (Recommended First)

Always run with `--dry-run` first to see what will be migrated:

```bash
# See what would be migrated for all models
django-admin migrate_to_private_media --dry-run

# See what would be migrated for specific model
django-admin migrate_to_private_media --dry-run --model=expense
django-admin migrate_to_private_media --dry-run --model=contract
django-admin migrate_to_private_media --dry-run --model=document
```

### 2. Actual Migration

Once you're satisfied with the dry-run output:

```bash
# Migrate all models
django-admin migrate_to_private_media

# Migrate specific model only
django-admin migrate_to_private_media --model=expense
```

### 3. Handle Missing Files

If some source files are missing, you can skip them:

```bash
# Skip missing files without errors
django-admin migrate_to_private_media --skip-missing
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Show what would be migrated without actually copying files | `False` |
| `--model` | Specify which model to migrate: `all`, `document`, `expense`, `contract` | `all` |
| `--skip-missing` | Skip files that don't exist in source location | `False` |

## Example Sessions

### Example 1: Full Migration

```bash
$ django-admin migrate_to_private_media

=== File Migration to Private Media ===

Source (MEDIA_ROOT):      /var/lib/krm3/media
Destination (PRIVATE):    /var/lib/krm3/private-media
Dry run:                  False
Skip missing:             False
Model filter:             all


--- Migrating Document files (django_simple_dms) ---
Found 150 documents to process...

Migrating documents  [####################################]  150/150

--- Migrating Expense images ---
Found 320 expenses with images to process...

Migrating expense images  [####################################]  320/320

--- Migrating Contract documents ---
Found 45 contracts with documents to process...

Migrating contract documents  [####################################]  45/45

=== Migration Summary ===
Total files processed:    515
Successfully copied:      500
Already exist:            10
Skipped (missing):        5
Errors:                   0

MIGRATION COMPLETE

Next steps:
1. Update models to use PrivateMediaStorage backend
2. Create protected views for Expense and Contract models
3. Update frontend to use protected URLs
4. Test file access through protected endpoints
```

### Example 2: Dry Run for Single Model

```bash
$ django-admin migrate_to_private_media --dry-run --model=expense

=== File Migration to Private Media ===

Source (MEDIA_ROOT):      /home/user/krm3/~media
Destination (PRIVATE):    /home/user/krm3/~private-media
Dry run:                  True
Skip missing:             False
Model filter:             expense

DRY RUN MODE - No files will be modified


--- Migrating Expense images ---
Found 320 expenses with images to process...

Migrating expense images  [####################################]  320/320

=== Migration Summary ===
Total files processed:    320
Successfully copied:      320
Already exist:            0
Skipped (missing):        0
Errors:                   0

DRY RUN COMPLETE - No files were actually modified
```

### Example 3: Skip Missing Files

```bash
$ django-admin migrate_to_private_media --skip-missing

=== File Migration to Private Media ===

Source (MEDIA_ROOT):      /var/lib/krm3/media
Destination (PRIVATE):    /var/lib/krm3/private-media
Dry run:                  False
Skip missing:             True
Model filter:             all

  [SKIP] Document 42: Source file does not exist: documents/2024/03/15/deleted.pdf
  [SKIP] Expense 156: Source file does not exist: missions/expenses/R5/M23/missing.jpg

=== Migration Summary ===
Total files processed:    515
Successfully copied:      500
Already exist:            10
Skipped (missing):        5
Errors:                   0

MIGRATION COMPLETE
```

## Post-Migration Steps

After running the migration command:

### 1. Verify Files Were Copied

```bash
# Check that files exist in private media
ls -la $PRIVATE_MEDIA_ROOT/missions/expenses/
ls -la $PRIVATE_MEDIA_ROOT/contracts/documents/
ls -la $PRIVATE_MEDIA_ROOT/documents/
```

### 2. Update Models to Use Private Storage

For **new files only**, you can configure models to use `PrivateMediaStorage`:

```python
from krm3.core.storage import PrivateMediaStorage

class Expense(models.Model):
    # This will make NEW uploads go to private storage
    image = models.FileField(
        upload_to=mission_directory_path,
        storage=PrivateMediaStorage(),  # Add this
        null=True,
        blank=True
    )
```

**Note:** This only affects NEW files. Existing files will continue to work with their current paths.

### 3. Create Protected Views

Create authorization views similar to `ProtectedDocumentView` for Expense and Contract models.

### 4. Test Access

Test that files are accessible through:
- Protected Django views (using X-Accel-Redirect)
- Not accessible via direct nginx URLs

## Rollback

If you need to rollback, simply:
1. Keep using the old `MEDIA_ROOT` locations (files are still there)
2. Delete the `PRIVATE_MEDIA_ROOT` directory if needed
3. No database changes were made, so no DB rollback needed

## Troubleshooting

### Files Already Exist

If files already exist in the destination, the command will:
- Check if file sizes match
- Skip copying if sizes are identical
- Warn if sizes differ

### Permission Errors

If you get permission errors:

```bash
# Ensure the destination directory is writable
chmod 755 $PRIVATE_MEDIA_ROOT

# Or run with appropriate permissions
sudo -u www-data django-admin migrate_to_private_media
```

### Large File Sets

For very large file sets (thousands of files):
- Use `--model` to migrate one model at a time
- Monitor disk space during migration
- Consider running during low-traffic periods

## Performance Notes

- Files are copied using `shutil.copy2()` which preserves timestamps
- Progress bars show real-time progress
- Already-existing files are skipped quickly (no re-copy)
- The command can be safely run multiple times (idempotent)

## Docker Usage

When running in Docker:

```bash
# Enter the container
docker exec -it krm3-container bash

# Run migration
django-admin migrate_to_private_media

# Or run from host
docker exec krm3-container django-admin migrate_to_private_media --dry-run
```

Ensure the private media directory is mounted as a volume for persistence:

```yaml
volumes:
  - /var/lib/krm3/private-media:/data/private-media
```
