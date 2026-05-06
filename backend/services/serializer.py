"""
services/serializer.py
Converts MongoDB documents (containing ObjectId, datetime, etc.) to
JSON-safe Python dicts. Used by all routers before returning responses.
"""
import json
from bson import ObjectId
from datetime import datetime, date


def mongo_to_dict(obj):
    """
    Recursively convert a MongoDB document (dict, list, ObjectId, datetime)
    to a plain Python dict/list/str that FastAPI can JSON-serialize.
    """
    if isinstance(obj, dict):
        return {k: mongo_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [mongo_to_dict(item) for item in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    else:
        return obj


class MongoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles ObjectId and datetime."""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)
