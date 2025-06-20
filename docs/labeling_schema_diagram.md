# Labelings Schema Diagram

This document provides a visual representation of the database schema for the labelings feature and its relationships to other tables.

## Entity Relationship Diagram

```
+----------------+       +----------------+       +----------------+
| participants   |       | projects       |       | sessions       |
+----------------+       +----------------+       +----------------+
| participant_id |<---+--| project_id     |<---+--| session_id     |
| ...            |    |  | participant_id |    |  | project_id     |
+----------------+    |  | ...            |    |  | ...            |
                      |  +----------------+    |  +----------------+
                      |                        |
                      |                        |
                      |  +----------------+    |
                      |  | labelings      |    |
                      |  +----------------+    |
                      +--| project_id     |    |
                         | session_id     |----+
                         | labeling_id    |
                         | name           |
                         | color          |
                         | visible        |
                         | data (JSON)    |
                         | ...            |
                         +----------------+
```

## Labeling Scope Hierarchy

```
Global Level
+---------------------------------+
|                                 |
|  System-wide Labelings          |
|  (project_id = NULL,            |
|   session_id = NULL)            |
|                                 |
+---------------------------------+
              |
              v
Project Level
+---------------------------------+
|                                 |
|  Project Labelings              |
|  (project_id = set,             |
|   session_id = NULL)            |
|                                 |
+---------------------------------+
              |
              v
Session Level
+---------------------------------+
|                                 |
|  Session Labelings              |
|  (project_id = set,             |
|   session_id = set)             |
|                                 |
+---------------------------------+
```

## Data Structure

```
Labeling
+-------------------+
| labeling_id: UUID |
| name: string      |
| color: hex        |
| visible: boolean  |
+-------------------+
         |
         v
+-------------------+
| data: JSON        |
+-------------------+
         |
         v
    Timestamps
+-------------------+
| - start: float    |
| - end: float      |
| - label: string   |
+-------------------+
```

## Database Flow for Typical Operations

1. **Creating a Labeling**:
   ```
   Application
   |
   v
   INSERT INTO labelings (labeling_id, name, color, ...)
   |
   v
   New Labeling Record Created
   ```

2. **Fetching Labelings for a Session**:
   ```
   Application
   |
   v
   SELECT * FROM labelings 
   WHERE session_id = ? OR 
         (project_id = ? AND session_id IS NULL) OR
         (project_id IS NULL AND session_id IS NULL)
   |
   v
   Return Session, Project, and Global Labelings
   ```

3. **Updating a Labeling's Data**:
   ```
   Application
   |
   v
   UPDATE labelings
   SET data = ?, updated_at = CURRENT_TIMESTAMP
   WHERE labeling_id = ?
   |
   v
   Labeling Record Updated
   ```

4. **Deleting a Project**:
   ```
   Application
   |
   v
   DELETE FROM projects
   WHERE project_id = ?
   |
   v
   ON DELETE CASCADE
   |
   v
   Associated Sessions & Labelings Automatically Deleted
   ```

## Index Usage Examples

For a complete list of indexes and usage examples, refer to the [Labeling Indexes Documentation](labeling_indexes.md).
