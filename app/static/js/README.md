# JavaScript Architecture Overview

This document outlines the organized JavaScript architecture for the labeling application.

## Layer Structure

```
app/static/
├── js/
│   ├── api/           # API Layer - HTTP requests to backend
│   │   ├── projectAPI.js
│   │   └── sessionAPI.js
│   └── services/      # Service Layer - Business logic and data manipulation
│       └── sessionService.js
├── helpers.js         # Utility functions
├── eventListeners.js  # Event handling
├── navigation.js      # Navigation logic
├── participants.js    # Participant management
└── script.js          # Main application controller
```

## Architectural Principles

### 1. **API Layer** (`js/api/`)
- **Purpose**: Handle all HTTP communication with the backend
- **Responsibilities**: 
  - Making fetch requests
  - Error handling for network issues
  - Data serialization/deserialization
- **Example**: `SessionAPI.loadSessionData(sessionId)`

### 2. **Service Layer** (`js/services/`)
- **Purpose**: Business logic and data manipulation
- **Responsibilities**:
  - Data filtering and transformation
  - Business rule validation
  - Complex calculations
  - State management utilities
- **Example**: `SessionService.getFilteredSessions(sessions)`

### 3. **Controller Layer** (`script.js`)
- **Purpose**: UI coordination and application flow
- **Responsibilities**:
  - DOM manipulation
  - Event handling coordination
  - Calling API and Service layers
  - UI state management

## Benefits

1. **Separation of Concerns**: Each layer has a clear responsibility
2. **Maintainability**: Changes to business logic don't affect API calls
3. **Testability**: Each layer can be tested independently
4. **Reusability**: Service functions can be used across different UI components
5. **Scalability**: Easy to add new features in the appropriate layer

## Usage Guidelines

- **API calls**: Always go through the API layer
- **Business logic**: Implement in the service layer
- **UI logic**: Keep in the main script.js or component files
- **Utilities**: Use helpers.js for pure utility functions

## Examples

```javascript
// ✅ Good: Using the proper layers
const sessions = await ProjectAPI.fetchProjectSessions(projectId);
const availableSessions = SessionService.getFilteredSessions(sessions);
const currentSession = SessionService.findSessionById(sessions, sessionId);

// ❌ Bad: Mixing concerns
const sessions = await fetch('/api/sessions').then(r => r.json());
const availableSessions = sessions.filter(s => s.keep !== 0); // Business logic in controller
```
