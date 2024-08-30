"""
Author: pillar
Date: 2024-08-30
Description: RetrievalService class for searching text chunks.
"""

import os
import threading
from functools import wraps


def db_singleton(cls):
    """Singleton decorator for database connectors."""
    instances = {}
    lock = threading.Lock()

    @wraps(cls)
    def get_instance(*args, **kwargs):
        db_type = kwargs.get('db_type') or os.getenv("LOCAL_DB_TYPE")
        db_name = kwargs.get('db_name') or os.getenv("LOCAL_DB_NAME")
        if not db_type or not db_name:
            raise ValueError("Database type and name must be provided.")

        key = (db_type, db_name)

        if key not in instances:  # First check (without lock)
            with lock:
                if key not in instances:
                    instances[key] = cls(*args, **kwargs)

        return instances[key]

    return get_instance


