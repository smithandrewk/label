"""
Labeling Examples

This file contains examples of how to use the Labeling class.
It demonstrates creating, manipulating, and validating labeling objects.
"""

from typing import Dict, Any
from labeling_service import Labeling, LabelingValidationError


def create_basic_labeling() -> Labeling:
    """
    Example of creating a basic labeling object with minimal parameters.
    
    Returns:
        Labeling: A basic labeling object
    """
    # Create a basic labeling with just a name
    basic_labeling = Labeling(name="Basic Activity Labels")
    print(f"Created basic labeling with ID: {basic_labeling.id}")
    print(f"Default color: {basic_labeling.color}")
    
    return basic_labeling


def create_detailed_labeling() -> Labeling:
    """
    Example of creating a detailed labeling object with all parameters.
    
    Returns:
        Labeling: A detailed labeling object
    """
    # Sample labeling data structure
    data = {
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
    
    # Create a detailed labeling with all parameters
    detailed_labeling = Labeling(
        name="Detailed Activity Labels",
        color="#FF5733",  # Custom orange color
        visible=True,
        data=data,
        id="custom-id-123"
    )
    
    print(f"Created detailed labeling with name: {detailed_labeling.name}")
    print(f"Contains {len(detailed_labeling.data.get('timestamps', []))} label entries")
    
    return detailed_labeling


def update_labeling(labeling: Labeling) -> None:
    """
    Example of updating a labeling object.
    
    Args:
        labeling: The labeling object to update
    """
    print(f"Before update - Name: {labeling.name}, Color: {labeling.color}")
    
    # Update properties
    labeling.update(
        name="Updated Activity Labels",
        color="#33B5FF"  # Change to blue
    )
    
    print(f"After update - Name: {labeling.name}, Color: {labeling.color}")
    print(f"Updated at: {labeling.updated_at}")


def convert_to_from_dict() -> None:
    """
    Example of converting a labeling to and from a dictionary.
    """
    # Create a labeling
    labeling = Labeling(
        name="Activity Labels",
        color="#33FF57"  # Green
    )
    
    # Convert to dictionary
    labeling_dict = labeling.to_dict()
    print("Labeling as dictionary:")
    print(labeling_dict)
    
    # Convert back to labeling object
    reconstructed = Labeling.from_dict(labeling_dict)
    print("\nReconstructed labeling:")
    print(f"Name: {reconstructed.name}")
    print(f"ID: {reconstructed.id}")
    print(f"Color: {reconstructed.color}")


def handle_validation_errors() -> None:
    """
    Example of handling validation errors.
    """
    try:
        # Try to create a labeling with an invalid color
        invalid_labeling = Labeling(
            name="Invalid Labeling",
            color="not-a-color"  # Invalid color format
        )
    except LabelingValidationError as e:
        print(f"Validation error caught: {e}")
    
    try:
        # Create a valid labeling
        valid_labeling = Labeling(name="Valid Labeling")
        
        # Try to update with invalid data
        invalid_data = {
            "timestamps": [
                {
                    "start": 2000.0,
                    "end": 1000.0,  # Invalid: end before start
                    "label": "walking"
                }
            ]
        }
        valid_labeling.update(data=invalid_data)
    except LabelingValidationError as e:
        print(f"Validation error caught during update: {e}")


if __name__ == "__main__":
    print("=== Basic Labeling Example ===")
    basic = create_basic_labeling()
    print()
    
    print("=== Detailed Labeling Example ===")
    detailed = create_detailed_labeling()
    print()
    
    print("=== Updating Labeling Example ===")
    update_labeling(basic)
    print()
    
    print("=== Dictionary Conversion Example ===")
    convert_to_from_dict()
    print()
    
    print("=== Validation Error Handling Example ===")
    handle_validation_errors()
    print()
