import logging
from py_nl2sql.relational_database.sql_database import SQLDatabase

logger = logging.getLogger(__name__)


class PostgreSQLConnector(SQLDatabase):
    """PostgreSQL connector."""

    driver = "postgresql+psycopg"
    db_type = "postgresql"
    port = 5432
