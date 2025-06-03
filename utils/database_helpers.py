"""
Type-safe helper functions for database operations and row access.
"""
from typing import Dict, List, Any, Optional, cast


def safe_str(value: Any) -> str:
    """Safely convert a database value to string"""
    if value is None:
        return ""
    return str(value)


def safe_int(value: Any) -> int:
    """Safely convert a database value to int"""
    if value is None:
        return 0
    return int(value)


def safe_float(value: Any) -> float:
    """Safely convert a database value to float"""
    if value is None:
        return 0.0
    return float(value)


def safe_bool(value: Any) -> bool:
    """Safely convert a database value to bool"""
    if value is None:
        return False
    return bool(value)


def get_row_value(row: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a database row dictionary"""
    return row.get(key, default)


def get_row_str(row: Dict[str, Any], key: str, default: str = "") -> str:
    """Safely get a string value from a database row dictionary"""
    value = row.get(key, default)
    return safe_str(value)


def get_row_int(row: Dict[str, Any], key: str, default: int = 0) -> int:
    """Safely get an int value from a database row dictionary"""
    value = row.get(key, default)
    return safe_int(value)


def get_row_float(row: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Safely get a float value from a database row dictionary"""
    value = row.get(key, default)
    return safe_float(value)


def get_row_bool(row: Dict[str, Any], key: str, default: bool = False) -> bool:
    """Safely get a bool value from a database row dictionary"""
    value = row.get(key, default)
    return safe_bool(value)


def safe_fetchone_dict(cursor) -> Optional[Dict[str, Any]]:
    """Safely fetch one row as dictionary with proper typing"""
    row = cursor.fetchone()
    if row is None:
        return None
    # Convert to dict if needed - cursor should be in dictionary mode
    if isinstance(row, dict):
        return cast(Dict[str, Any], row)
    else:
        # Fallback for non-dict mode cursors
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))


def safe_fetchall_dict(cursor) -> List[Dict[str, Any]]:
    """Safely fetch all rows as dictionaries with proper typing"""
    rows = cursor.fetchall()
    if not rows:
        return []
    # Convert to list of dicts if needed
    if rows and isinstance(rows[0], dict):
        return cast(List[Dict[str, Any]], rows)
    else:
        # Fallback for non-dict mode cursors
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
