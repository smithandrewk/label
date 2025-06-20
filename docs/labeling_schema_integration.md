# Labelings Integration with Existing Schema

This document explains how the new labelings table integrates with the existing database schema and application architecture.

## Schema Integration

### Before: Original Schema Structure

The existing schema used a file-based approach for labels, with references in the database:

```
participants → projects → sessions
                             ↓
                        labels.json (file-based)
```

Sessions would reference label files stored on disk, with no direct database representation of the labels.

### After: New Schema Structure

With the addition of the labelings table, we now have a fully database-driven approach:

```
participants → projects → sessions
       ↑           ↑          ↑
       └───────────┴──────────┘
                   │
                   v
               labelings
```

The labelings table can reference participants, projects, or sessions, allowing for different levels of scope for labeling sets.

## Data Migration Considerations

When migrating from the existing file-based labeling system to the new database-driven approach:

1. **Existing labels.json files** will need to be parsed and converted into database records in the `labelings` table.

2. **Default scope** for migrated labels should be at the session level (both `project_id` and `session_id` set).

3. **Duplicate handling** may be needed if the same label name appears across multiple files.

4. **Data consistency** checks should be performed to ensure all label data is properly migrated.

## Application Integration Points

The labelings table integrates with the application at several key points:

### Backend Integration

1. **Session Management**:
   - When sessions are loaded, associated labelings should be fetched from the database.
   - When sessions are deleted, associated labelings will be automatically deleted via foreign key cascade.

2. **Project Management**:
   - Project-level labelings should be accessible to all sessions within that project.
   - When projects are deleted, all associated labelings will be automatically deleted.

3. **API Layer**:
   - New API endpoints will be needed to create, read, update, and delete labelings.
   - APIs should respect the scope hierarchy (global, project, session).

### Frontend Integration

1. **Visualization View**:
   - The UI will need controls to toggle different labeling sets on/off.
   - Color handling will need to support multiple concurrent labelings.

2. **Session Management UI**:
   - Options to create new labelings or modify existing ones.
   - Ability to copy labelings between sessions.

3. **Project Management UI**:
   - Options to create project-level labelings.
   - Ability to apply project labelings to specific sessions.

## Backward Compatibility

To maintain backward compatibility:

1. **Default Labeling**: Each session should have a default labeling that behaves like the original labeling system.

2. **File Fallback**: If database labelings are not found, the system should fall back to reading the legacy labels.json file.

3. **Export Format**: Support exporting labelings in the original labels.json format for compatibility with external tools.

## Performance Considerations

Adding the labelings table has performance implications:

1. **Query Optimization**: Proper use of indexes is critical, especially for filtering by project_id and session_id.

2. **Frontend Rendering**: Displaying multiple labelings simultaneously requires efficient rendering strategies.

3. **Data Volume**: The JSON data field can grow large, so consider techniques like pagination or partial loading for large label sets.

## Future Schema Evolution

As the feature evolves, consider these schema enhancements:

1. **User Attribution**: Add columns for created_by_user_id and updated_by_user_id to track changes.

2. **Versioning**: Add a version column or separate history table to track labeling changes over time.

3. **Sharing & Permissions**: Add tables to control who can view/edit specific labelings.

4. **Labeling Templates**: Create a separate table for reusable labeling templates.
