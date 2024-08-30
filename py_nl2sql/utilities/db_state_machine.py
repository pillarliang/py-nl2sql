"""
Author: pillar
Date: 2024-08-30
Description: RetrievalService class for searching text chunks.
"""

from enum import Enum, auto
import logging

from py_nl2sql.vector_database.faiss_wrapper import FaissWrapper

logger = logging.getLogger(__name__)


class NL2SQLState(Enum):
    INITIALIZED = auto()
    UPDATING = auto()
    COMPLETED = auto()


class NL2SQLStateMachine:
    """
    TODO: State Machine is not the best strategy for this use case.
    It is better to use a Observe subscriber pattern.
    """
    def __init__(self, db_instance):
        self.state = NL2SQLState.INITIALIZED
        self.db_instance = db_instance

    def on_notification(self):
        """Method to call when a notification of change is received."""
        logger.info(f"Notification received for {self.db_instance.db_name}. Updating instance...")
        self.state = NL2SQLState.UPDATING
        self.update_db_instance()

    def update_db_instance(self):
        """Update the instance with new database information."""
        self.db_instance.db_summary = self.db_instance.get_db_summary()
        self.db_instance.vector_index = FaissWrapper(text_chunks=self.db_instance.db_summary)
        logger.info(f"Instance for {self.db_instance.db_name} updated.")
        self.state = NL2SQLState.COMPLETED

    @property
    def db_state(self) -> NL2SQLState:
        return self.state
