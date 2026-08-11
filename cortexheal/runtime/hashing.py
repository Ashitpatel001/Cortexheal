import hashlib
import json
from typing import Any

def _sort_dict(obj: Any) -> Any:
    """Recursively sorts dictionaries by key to ensure stable serialization."""
    if isinstance(obj, dict):
        return {k: _sort_dict(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [_sort_dict(x) for x in obj]
    else:
        return obj

def serialize(obj: Any) -> str:
    """
    Serializes an object into a stable, deterministic JSON string.
    Explicitly handles None, booleans, numbers, strings, lists, and dicts.
    """
    sorted_obj = _sort_dict(obj)
    # separators=(',', ':') removes whitespace
    return json.dumps(sorted_obj, separators=(',', ':'), sort_keys=True)

def deterministic_hash(obj: Any) -> str:
    """
    Returns a SHA-256 hash of the deterministic serialization of the object.
    Returns None if the object is None or empty.
    """
    if obj is None:
        return "null_hash"
    
    serialized = serialize(obj)
    if serialized == "{}" or serialized == "[]" or serialized == '""':
        return "empty_hash"
        
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
