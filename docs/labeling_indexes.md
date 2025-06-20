# Labeling Table Index Documentation

This document provides information about the database indexes defined for the `labelings` table in the database schema. These indexes improve the performance of common queries on the labelings table.

## Existing Indexes

### Primary Key
- **Index Name:** PRIMARY (auto-created)
- **Fields:** `labeling_id` (VARCHAR(36))
- **Purpose:** Uniquely identifies each labeling record
- **Usage:** Essential for all operations that reference a specific labeling

### Project Index
- **Index Name:** `idx_project`
- **Fields:** `project_id`
- **Purpose:** Improves query performance when filtering labelings by project
- **Usage:** `SELECT * FROM labelings WHERE project_id = ?`

### Session Index
- **Index Name:** `idx_session`
- **Fields:** `session_id`
- **Purpose:** Improves query performance when filtering labelings by session
- **Usage:** `SELECT * FROM labelings WHERE session_id = ?`

### Unique Labeling Name
- **Index Name:** `unique_labeling_name`
- **Fields:** `name`, `project_id`, `session_id`
- **Purpose:** Enforces uniqueness of labeling names within the same context
- **Usage:** Prevents duplicate names at the project/session level

## Additional Indexes

### Visibility Index
- **Index Name:** `idx_visible`
- **Fields:** `visible`
- **Purpose:** Optimizes filtering of labelings by visibility status
- **Usage:** `SELECT * FROM labelings WHERE visible = TRUE`

### Project-Visibility Composite Index
- **Index Name:** `idx_project_visible`
- **Fields:** `project_id`, `visible`
- **Purpose:** Optimizes queries filtering by both project and visibility
- **Usage:** `SELECT * FROM labelings WHERE project_id = ? AND visible = TRUE`

### Session-Visibility Composite Index
- **Index Name:** `idx_session_visible`
- **Fields:** `session_id`, `visible`
- **Purpose:** Optimizes queries filtering by both session and visibility
- **Usage:** `SELECT * FROM labelings WHERE session_id = ? AND visible = TRUE`

### Name Full-Text Search Index
- **Index Name:** `idx_name_fulltext`
- **Fields:** `name`
- **Purpose:** Enables efficient text search on labeling names
- **Usage:** `SELECT * FROM labelings WHERE MATCH(name) AGAINST('search term')`

### Last Modified Index
- **Index Name:** `idx_updated_at`
- **Fields:** `updated_at`
- **Purpose:** Improves performance when sorting by last modified date
- **Usage:** `SELECT * FROM labelings ORDER BY updated_at DESC`

## Query Optimization Guidelines

When querying the `labelings` table, consider the following guidelines:

1. **Filter by Project or Session First:**
   Always include `project_id` or `session_id` in your WHERE clause when possible, as these are indexed fields.
   ```sql
   -- Good: Using indexed field
   SELECT * FROM labelings WHERE project_id = 123;
   
   -- Avoid: Not using indexed fields
   SELECT * FROM labelings WHERE color = '#FF0000';
   ```

2. **Leverage Composite Indexes:**
   When filtering by both project/session and visibility, the query optimizer can use the composite indexes.
   ```sql
   -- Uses idx_project_visible
   SELECT * FROM labelings WHERE project_id = 123 AND visible = TRUE;
   ```

3. **Use Full-Text Search for Name Queries:**
   For searching labeling names, use the MATCH...AGAINST syntax to leverage the full-text index.
   ```sql
   -- Uses idx_name_fulltext
   SELECT * FROM labelings WHERE MATCH(name) AGAINST('activity');
   
   -- Avoid: Won't use the full-text index
   SELECT * FROM labelings WHERE name LIKE '%activity%';
   ```

4. **Include ORDER BY Indexed Fields:**
   When sorting results, try to sort by indexed fields like `updated_at`.
   ```sql
   -- Uses idx_updated_at
   SELECT * FROM labelings ORDER BY updated_at DESC;
   ```

5. **Be Mindful of Index Selectivity:**
   Indexes on fields with low selectivity (e.g., boolean fields like `visible`) are less effective on their own, but are useful in composite indexes.

By properly leveraging these indexes, application code can efficiently query the labelings data, resulting in better performance even with large numbers of labelings.
