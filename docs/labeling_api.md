# Labeling API Documentation

This document provides comprehensive documentation for the Labelings API endpoints.

## Overview

The Labelings API allows for creating, reading, updating, and deleting labeling sets in the accelerometer data visualization application. Labelings can exist at different scopes: global (system-wide), project-level, or session-specific.

## Base URL

All API endpoints are relative to the base URL of your application.

## Authentication

*Note: Authentication details will be added in future versions.*

## Response Format

All API responses follow a standardized format:

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {...}
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_TYPE"
}
```

## Endpoints

### Global Labelings

#### Get All Labelings
**GET** `/api/labelings`

Retrieves all labelings available in the system.

**Query Parameters:**
- `visible_only` (boolean, optional): If `true` (default), returns only visible labelings. If `false`, returns all labelings.

**Example Request:**
```
GET /api/labelings?visible_only=true
```

**Example Response:**
```json
{
  "success": true,
  "message": "Retrieved 3 labelings",
  "data": [
    {
      "labeling_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Activity Labels",
      "color": "#1f77b4",
      "visible": true,
      "data": {
        "timestamps": [
          {
            "start": 1000.0,
            "end": 1500.0,
            "label": "walking"
          }
        ]
      },
      "project_id": null,
      "session_id": null,
      "created_at": "2025-06-20T10:30:00.000Z",
      "updated_at": "2025-06-20T10:30:00.000Z"
    }
  ]
}
```

#### Get Specific Labeling
**GET** `/api/labelings/{labeling_id}`

Retrieves a specific labeling by its ID.

**Path Parameters:**
- `labeling_id` (string): The unique identifier of the labeling

**Example Request:**
```
GET /api/labelings/550e8400-e29b-41d4-a716-446655440000
```

**Example Response:**
```json
{
  "success": true,
  "message": "Retrieved labeling: Activity Labels",
  "data": {
    "labeling_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Activity Labels",
    "color": "#1f77b4",
    "visible": true,
    "data": {
      "timestamps": [
        {
          "start": 1000.0,
          "end": 1500.0,
          "label": "walking"
        }
      ]
    },
    "project_id": null,
    "session_id": null,
    "created_at": "2025-06-20T10:30:00.000Z",
    "updated_at": "2025-06-20T10:30:00.000Z"
  }
}
```

**Error Responses:**
- `404 NOT_FOUND`: Labeling not found
- `500 DATABASE_ERROR`: Database operation failed

#### Create Labeling
**POST** `/api/labelings`

*Status: To be implemented in future commits*

#### Update Labeling
**PUT** `/api/labelings/{labeling_id}`

*Status: To be implemented in future commits*

#### Delete Labeling
**DELETE** `/api/labelings/{labeling_id}`

*Status: To be implemented in future commits*

### Project-Specific Labelings

#### Get Project Labelings
**GET** `/api/projects/{project_id}/labelings`

Retrieves all labelings for a specific project, including global labelings that are accessible to the project.

**Path Parameters:**
- `project_id` (integer): The unique identifier of the project

**Query Parameters:**
- `visible_only` (boolean, optional): If `true` (default), returns only visible labelings. If `false`, returns all labelings.

**Example Request:**
```
GET /api/projects/123/labelings
```

**Example Response:**
```json
{
  "success": true,
  "message": "Retrieved 2 labelings for project 123",
  "data": [
    {
      "labeling_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Project Activity Labels",
      "color": "#ff7f0e",
      "visible": true,
      "data": {
        "timestamps": []
      },
      "project_id": 123,
      "session_id": null,
      "created_at": "2025-06-20T10:30:00.000Z",
      "updated_at": "2025-06-20T10:30:00.000Z"
    },
    {
      "labeling_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Global Activity Labels",
      "color": "#1f77b4",
      "visible": true,
      "data": {
        "timestamps": []
      },
      "project_id": null,
      "session_id": null,
      "created_at": "2025-06-20T10:30:00.000Z",
      "updated_at": "2025-06-20T10:30:00.000Z"
    }
  ]
}
```

#### Create Project Labeling
**POST** `/api/projects/{project_id}/labelings`

*Status: To be implemented in future commits*

### Session-Specific Labelings

#### Get Session Labelings
**GET** `/api/sessions/{session_id}/labelings`

Retrieves all labelings for a specific session, including project-level and global labelings that are accessible to the session.

**Path Parameters:**
- `session_id` (integer): The unique identifier of the session

**Query Parameters:**
- `visible_only` (boolean, optional): If `true` (default), returns only visible labelings. If `false`, returns all labelings.

**Example Request:**
```
GET /api/sessions/456/labelings
```

**Example Response:**
```json
{
  "success": true,
  "message": "Retrieved 3 labelings for session 456",
  "data": [
    {
      "labeling_id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "Session Specific Labels",
      "color": "#2ca02c",
      "visible": true,
      "data": {
        "timestamps": [
          {
            "start": 2000.0,
            "end": 2500.0,
            "label": "running"
          }
        ]
      },
      "project_id": 123,
      "session_id": 456,
      "created_at": "2025-06-20T10:30:00.000Z",
      "updated_at": "2025-06-20T10:30:00.000Z"
    },
    {
      "labeling_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Project Activity Labels",
      "color": "#ff7f0e",
      "visible": true,
      "data": {
        "timestamps": []
      },
      "project_id": 123,
      "session_id": null,
      "created_at": "2025-06-20T10:30:00.000Z",
      "updated_at": "2025-06-20T10:30:00.000Z"
    },
    {
      "labeling_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Global Activity Labels",
      "color": "#1f77b4",
      "visible": true,
      "data": {
        "timestamps": []
      },
      "project_id": null,
      "session_id": null,
      "created_at": "2025-06-20T10:30:00.000Z",
      "updated_at": "2025-06-20T10:30:00.000Z"
    }
  ]
}
```

#### Create Session Labeling
**POST** `/api/sessions/{session_id}/labelings`

*Status: To be implemented in future commits*

### Utility Endpoints

#### Toggle Labeling Visibility
**POST** `/api/labelings/{labeling_id}/toggle`

*Status: To be implemented in future commits*

#### Duplicate Labeling
**POST** `/api/labelings/{labeling_id}/duplicate`

*Status: To be implemented in future commits*

## Data Models

### Labeling Object

| Field | Type | Description |
|-------|------|-------------|
| `labeling_id` | string | Unique identifier (UUID format) |
| `name` | string | Display name of the labeling |
| `color` | string | Hex color code (#RRGGBB) |
| `visible` | boolean | Whether the labeling is currently visible |
| `data` | object | The actual label data (see Data Structure below) |
| `project_id` | integer\|null | Associated project ID (null for global) |
| `session_id` | integer\|null | Associated session ID (null for project/global) |
| `created_at` | string | ISO timestamp of creation |
| `updated_at` | string | ISO timestamp of last update |

### Data Structure

The `data` field contains the actual labeling information:

```json
{
  "timestamps": [
    {
      "start": 1000.0,
      "end": 1500.0,
      "label": "walking"
    },
    {
      "start": 1500.0,
      "end": 2000.0,
      "label": "running"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `timestamps` | array | Array of timestamp objects |
| `timestamps[].start` | number | Start timestamp (milliseconds) |
| `timestamps[].end` | number | End timestamp (milliseconds) |
| `timestamps[].label` | string | Label for this time range |

## Scope Hierarchy

Labelings follow a hierarchical scope system:

1. **Global Labelings** (`project_id: null, session_id: null`): Available system-wide
2. **Project Labelings** (`project_id: set, session_id: null`): Available to all sessions in a project
3. **Session Labelings** (`project_id: set, session_id: set`): Available only to a specific session

When retrieving labelings for a session or project, the API returns labelings from all relevant scopes in hierarchical order.

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `NOT_FOUND` | Requested resource not found |
| `DATABASE_ERROR` | Database operation failed |

## Examples

### Get All Visible Labelings
```bash
curl -X GET "http://localhost:5000/api/labelings?visible_only=true"
```

### Get Specific Labeling
```bash
curl -X GET "http://localhost:5000/api/labelings/550e8400-e29b-41d4-a716-446655440000"
```

### Get Project Labelings
```bash
curl -X GET "http://localhost:5000/api/projects/123/labelings"
```

### Get Session Labelings
```bash
curl -X GET "http://localhost:5000/api/sessions/456/labelings"
```

## Future Enhancements

The following endpoints will be added in future commits:

- **Create** operations for all scopes
- **Update** operations for existing labelings
- **Delete** operations with cascade handling
- **Toggle visibility** for quick show/hide
- **Duplicate** labelings for easy copying
- **Batch operations** for efficient bulk changes
- **Search and filtering** by name, color, or content
- **Export/Import** functionality for labeling sets

## Related Documentation

- [Database Schema Documentation](labeling_schema.md)
- [Schema Integration Guide](labeling_schema_integration.md)
- [Database Indexes Documentation](labeling_indexes.md)
