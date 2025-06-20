"""
Labeling Service Module

This module provides classes and utilities for managing labelings in the accelerometer 
data visualization application. It defines the data structure for representing multiple
labeling systems that can be overlaid on accelerometer data visualizations.

Key components:
- Labeling: Class representing a set of labels with visual properties
- LabelingValidationError: Exception for validation errors
- LabelingService: Service class for database operations

Example usage:
    # Create a new labeling
    basic_labeling = Labeling(name="Activity Labels")
    
    # Create a labeling with custom properties
    custom_labeling = Labeling(
        name="Custom Activity Labels",
        color="#FF5733",
        visible=True
    )
    
    # Add data to the labeling
    custom_labeling.update(data={
        "timestamps": [
            {
                "start": 1000.0, 
                "end": 1500.0, 
                "label": "walking"
            }
        ]
    })
    
    # Database operations
    service = LabelingService(get_db_connection)
    all_labelings = service.get_all_labelings()
    project_labelings = service.get_labelings_for_project(project_id)
"""

from typing import Dict, List, Optional, Any, Union
import uuid
import json
import re
from datetime import datetime
from app.exceptions import DatabaseError


class LabelingValidationError(Exception):
    """
    Exception raised for validation errors in the Labeling class.
    
    This exception is raised when validation fails for Labeling attributes
    during initialization or updates.
    
    Example:
        try:
            labeling = Labeling(name="", color="invalid-color")
        except LabelingValidationError as e:
            print(f"Validation failed: {e}")
    """
    pass


