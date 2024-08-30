from typing import Dict, Type, Optional
from py_nl2sql.constants.type import RDBType
from py_nl2sql.relational_database.mysql_connector import MySQLConnector
from py_nl2sql.relational_database.postgresql_connector import PostgreSQLConnector
from py_nl2sql.relational_database.sql_database import SQLDatabase


def create_connector(connector_class: Type[SQLDatabase], db_host: str, db_port: str, db_user: str, db_password: str, db_name: str):
    """create database connector instance."""
    return connector_class.from_uri_db(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        db_name=db_name,
    )


def rdb_factory(
        db_type: str,
        db_name: str,
        db_host: Optional[str] = None,
        db_port: Optional[str] = None,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
):
    """Relational Database Factory. Create a database connector instance based on the database type.
    :param:
        db_type (str)
        db_host (str, optional)
        db_port (str, optional)
        db_user (str, optional)
        db_password (str, optional)
        db_name (str, optional)
    :raises:
        ValueError: If the db_type is not supported.
    """
    connector_map: Dict[str, Type[SQLDatabase]] = {
        RDBType.MySQL.value: MySQLConnector,
        RDBType.Postgresql.value: PostgreSQLConnector,
    }
    connector_class = connector_map.get(db_type)
    if connector_class:
        return create_connector(connector_class, db_host, db_port, db_user, db_password, db_name)
    else:
        raise ValueError(f"Unknown db_type: {db_type}. Supported types are: {', '.join(connector_map.keys())}.")
