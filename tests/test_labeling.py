"""
Unit tests for the Labeling class.
"""

import unittest
from datetime import datetime
import uuid
import re
import sys
import os

# Add parent directory to path to import the labeling_service module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.labeling_service import Labeling, LabelingValidationError


class TestLabeling(unittest.TestCase):
    """Test cases for the Labeling class."""
    
    def test_init_with_minimal_args(self):
        """Test initialization with minimal arguments."""
        name = "Test Labeling"
        labeling = Labeling(name=name)
        
        self.assertEqual(labeling.name, name)
        self.assertEqual(labeling.color, "#1f77b4")  # Default color
        self.assertTrue(labeling.visible)  # Default visibility
        self.assertEqual(labeling.data, {})  # Empty data
        self.assertTrue(isinstance(labeling.id, str))
        self.assertTrue(uuid.UUID(labeling.id, version=4))  # Valid UUID4
        self.assertTrue(isinstance(labeling.created_at, str))
        self.assertTrue(isinstance(labeling.updated_at, str))
    
    def test_init_with_all_args(self):
        """Test initialization with all arguments."""
        name = "Full Test Labeling"
        color = "#FF5733"
        visible = False
        data = {"timestamps": [{"start": 100, "end": 200, "label": "test"}]}
        custom_id = "custom-id-123"
        
        labeling = Labeling(
            name=name,
            color=color,
            visible=visible,
            data=data,
            id=custom_id
        )
        
        self.assertEqual(labeling.name, name)
        self.assertEqual(labeling.color, color)
        self.assertEqual(labeling.visible, visible)
        self.assertEqual(labeling.data, data)
        self.assertEqual(labeling.id, custom_id)
    
    def test_name_validation(self):
        """Test name validation."""
        # Valid names
        self.assertTrue(Labeling._validate_name("Test"))
        self.assertTrue(Labeling._validate_name("A"))
        self.assertTrue(Labeling._validate_name("  Spaces  "))  # Spaces are allowed
        
        # Invalid names
        self.assertFalse(Labeling._validate_name(""))
        self.assertFalse(Labeling._validate_name("   "))  # Just spaces
        self.assertFalse(Labeling._validate_name(123))  # Not a string
        self.assertFalse(Labeling._validate_name(None))  # None
    
    def test_color_validation(self):
        """Test color validation."""
        # Valid colors
        self.assertTrue(Labeling._validate_color("#123"))
        self.assertTrue(Labeling._validate_color("#123456"))
        self.assertTrue(Labeling._validate_color("#abcDEF"))
        
        # Invalid colors
        self.assertFalse(Labeling._validate_color("123456"))  # Missing #
        self.assertFalse(Labeling._validate_color("#12"))  # Too short
        self.assertFalse(Labeling._validate_color("#1234567"))  # Too long
        self.assertFalse(Labeling._validate_color("#GHIJKL"))  # Invalid hex
        self.assertFalse(Labeling._validate_color(123456))  # Not a string
    
    def test_data_structure_validation(self):
        """Test data structure validation."""
        # Valid data structures
        self.assertTrue(Labeling._validate_data_structure({}))  # Empty dict is valid
        self.assertTrue(Labeling._validate_data_structure({"other_key": "value"}))  # Other keys are allowed
        
        valid_data = {
            "timestamps": [
                {"start": 100, "end": 200, "label": "test1"},
                {"start": 200, "end": 300, "label": "test2"}
            ]
        }
        self.assertTrue(Labeling._validate_data_structure(valid_data))
        
        # Invalid data structures
        self.assertFalse(Labeling._validate_data_structure(None))  # None
        self.assertFalse(Labeling._validate_data_structure([]))  # List instead of dict
        self.assertFalse(Labeling._validate_data_structure("not a dict"))  # String instead of dict
        
        # Invalid timestamps format
        invalid_timestamps_type = {"timestamps": "not a list"}
        self.assertFalse(Labeling._validate_data_structure(invalid_timestamps_type))
        
        # Missing required keys
        missing_keys = {
            "timestamps": [
                {"start": 100, "label": "test"}  # Missing 'end'
            ]
        }
        self.assertFalse(Labeling._validate_data_structure(missing_keys))
        
        # Invalid types
        invalid_types = {
            "timestamps": [
                {"start": "100", "end": 200, "label": "test"}  # start should be number
            ]
        }
        self.assertFalse(Labeling._validate_data_structure(invalid_types))
        
        # End before start
        invalid_range = {
            "timestamps": [
                {"start": 200, "end": 100, "label": "test"}  # end before start
            ]
        }
        self.assertFalse(Labeling._validate_data_structure(invalid_range))
    
    def test_validation_errors_raised(self):
        """Test that validation errors are raised."""
        # Test invalid name
        with self.assertRaises(LabelingValidationError):
            Labeling(name="")
            
        # Test invalid color
        with self.assertRaises(LabelingValidationError):
            Labeling(name="Test", color="invalid")
            
        # Test invalid data structure
        invalid_data = {
            "timestamps": [
                {"start": 200, "end": 100, "label": "test"}  # end before start
            ]
        }
        with self.assertRaises(LabelingValidationError):
            Labeling(name="Test", data=invalid_data)
    
    def test_update_method(self):
        """Test the update method."""
        labeling = Labeling(name="Original")
        
        # Test valid updates
        labeling.update(
            name="Updated",
            color="#FF0000",
            visible=False
        )
        
        self.assertEqual(labeling.name, "Updated")
        self.assertEqual(labeling.color, "#FF0000")
        self.assertFalse(labeling.visible)
        
        # Test that updated_at is changed
        original_updated_at = labeling.updated_at
        
        # Wait a moment to ensure timestamp is different
        import time
        time.sleep(0.01)
        
        labeling.update(name="Another Update")
        self.assertEqual(labeling.name, "Another Update")
        self.assertNotEqual(labeling.updated_at, original_updated_at)
        
        # Test invalid updates
        with self.assertRaises(LabelingValidationError):
            labeling.update(name="")
            
        with self.assertRaises(LabelingValidationError):
            labeling.update(color="invalid")
            
        invalid_data = {
            "timestamps": [
                {"start": 200, "end": 100, "label": "test"}  # end before start
            ]
        }
        with self.assertRaises(LabelingValidationError):
            labeling.update(data=invalid_data)
    
    def test_to_dict_method(self):
        """Test the to_dict method."""
        name = "Test"
        color = "#00FF00"
        visible = True
        data = {"timestamps": [{"start": 100, "end": 200, "label": "test"}]}
        custom_id = "test-id"
        
        labeling = Labeling(
            name=name,
            color=color,
            visible=visible,
            data=data,
            id=custom_id
        )
        
        result = labeling.to_dict()
        
        self.assertEqual(result["id"], custom_id)
        self.assertEqual(result["name"], name)
        self.assertEqual(result["color"], color)
        self.assertEqual(result["visible"], visible)
        self.assertEqual(result["data"], data)
        self.assertTrue("created_at" in result)
        self.assertTrue("updated_at" in result)
    
    def test_from_dict_method(self):
        """Test the from_dict class method."""
        original_dict = {
            "id": "test-id",
            "name": "Test",
            "color": "#00FF00",
            "visible": True,
            "data": {"timestamps": [{"start": 100, "end": 200, "label": "test"}]},
            "created_at": "2025-06-20T10:00:00",
            "updated_at": "2025-06-20T11:00:00"
        }
        
        labeling = Labeling.from_dict(original_dict)
        
        self.assertEqual(labeling.id, original_dict["id"])
        self.assertEqual(labeling.name, original_dict["name"])
        self.assertEqual(labeling.color, original_dict["color"])
        self.assertEqual(labeling.visible, original_dict["visible"])
        self.assertEqual(labeling.data, original_dict["data"])
        self.assertEqual(labeling.created_at, original_dict["created_at"])
        self.assertEqual(labeling.updated_at, original_dict["updated_at"])
    
    def test_from_dict_with_minimal_data(self):
        """Test from_dict with minimal data."""
        minimal_dict = {
            "name": "Minimal Test"
        }
        
        labeling = Labeling.from_dict(minimal_dict)
        
        self.assertEqual(labeling.name, minimal_dict["name"])
        self.assertEqual(labeling.color, "#1f77b4")  # Default color
        self.assertTrue(labeling.visible)  # Default visibility
        self.assertEqual(labeling.data, {})  # Default empty data
        self.assertTrue(isinstance(labeling.id, str))
        
        # Missing timestamps should be handled gracefully
        self.assertTrue(isinstance(labeling.created_at, str)) 
        self.assertTrue(isinstance(labeling.updated_at, str))


if __name__ == "__main__":
    unittest.main()