class Labeling:
    """
    Represents a set of labels with visual properties for accelerometer data visualization.
    
    A labeling contains a collection of timestamp ranges with associated labels,
    along with visual properties like color and visibility status.
    
    Attributes:
        id (str): Unique identifier for the labeling (UUID)
        name (str): Display name of the labeling
        color (str): Hex color code for visualization (#RRGGBB)
        visible (bool): Whether the labeling is currently visible
        data (dict): Dictionary containing timestamp ranges and labels
        created_at (str): ISO timestamp of creation
        updated_at (str): ISO timestamp of last update
    """
    
    def __init__(self, name: str, color: str = "#1f77b4", visible: bool = True, 
                 data: Optional[Dict[str, Any]] = None, id: Optional[str] = None):
        """
        Initialize a new Labeling instance.
        
        Args:
            name: Display name of the labeling
            color: Hex color code (default: "#1f77b4")
            visible: Whether the labeling is visible (default: True)
            data: Dictionary containing labeling data (default: empty dict)
            id: Unique identifier (default: auto-generated UUID)
            
        Raises:
            LabelingValidationError: If validation fails
        """
        # Validate inputs
        if not self._validate_name(name):
            raise LabelingValidationError("Name must be a non-empty string")
        if not self._validate_color(color):
            raise LabelingValidationError("Color must be a valid hex color code")
        if data is not None and not self._validate_data_structure(data):
            raise LabelingValidationError("Invalid data structure")
        
        # Set attributes
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.color = color
        self.visible = visible
        self.data = data if data is not None else {}
        
        # Set timestamps
        current_time = datetime.now().isoformat()
        self.created_at = current_time
        self.updated_at = current_time
    
    @staticmethod
    def _validate_name(name: Any) -> bool:
        """Validate that name is a non-empty string."""
        return isinstance(name, str) and name.strip() != ""
    
    @staticmethod
    def _validate_color(color: Any) -> bool:
        """Validate that color is a valid hex color code."""
        if not isinstance(color, str):
            return False
        # Match #RGB or #RRGGBB format
        pattern = r'^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$'
        return bool(re.match(pattern, color))
    
    @staticmethod
    def _validate_data_structure(data: Any) -> bool:
        """Validate the data structure format."""
        if not isinstance(data, dict):
            return False
        
        # If timestamps exist, validate their structure
        if 'timestamps' in data:
            timestamps = data['timestamps']
            if not isinstance(timestamps, list):
                return False
            
            for entry in timestamps:
                if not isinstance(entry, dict):
                    return False
                
                # Check required keys
                required_keys = ['start', 'end', 'label']
                if not all(key in entry for key in required_keys):
                    return False
                
                # Validate types
                if not isinstance(entry['start'], (int, float)):
                    return False
                if not isinstance(entry['end'], (int, float)):
                    return False
                if not isinstance(entry['label'], str):
                    return False
                
                # Validate time order
                if entry['end'] <= entry['start']:
                    return False
        
        return True
    
    def update(self, **kwargs) -> None:
        """
        Update labeling properties.
        
        Args:
            **kwargs: Keyword arguments for properties to update
            
        Raises:
            LabelingValidationError: If validation fails
        """
        # Validate updates before applying
        if 'name' in kwargs and not self._validate_name(kwargs['name']):
            raise LabelingValidationError("Name must be a non-empty string")
        if 'color' in kwargs and not self._validate_color(kwargs['color']):
            raise LabelingValidationError("Color must be a valid hex color code")
        if 'data' in kwargs and not self._validate_data_structure(kwargs['data']):
            raise LabelingValidationError("Invalid data structure")
        
        # Apply updates
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Update timestamp
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert labeling to dictionary format.
        
        Returns:
            Dictionary representation of the labeling
        """
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "visible": self.visible,
            "data": self.data,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Labeling':
        """
        Create a Labeling instance from a dictionary.
        
        Args:
            data: Dictionary containing labeling data
            
        Returns:
            New Labeling instance
            
        Raises:
            LabelingValidationError: If validation fails
        """
        # Create instance
        labeling = cls(
            name=data.get("name", "Untitled Labeling"),
            color=data.get("color", "#1f77b4"),
            visible=data.get("visible", True),
            data=data.get("data", {}),
            id=data.get("id")
        )
        
        # Set timestamps if provided
        if "created_at" in data:
            labeling.created_at = data["created_at"]
        if "updated_at" in data:
            labeling.updated_at = data["updated_at"]
        
        return labeling


class LabelingService:
    """
    Service class for managing labeling database operations.
    
    This class provides methods for creating, reading, updating, and deleting
    labelings in the database. It handles the conversion between database
    records and Labeling objects.
    """
    
    def __init__(self, get_db_connection=None):
        """
        Initialize the LabelingService.
        
        Args:
            get_db_connection: Function to get database connection
        """
        self.get_db_connection = get_db_connection
    
    def get_all_labelings(self, visible_only=True) -> List[Dict[str, Any]]:
        """
        Get all labelings from the database.
        
        Args:
            visible_only: If True, only return visible labelings
            
        Returns:
            List of labeling dictionaries
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Build query based on visibility filter
            if visible_only:
                cursor.execute("""
                    SELECT labeling_id, name, color, visible, data, project_id, session_id,
                           created_at, updated_at
                    FROM labelings
                    WHERE visible = TRUE
                    ORDER BY updated_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT labeling_id, name, color, visible, data, project_id, session_id,
                           created_at, updated_at
                    FROM labelings
                    ORDER BY updated_at DESC
                """)
            
            labelings = cursor.fetchall()
            
            # Convert to proper format
            for labeling in labelings:
                if labeling['data'] is not None:
                    labeling['data'] = json.loads(labeling['data']) if isinstance(labeling['data'], str) else labeling['data']
                else:
                    labeling['data'] = {}
                    
                # Convert timestamps to ISO format
                labeling['created_at'] = labeling['created_at'].isoformat() if labeling['created_at'] else None
                labeling['updated_at'] = labeling['updated_at'].isoformat() if labeling['updated_at'] else None
            
            return labelings
            
        except Exception as e:
            raise DatabaseError(f'Failed to get labelings: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def get_labeling_by_id(self, labeling_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific labeling by ID.
        
        Args:
            labeling_id: The unique identifier for the labeling
            
        Returns:
            Labeling dictionary or None if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT labeling_id, name, color, visible, data, project_id, session_id,
                       created_at, updated_at
                FROM labelings
                WHERE labeling_id = %s
            """, (labeling_id,))
            
            labeling = cursor.fetchone()
            
            if labeling:
                # Convert JSON data
                if labeling['data'] is not None:
                    labeling['data'] = json.loads(labeling['data']) if isinstance(labeling['data'], str) else labeling['data']
                else:
                    labeling['data'] = {}
                    
                # Convert timestamps to ISO format
                labeling['created_at'] = labeling['created_at'].isoformat() if labeling['created_at'] else None
                labeling['updated_at'] = labeling['updated_at'].isoformat() if labeling['updated_at'] else None
            
            return labeling
            
        except Exception as e:
            raise DatabaseError(f'Failed to get labeling: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def get_labelings_for_project(self, project_id: int, visible_only=True) -> List[Dict[str, Any]]:
        """
        Get all labelings for a specific project, including global labelings.
        
        Args:
            project_id: The project ID
            visible_only: If True, only return visible labelings
            
        Returns:
            List of labeling dictionaries
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get labelings for this project and global labelings
            visibility_clause = "AND visible = TRUE" if visible_only else ""
            
            cursor.execute(f"""
                SELECT labeling_id, name, color, visible, data, project_id, session_id,
                       created_at, updated_at
                FROM labelings
                WHERE (project_id = %s OR project_id IS NULL) 
                      AND session_id IS NULL
                      {visibility_clause}
                ORDER BY project_id IS NULL ASC, updated_at DESC
            """, (project_id,))
            
            labelings = cursor.fetchall()
            
            # Convert to proper format
            for labeling in labelings:
                if labeling['data'] is not None:
                    labeling['data'] = json.loads(labeling['data']) if isinstance(labeling['data'], str) else labeling['data']
                else:
                    labeling['data'] = {}
                    
                # Convert timestamps to ISO format
                labeling['created_at'] = labeling['created_at'].isoformat() if labeling['created_at'] else None
                labeling['updated_at'] = labeling['updated_at'].isoformat() if labeling['updated_at'] else None
            
            return labelings
            
        except Exception as e:
            raise DatabaseError(f'Failed to get project labelings: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def get_labelings_for_session(self, session_id: int, project_id: int = None, visible_only=True) -> List[Dict[str, Any]]:
        """
        Get all labelings for a specific session, including project and global labelings.
        
        Args:
            session_id: The session ID
            project_id: The project ID (optional, will be fetched if not provided)
            visible_only: If True, only return visible labelings
            
        Returns:
            List of labeling dictionaries
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # If project_id not provided, get it from session
            if project_id is None:
                cursor.execute("SELECT project_id FROM sessions WHERE session_id = %s", (session_id,))
                session_info = cursor.fetchone()
                if not session_info:
                    raise DatabaseError(f'Session {session_id} not found')
                project_id = session_info['project_id']
            
            # Get labelings for this session, project, and global labelings
            visibility_clause = "AND visible = TRUE" if visible_only else ""
            
            cursor.execute(f"""
                SELECT labeling_id, name, color, visible, data, project_id, session_id,
                       created_at, updated_at
                FROM labelings
                WHERE (session_id = %s OR 
                       (project_id = %s AND session_id IS NULL) OR 
                       (project_id IS NULL AND session_id IS NULL))
                      {visibility_clause}
                ORDER BY session_id IS NULL ASC, project_id IS NULL ASC, updated_at DESC
            """, (session_id, project_id))
            
            labelings = cursor.fetchall()
            
            # Convert to proper format
            for labeling in labelings:
                if labeling['data'] is not None:
                    labeling['data'] = json.loads(labeling['data']) if isinstance(labeling['data'], str) else labeling['data']
                else:
                    labeling['data'] = {}
                    
                # Convert timestamps to ISO format
                labeling['created_at'] = labeling['created_at'].isoformat() if labeling['created_at'] else None
                labeling['updated_at'] = labeling['updated_at'].isoformat() if labeling['updated_at'] else None
            
            return labelings
            
        except Exception as e:
            raise DatabaseError(f'Failed to get session labelings: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def create_labeling(self, labeling: Labeling, project_id: int = None, session_id: int = None) -> str:
        """
        Create a new labeling in the database.
        
        Args:
            labeling: The Labeling object to create
            project_id: Optional project ID for project-scoped labeling
            session_id: Optional session ID for session-scoped labeling
            
        Returns:
            The labeling_id of the created labeling
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            # Serialize the labeling data
            serialized_data = self.serialize_labeling_data(labeling.data)
            
            cursor.execute("""
                INSERT INTO labelings (labeling_id, name, color, visible, data, project_id, session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                labeling.id, 
                labeling.name, 
                labeling.color, 
                labeling.visible,
                serialized_data,
                project_id,
                session_id
            ))
            
            conn.commit()
            return labeling.id
            
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to create labeling: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def update_labeling(self, labeling_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing labeling in the database.
        
        Args:
            labeling_id: The ID of the labeling to update
            updates: Dictionary of fields to update
            
        Returns:
            True if labeling was updated, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key == 'data':
                    # Serialize data if updating data field
                    value = self.serialize_labeling_data(value)
                set_clauses.append(f"{key} = %s")
                values.append(value)
            
            if not set_clauses:
                return False
            
            # Add updated_at timestamp
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(labeling_id)
            
            query = f"""
                UPDATE labelings 
                SET {', '.join(set_clauses)}
                WHERE labeling_id = %s
            """
            
            cursor.execute(query, values)
            rows_affected = cursor.rowcount
            conn.commit()
            
            return rows_affected > 0
            
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to update labeling: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def delete_labeling(self, labeling_id: str) -> bool:
        """
        Delete a labeling from the database.
        
        Args:
            labeling_id: The ID of the labeling to delete
            
        Returns:
            True if labeling was deleted, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM labelings WHERE labeling_id = %s", (labeling_id,))
            rows_affected = cursor.rowcount
            conn.commit()
            
            return rows_affected > 0
            
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to delete labeling: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    def toggle_labeling_visibility(self, labeling_id: str) -> Optional[bool]:
        """
        Toggle the visibility of a labeling.
        
        Args:
            labeling_id: The ID of the labeling to toggle
            
        Returns:
            New visibility state, or None if labeling not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get current visibility state
            cursor.execute("SELECT visible FROM labelings WHERE labeling_id = %s", (labeling_id,))
            result = cursor.fetchone()
            
            if not result:
                return None
            
            new_visibility = not result['visible']
            
            # Update visibility
            cursor.execute("""
                UPDATE labelings 
                SET visible = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE labeling_id = %s
            """, (new_visibility, labeling_id))
            
            conn.commit()
            return new_visibility
            
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Failed to toggle labeling visibility: {str(e)}')
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def serialize_labeling_data(data: Dict[str, Any]) -> str:
        """
        Serialize labeling data to JSON string for database storage.
        
        Args:
            data: The labeling data dictionary
            
        Returns:
            JSON string representation of the data
        """
        if not data:
            return json.dumps({})
        
        # Ensure data is in the expected format
        if not isinstance(data, dict):
            raise ValueError("Labeling data must be a dictionary")
        
        # Validate the structure if timestamps exist
        if 'timestamps' in data:
            timestamps = data['timestamps']
            if not isinstance(timestamps, list):
                raise ValueError("Timestamps must be a list")
            
            for i, entry in enumerate(timestamps):
                if not isinstance(entry, dict):
                    raise ValueError(f"Timestamp entry {i} must be a dictionary")
                
                required_keys = ['start', 'end', 'label']
                for key in required_keys:
                    if key not in entry:
                        raise ValueError(f"Timestamp entry {i} missing required key: {key}")
                
                # Validate data types
                if not isinstance(entry['start'], (int, float)):
                    raise ValueError(f"Timestamp entry {i} 'start' must be a number")
                if not isinstance(entry['end'], (int, float)):
                    raise ValueError(f"Timestamp entry {i} 'end' must be a number")
                if not isinstance(entry['label'], str):
                    raise ValueError(f"Timestamp entry {i} 'label' must be a string")
                
                # Validate time order
                if entry['end'] <= entry['start']:
                    raise ValueError(f"Timestamp entry {i} 'end' must be after 'start'")
        
        return json.dumps(data)
    
    @staticmethod
    def deserialize_labeling_data(json_str: str) -> Dict[str, Any]:
        """
        Deserialize labeling data from JSON string.
        
        Args:
            json_str: JSON string representation of the data
            
        Returns:
            Dictionary representation of the labeling data
        """
        if not json_str:
            return {}
        
        try:
            data = json.loads(json_str)
            if not isinstance(data, dict):
                return {}
            return data
        except json.JSONDecodeError:
            return {}
    
    def labeling_to_dict(self, labeling: Labeling) -> Dict[str, Any]:
        """
        Convert a Labeling object to a dictionary suitable for API responses.
        
        Args:
            labeling: The Labeling object to convert
            
        Returns:
            Dictionary representation
        """
        return {
            "labeling_id": labeling.id,
            "name": labeling.name,
            "color": labeling.color,
            "visible": labeling.visible,
            "data": labeling.data,
            "created_at": labeling.created_at,
            "updated_at": labeling.updated_at
        }
    
    def dict_to_labeling(self, data: Dict[str, Any]) -> Labeling:
        """
        Convert a dictionary to a Labeling object.
        
        Args:
            data: Dictionary containing labeling data
            
        Returns:
            Labeling object
        """
        return Labeling.from_dict({
            "id": data.get("labeling_id"),
            "name": data.get("name", "Untitled Labeling"),
            "color": data.get("color", "#1f77b4"),
            "visible": data.get("visible", True),
            "data": data.get("data", {}),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at")
        })
    
    def export_labelings_json(self, labeling_ids: List[str] = None) -> Dict[str, Any]:
        """
        Export labelings to a JSON-serializable format.
        
        Args:
            labeling_ids: Optional list of specific labeling IDs to export.
                         If None, exports all labelings.
            
        Returns:
            Dictionary containing exported labelings data
        """
        try:
            if labeling_ids:
                # Get specific labelings
                labelings = []
                for labeling_id in labeling_ids:
                    labeling = self.get_labeling_by_id(labeling_id)
                    if labeling:
                        labelings.append(labeling)
            else:
                # Get all labelings
                labelings = self.get_all_labelings(visible_only=False)
            
            return {
                "export_timestamp": datetime.now().isoformat(),
                "export_version": "1.0",
                "total_labelings": len(labelings),
                "labelings": labelings
            }
            
        except Exception as e:
            raise DatabaseError(f'Failed to export labelings: {str(e)}')
    
    def import_labelings_json(self, import_data: Dict[str, Any], overwrite_existing: bool = False) -> Dict[str, Any]:
        """
        Import labelings from a JSON format.
        
        Args:
            import_data: Dictionary containing labelings data to import
            overwrite_existing: Whether to overwrite existing labelings with same ID
            
        Returns:
            Dictionary with import results
        """
        if not isinstance(import_data, dict) or 'labelings' not in import_data:
            raise ValueError("Invalid import data format")
        
        results = {
            "imported": 0,
            "skipped": 0,
            "errors": []
        }
        
        for labeling_data in import_data['labelings']:
            try:
                labeling_id = labeling_data.get('labeling_id')
                
                # Check if labeling already exists
                existing = self.get_labeling_by_id(labeling_id) if labeling_id else None
                
                if existing and not overwrite_existing:
                    results["skipped"] += 1
                    continue
                
                # Create Labeling object
                labeling = self.dict_to_labeling(labeling_data)
                
                if existing and overwrite_existing:
                    # Update existing labeling
                    success = self.update_labeling(labeling_id, {
                        'name': labeling.name,
                        'color': labeling.color,
                        'visible': labeling.visible,
                        'data': labeling.data
                    })
                    if success:
                        results["imported"] += 1
                    else:
                        results["errors"].append(f"Failed to update labeling {labeling_id}")
                else:
                    # Create new labeling
                    project_id = labeling_data.get('project_id')
                    session_id = labeling_data.get('session_id')
                    self.create_labeling(labeling, project_id, session_id)
                    results["imported"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Error processing labeling: {str(e)}")
        
        return results
