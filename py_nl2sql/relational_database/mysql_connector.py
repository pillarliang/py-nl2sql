import logging
from py_nl2sql.relational_database.sql_database import SQLDatabase

logger = logging.getLogger(__name__)


class MySQLConnector(SQLDatabase):
    """MySQL connector."""

    db_type: str = "mysql"
    driver: str = "mysql+pymysql"
    port: int = 3306
