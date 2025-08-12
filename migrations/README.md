# Database Migrations and Data Migration Tools

This directory contains database schema migrations and data migration tools for the Label application.

## Database Schema Migrations

### create_raw_datasets_tables.sql
Creates the new database schema for raw dataset management:
- `raw_datasets` - Store raw dataset metadata and file locations
- `raw_dataset_sessions` - Original session structure from raw datasets  
- `project_dataset_refs` - Many-to-many links between projects and datasets
- `project_split_configs` - Virtual splitting configurations per project
- Updates to existing `projects` and `sessions` tables for backward compatibility

### add_virtual_split_columns.sql
Adds virtual splitting support to the sessions table:
- `parent_session_data_path` - Path to parent data file for virtual splits
- `data_start_offset` - Start row index for pandas slicing
- `data_end_offset` - End row index for pandas slicing

## Data Migration Tools

### migrate_legacy_projects.py
Converts existing legacy projects (that own their data files) to the new dataset-based architecture.

**Features:**
- Identifies legacy projects with data directories
- Extracts raw data into shared dataset storage with hash-based deduplication
- Converts projects to reference shared datasets instead of owning files
- Preserves all project metadata, labelings, and sessions
- Generates detailed migration reports
- Supports dry-run mode for testing

**Usage:**
```bash
# Dry run to see what would be migrated
python3 migrations/migrate_legacy_projects.py --dry-run

# Migrate all legacy projects  
python3 migrations/migrate_legacy_projects.py

# Migrate specific project only
python3 migrations/migrate_legacy_projects.py --project-id 123

# Dry run for specific project
python3 migrations/migrate_legacy_projects.py --dry-run --project-id 123
```

### rollback_migration.py
Reverts migrated projects back to legacy architecture if needed.

**Features:**
- Identifies projects that were migrated from legacy to dataset-based
- Restores original project paths and ownership model
- Removes dataset references while preserving project data
- Only affects projects that were automatically migrated (not manually created dataset-based projects)
- Generates detailed rollback reports
- Supports dry-run mode for testing

**Usage:**
```bash
# Dry run to see what would be rolled back
python3 migrations/rollback_migration.py --dry-run

# Rollback all migrated projects
python3 migrations/rollback_migration.py

# Rollback specific project only
python3 migrations/rollback_migration.py --project-id 123
```

## Migration Workflow

1. **Backup your database** before running any migrations
2. **Apply database schema changes** by running the SQL migration files
3. **Test the migration** using dry-run mode first:
   ```bash
   python3 migrations/migrate_legacy_projects.py --dry-run
   ```
4. **Run the migration** for real:
   ```bash
   python3 migrations/migrate_legacy_projects.py
   ```
5. **Verify** the migration results and test the application
6. **Keep rollback scripts** available in case you need to revert

## Migration Reports

Both migration scripts generate detailed JSON reports:
- `migration_report_YYYYMMDD_HHMMSS.json` - Details of projects migrated
- `rollback_report_YYYYMMDD_HHMMSS.json` - Details of projects rolled back

These reports include:
- Timestamp and dry-run status
- Count of projects processed/migrated/rolled back
- Count of datasets created
- Detailed results for each project
- List of any errors encountered

## Benefits of the New Architecture

**Before (Legacy):**
- Each project owns and duplicates raw data files
- Projects tightly coupled to specific file directories
- No way to reuse raw data across multiple analysis projects
- Difficult to share datasets between researchers

**After (Dataset-based):**
- Raw data stored once in shared repository with hash-based deduplication
- Projects become lightweight analysis configurations
- Multiple projects can reference the same raw datasets
- Easy export/import of project configurations without moving data files
- Better storage efficiency and data management

## Rollback Considerations

The rollback tool can safely revert projects that were migrated, but:
- Raw datasets created during migration will remain (they may be used by other projects)
- Original file paths must still exist and be accessible
- Only automatically migrated projects can be rolled back (not manually created dataset-based projects)
- Always test rollback in dry-run mode first

## Troubleshooting

**Migration fails with "Directory does not exist":**
- Check that project paths in the database are correct and accessible
- Ensure the application has read permissions to project directories

**Migration fails with "Database connection failed":**
- Verify database connection settings in your .env file
- Ensure database server is running and accessible

**Rollback fails with "Legacy path no longer exists":**
- Original project directories may have been moved or deleted
- Check the migration report to see what the original paths were