from typing import Dict, List, Optional, Any, Union
import uuid
import json
from datetime import datetime


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
        """
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.color = color
        self.visible = visible
        self.data = data if data else {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
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
