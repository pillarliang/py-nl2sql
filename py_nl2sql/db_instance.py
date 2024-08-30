import os
import threading
import logging

from py_nl2sql.constants.prompts import CREATE_SAMPLE_SQL_FROM_TABLE
from py_nl2sql.constants.type import GenerateSampleSQLResponse
from py_nl2sql.relational_database.sql_factory import rdb_factory
from py_nl2sql.vector_database.faiss_wrapper import FaissWrapper
from py_nl2sql.utilities.db_state_machine import NL2SQLStateMachine, NL2SQLState
from py_nl2sql.utilities.decorators import db_singleton
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@db_singleton
class DBInstance:
    """NL2SQL class for multiple instances of databases."""
    _state_machines: Dict[tuple, NL2SQLStateMachine] = {}
    _lock = threading.Lock()

    def __init__(
            self,
            llm,
            db_type: Optional[str] = None,
            db_name: Optional[str] = None,
            db_host: Optional[str] = None,
            db_port: Optional[str] = None,
            db_user: Optional[str] = None,
            db_password: Optional[str] = None,
            need_sql_sample: bool = False,
    ):
        self.db_type = db_type or os.getenv("LOCAL_DB_TYPE")
        self.db_name = db_name or os.getenv("LOCAL_DB_NAME")
        self.db_host = db_host or os.getenv("LOCAL_DB_HOST")
        self.db_port = db_port or os.getenv("LOCAL_DB_PORT")
        self.db_user = db_user or os.getenv("LOCAL_DB_USER")
        self.db_password = db_password if db_password is not None else os.getenv("LOCAL_DB_PASSWORD")

        self.db = rdb_factory(
            db_type=self.db_type,
            db_name=self.db_name,
            db_host=self.db_host,
            db_port=self.db_port,
            db_user=self.db_user,
            db_password=self.db_password,
        )

        self.llm = llm  # init LLM model
        self.db_summary = self.get_db_summary()
        self.summary_index = FaissWrapper(text_chunks=self.db_summary, embedding=self.llm.embedding_model)
        self.sql_example = need_sql_sample and llm and self._get_sql_example_llm()
        self.sql_example_index = need_sql_sample and llm and FaissWrapper(text_chunks=self.sql_example, embedding=self.llm.embedding_model)

        # init state machine
        self.db_key = (self.db_type, self.db_name)
        if self.db_key not in self._state_machines:
            with self._lock:
                if self.db_key not in self._state_machines:
                    self._state_machines[self.db_key] = NL2SQLStateMachine(self)

    def get_db_summary(self):
        """Get database summary used for constructing prompts."""
        return self.db.get_db_summary()

    @property
    def sql_example_llm(self):
        return self.sql_example

    def _get_sql_example_llm(self):
        """Get SQL example: ⚠️ Call LLM as many times as there are tables, should collect and organize representative SQL query examples to proxy each LLM generation"""

        table_info = self.db.get_table_info()
        table_info_list = table_info.split("\n\n\n")
        sample_sql = []

        for table in table_info_list:
            response = self.llm.get_structured_response(CREATE_SAMPLE_SQL_FROM_TABLE.format(table_info=table),
                                                        response_format=GenerateSampleSQLResponse)
            sample_sql.extend(response["sql_list"])

        return sample_sql

    def db_update(self):
        """Notify the state machine of a database update."""
        if self.db_key in self._state_machines and self._state_machines[self.db_key].db_state is not NL2SQLState.UPDATING:
            logger.info(f"Updating state machine for {self.db_key}")
            with self._lock:
                self._state_machines[self.db_key].on_notification()
        else:
            logger.error(f"No state machine found for {self.db_key}. Is the instance initialized?")
