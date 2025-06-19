class DatabaseError(Exception):
    """Raised when database operations fail"""
    pass

class ValidationError(Exception):
    """Raised when data validation fails"""
    pass