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


class Labeling:
    """
    Represents a set of labels that can be applied to accelerometer data.
    
    This class serves as the data structure for multiple labeling systems that can
    be overlaid on accelerometer data visualizations. It contains properties to
    manage the visual representation and data of the labels.
    
    A labeling object consists of:
    1. Metadata (id, name, color, visibility status)
    2. Label data containing timestamp ranges and associated labels
    3. Creation and update timestamps for tracking changes
    
    Key functionalities:
    - Create and manage labeling sets with visual properties
    - Validate labeling data structure
    - Convert to/from dictionary format for storage and transmission
    - Update properties with validation
    
    Attributes:
        id (str): Unique identifier for the labeling set
        name (str): Display name of the labeling set
        color (str): Hex color code for visual representation of this labeling set
        visible (bool): Whether this labeling set is currently visible in the UI
        data (dict): The actual label data containing timestamp ranges and labels
        created_at (str): ISO-formatted timestamp of creation
        updated_at (str): ISO-formatted timestamp of last update
    
    Example:
        # Create a basic labeling
        labeling = Labeling(name="Activity Labels")
        
        # Convert to dictionary for storage
        data = labeling.to_dict()
        
        # Later, reconstruct the labeling
        reconstructed = Labeling.from_dict(data)
    """
    
    def __init__(
        self,
        name: str,
        color: str = "#1f77b4",  # Default to a standard blue color
        visible: bool = True,
        data: Optional[Dict] = None,
        id: Optional[str] = None
    ):
        """
        Initialize a new Labeling instance.
        
        Args:
            name: Display name for the labeling set
            color: Hex color code for visual representation (default: "#1f77b4")
            visible: Whether this labeling is visible by default (default: True)
            data: Optional dictionary containing labeling data
            id: Optional unique identifier (will be generated if not provided)
            
        Raises:
            LabelingValidationError: If any of the input parameters fail validation
        """
        # Validate inputs before setting attributes
        if not self._validate_name(name):
            raise LabelingValidationError(f"Invalid name: {name}. Name must be a non-empty string.")
            
        if not self._validate_color(color):
            raise LabelingValidationError(f"Invalid color code: {color}. Must be a valid hex color code.")
        
        if data and not self._validate_data_structure(data):
            raise LabelingValidationError("Invalid data structure for labeling data.")
        
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.color = color
        self.visible = visible
        self.data = data if data else {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    @staticmethod
    def _validate_name(name: str) -> bool:
        """
        Validate the labeling name.
        
        Args:
            name: The name to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        return isinstance(name, str) and len(name.strip()) > 0
    
    @staticmethod
    def _validate_color(color: str) -> bool:
        """
        Validate the color code.
        
        Args:
            color: The hex color code to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check if it's a valid hex color code
        pattern = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
        return isinstance(color, str) and bool(re.match(pattern, color))
        
    @staticmethod
    def _validate_data_structure(data: Dict) -> bool:
        """
        Validate the data structure for labelings.
        
        Expected format:
        {
            "timestamps": [
                {
                    "start": float,  # start timestamp
                    "end": float,    # end timestamp
                    "label": str      # label value
                },
                ...
            ]
        }
        
        Args:
            data: The labeling data to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
            
        # Check for timestamps key
        if "timestamps" not in data:
            return True  # Empty data is valid
            
        # Validate each timestamp entry
        timestamps = data.get("timestamps", [])
        if not isinstance(timestamps, list):
            return False
            
        for entry in timestamps:
            if not isinstance(entry, dict):
                return False
                
            # Check required keys
            if not all(key in entry for key in ["start", "end", "label"]):
                return False
                
            # Check types
            if not (isinstance(entry.get("start"), (int, float)) and 
                    isinstance(entry.get("end"), (int, float)) and
                    isinstance(entry.get("label"), str)):
                return False
                
            # Ensure end is after start
            if entry.get("end") <= entry.get("start"):
                return False
                
        return True
    
    def update(self, **kwargs) -> None:
        """
        Update the labeling attributes.
        
        Args:
            **kwargs: Keyword arguments with attributes to update
            
        Raises:
            LabelingValidationError: If any of the updated attributes fail validation
        """
        # Validate inputs before updating
        if "name" in kwargs and not self._validate_name(kwargs["name"]):
            raise LabelingValidationError(f"Invalid name: {kwargs['name']}. Name must be a non-empty string.")
            
        if "color" in kwargs and not self._validate_color(kwargs["color"]):
            raise LabelingValidationError(f"Invalid color code: {kwargs['color']}. Must be a valid hex color code.")
            
        if "data" in kwargs and not self._validate_data_structure(kwargs["data"]):
            raise LabelingValidationError("Invalid data structure for labeling data.")
        
        # Update attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Update timestamp
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Labeling instance to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the Labeling
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
            Labeling: A new Labeling instance
        """
        labeling = cls(
            name=data.get("name", "Untitled Labeling"),
            color=data.get("color", "#1f77b4"),
            visible=data.get("visible", True),
            data=data.get("data", {}),
            id=data.get("id")
        )
        
        # Handle timestamps if they exist
        if "created_at" in data:
            labeling.created_at = data["created_at"]
        if "updated_at" in data:
            labeling.updated_at = data["updated_at"]
            
        return labeling
