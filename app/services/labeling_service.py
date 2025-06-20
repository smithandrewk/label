from typing import Dict, List, Optional, Any, Union
import uuid
import json
import re
from datetime import datetime


class LabelingValidationError(Exception):
    """Exception raised for validation errors in the Labeling class."""
    pass


class Labeling:
    """
    Represents a set of labels that can be applied to accelerometer data.
    
    This class serves as the data structure for multiple labeling systems that can
    be overlaid on accelerometer data visualizations. It contains properties to
    manage the visual representation and data of the labels.
    
    Attributes:
        id (str): Unique identifier for the labeling set
        name (str): Display name of the labeling set
        color (str): Hex color code for visual representation of this labeling set
        visible (bool): Whether this labeling set is currently visible in the UI
        data (dict): The actual label data containing timestamp ranges and labels
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
