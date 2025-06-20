# Labelings Database Schema Documentation

This document provides comprehensive information about the database schema changes related to the labelings management feature.

## Overview

The labelings feature introduces a new table to the database schema to store multiple labeling sets that can be overlaid on accelerometer data visualizations. This enables users to create, manage, and toggle different labeling systems for the same data.

## Table Structure

### Labelings Table

The `labelings` table stores information about different labeling sets in the system.

#### Column Definitions

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `labeling_id` | VARCHAR(36) | PRIMARY KEY | Unique identifier for the labeling (UUID format) |
| `name` | VARCHAR(255) | NOT NULL | Display name of the labeling |
| `color` | CHAR(7) | NOT NULL | Hex color code for visual representation (#RRGGBB) |
| `visible` | BOOLEAN | NOT NULL DEFAULT TRUE | Whether the labeling is currently visible |
| `data` | JSON | | The actual label data containing timestamp ranges and labels |
| `project_id` | INT | | Foreign key to projects table (NULL for global labelings) |
| `session_id` | INT | | Foreign key to sessions table (NULL for project-level labelings) |
| `created_at` | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | When the labeling was created |
| `updated_at` | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | When the labeling was last updated |

#### Indexes

| Index Name | Type | Columns | Description |
|------------|------|---------|-------------|
| PRIMARY | PRIMARY KEY | `labeling_id` | Primary key for table |
| `idx_project` | INDEX | `project_id` | Improves performance when filtering by project |
| `idx_session` | INDEX | `session_id` | Improves performance when filtering by session |
| `unique_labeling_name` | UNIQUE | `name`, `project_id`, `session_id` | Ensures unique names within same context |
| `idx_visible` | INDEX | `visible` | Optimizes filtering by visibility status |
| `idx_project_visible` | INDEX | `project_id`, `visible` | Optimizes filtering by project and visibility |
| `idx_session_visible` | INDEX | `session_id`, `visible` | Optimizes filtering by session and visibility |
| `idx_name_fulltext` | FULLTEXT | `name` | Enables efficient text search on names |
| `idx_updated_at` | INDEX | `updated_at` | Improves sorting by last modified date |

#### Foreign Keys

| Foreign Key | Referenced Table | Referenced Column | On Delete | On Update |
|-------------|-----------------|-------------------|-----------|-----------|
| `project_id` | `projects` | `project_id` | CASCADE | RESTRICT |
| `session_id` | `sessions` | `session_id` | CASCADE | RESTRICT |

The CASCADE delete behavior ensures that when a project or session is deleted, any associated labelings are also deleted.

## Relationships

The `labelings` table has the following relationships:

1. **Many-to-One with Projects**: Each labeling can be associated with at most one project, but a project can have many labelings. This is represented by the `project_id` foreign key.

2. **Many-to-One with Sessions**: Each labeling can be associated with at most one session, but a session can have many labelings. This is represented by the `session_id` foreign key.

## Scope Hierarchy

Labelings can be defined at different levels of scope:

1. **Global/System-level Labelings**: When both `project_id` and `session_id` are NULL, the labeling is available system-wide.

2. **Project-level Labelings**: When `project_id` is set but `session_id` is NULL, the labeling applies to all sessions within that project.

3. **Session-specific Labelings**: When both `project_id` and `session_id` are set, the labeling is specific to a single session.

## Data Format

The `data` column uses the JSON data type to store the actual labeling information. The expected format is:

```json
{
  "timestamps": [
    {
      "start": 1000.0,     // Start timestamp (in milliseconds)
      "end": 1500.0,       // End timestamp (in milliseconds)
      "label": "walking"   // Label value
    },
    {
      "start": 1500.0,
      "end": 2000.0,
      "label": "running"
    }
    // More timestamp ranges...
  ]
}
```

## Migration Scripts

Two migration scripts have been created to implement these schema changes:

1. **migration_20250620_labelings.sql**: Creates the labelings table with basic structure and constraints.

2. **migration_20250620_labeling_indexes.sql**: Adds additional indexes for optimizing various query patterns.

## Querying Guidelines

For detailed information about using the indexes efficiently and optimizing queries on the labelings table, refer to the [Labeling Indexes Documentation](labeling_indexes.md).

## Extension Considerations

Future extensions to this schema might include:

1. **Labeling Templates**: A separate table for storing reusable labeling templates.

2. **Label Categories**: Adding support for categorizing labels within a labeling set.

3. **Collaborative Labeling**: Adding fields to track which user created/modified each labeling for collaborative workflows.

4. **Version History**: Tracking changes to labelings over time by storing version history.
