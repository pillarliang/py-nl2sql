"""SQLAlchemy wrapper around a database.

This file uses the following code:
Copyright (c) [Langchain]
https://github.com/langchain-ai

"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Union
from urllib.parse import quote
from urllib.parse import quote_plus as urlquote
import sqlalchemy
from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import URL, Engine, Result
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql.expression import Executable
from sqlalchemy.types import NullType


def _format_index(index: sqlalchemy.engine.interfaces.ReflectedIndex) -> str:
    return (
        f'Name: {index["name"]}, Unique: {index["unique"]},'
        f' Columns: {str(index["column_names"])}'
    )


def truncate_word(content: Any, *, length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a certain number of words, based on the max string
    length.
    """

    if not isinstance(content, str) or length <= 0:
        return content

    if len(content) <= length:
        return content

    return content[: length - len(suffix)].rsplit(" ", 1)[0] + suffix

class SQLDatabase:
    """SQLAlchemy wrapper around a database."""
    driver: str = ""
    port: int = 0

    def __init__(
        self,
        engine: Engine,
        schema: Optional[str] = None,
        metadata: Optional[MetaData] = None,
        ignore_tables: Optional[List[str]] = None,
        include_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
        indexes_in_table_info: bool = False,
        custom_table_info: Optional[dict] = None,
        view_support: bool = False,
        max_string_length: int = 300,
        lazy_table_reflection: bool = False,
    ):
        """Create engine from database URI."""
        self._engine = engine
        self._schema = schema
        if include_tables and ignore_tables:
            raise ValueError("Cannot specify both include_tables and ignore_tables")

        self._inspector = inspect(self._engine)

        # including view support by adding the views as well as tables to the all
        # tables list if view_support is True
        self._all_tables = set(
            self._inspector.get_table_names(schema=schema)
            + (self._inspector.get_view_names(schema=schema) if view_support else [])
        )

        self._include_tables = set(include_tables) if include_tables else set()
        if self._include_tables:
            missing_tables = self._include_tables - self._all_tables
            if missing_tables:
                raise ValueError(
                    f"include_tables {missing_tables} not found in database"
                )
        self._ignore_tables = set(ignore_tables) if ignore_tables else set()
        if self._ignore_tables:
            missing_tables = self._ignore_tables - self._all_tables
            if missing_tables:
                raise ValueError(
                    f"ignore_tables {missing_tables} not found in database"
                )
        usable_tables = self.get_usable_table_names()
        self._usable_tables = set(usable_tables) if usable_tables else self._all_tables

        if not isinstance(sample_rows_in_table_info, int):
            raise TypeError("sample_rows_in_table_info must be an integer")

        self._sample_rows_in_table_info = sample_rows_in_table_info
        self._indexes_in_table_info = indexes_in_table_info

        self._custom_table_info = custom_table_info
        if self._custom_table_info:
            if not isinstance(self._custom_table_info, dict):
                raise TypeError(
                    "table_info must be a dictionary with table names as keys and the "
                    "desired table info as values"
                )
            # only keep the tables that are also present in the database
            intersection = set(self._custom_table_info).intersection(self._all_tables)
            self._custom_table_info = dict(
                (table, self._custom_table_info[table])
                for table in self._custom_table_info
                if table in intersection
            )

        self._max_string_length = max_string_length
        self._view_support = view_support

        self._metadata = metadata or MetaData()
        if not lazy_table_reflection:
            # including view support if view_support = true
            self._metadata.reflect(
                views=view_support,
                bind=self._engine,
                only=list(self._usable_tables),
                schema=self._schema,
            )

    @classmethod
    def from_uri_db(
        cls,
        host: str,
        user: str,
        password: str,
        db_name: str,
        port: Optional[str] = None,
        engine_args: Optional[dict] = None,
        **kwargs: Any,
    ) -> SQLDatabase:
        """🌟@by:pillar 🌟
        Construct a SQLAlchemy engine from uri database.

        Args:
            host (str): database host.
            port (int): database port
            user (str): database user.
            password (str): database password.
            db_name (str): database name.
            engine_args (Optional[dict]):other engine_args.
        """
        selected_port = str(port) if port else str(cls.port)
        db_url: str = (
            f"{cls.driver}://{quote(user)}:{urlquote(password)}@{host}:{selected_port}/{db_name}"
        )
        return cls.from_uri(db_url, engine_args, **kwargs)

    def get_columns(self, table_name: str) -> list:
        """Get columns about specified table.
         🌟Developed by pillar🌟

        Args:
            table_name (str): table name

        Returns:
            columns: List[Dict], which contains name: str, type: str,
                default_expression: str, is_in_primary_key: bool, comment: str
                eg:[
                    {'name': 'id', 'type': 'int', 'default_expression': '', 'is_in_primary_key': True, 'comment': 'id'},
                    ...
                ]
        """
        return self._inspector.get_columns(table_name)  # sqlalchem native method. We can get the column, constraint, index and other information of the database table through inspect.

    def get_indexes(self, table_name: str) -> List[Dict]:
        """Get table indexes about specified table.
        🌟Developed by pillar🌟
        Args:
            table_name:(str) table name

        Returns:
            List[Dict]:eg:[{'name': 'idx_key', 'column_names': ['id']}] # name: the name of index, column_names: the column names that the index is on
        """
        return self._inspector.get_indexes(table_name)

    def get_table_comment(self, table_name: str) -> Dict:
        """Get table comments.
        🌟Developed by pillar🌟
        Args:
            table_name (str): table name
        Returns:
            comment: Dict, which contains text: Optional[str], eg:["text": "comment"]
        """
        return self._inspector.get_table_comment(table_name)

    def get_db_summary(self) -> List[str]:
        """Get db summary for database.
        🌟Developed by pillar🌟

        """
        summary_template: str = "{table_name}({columns})"
        tables = self.get_usable_table_names()
        db_info_summaries = [
            self._parse_table_summary(summary_template, table_name)
            for table_name in tables
        ]
        return db_info_summaries

    def _parse_table_summary(
            self, summary_template: str, table_name: str
    ) -> str:
        """Get table summary for table.
        🌟Developed by pillar🌟

        Args:
            summary_template (str): summary template
            table_name (str): table name

        Examples:
            table_name(column1(column1 comment),column2(column2 comment),
            column3(column3 comment) and index keys, and table comment: {table_comment})
        """
        columns = []
        for column in self.get_columns(table_name):
            if column.get("comment"):
                columns.append(f"{column['name']} ({column.get('comment')})")
            else:
                columns.append(f"{column['name']}")

        column_str = ", ".join(columns)
        # Obtain index information
        index_keys = []
        raw_indexes = self.get_indexes(table_name)
        for index in raw_indexes:
            if isinstance(index, tuple):  # Process tuple type index information
                index_name, index_creation_command = index
                # Extract column names using re
                matched_columns = re.findall(r"\(([^)]+)\)", index_creation_command)
                if matched_columns:
                    key_str = ", ".join(matched_columns)
                    index_keys.append(f"{index_name}(`{key_str}`) ")
            else:
                key_str = ", ".join(index["column_names"])
                index_keys.append(f"{index['name']}(`{key_str}`) ")
        table_str = summary_template.format(table_name=table_name, columns=column_str)
        if len(index_keys) > 0:
            index_key_str = ", ".join(index_keys)
            table_str += f", and index keys: {index_key_str}"
        try:
            comment = self.get_table_comment(table_name)
        except Exception:
            comment = dict(text=None)
        if comment.get("text"):
            table_str += f", and table comment: {comment.get('text')}"
        return table_str

    @classmethod
    def from_uri(
        cls,
        database_uri: Union[str, URL],
        engine_args: Optional[dict] = None,
        **kwargs: Any,
    ) -> SQLDatabase:
        """Construct a SQLAlchemy engine from URI."""
        _engine_args = engine_args or {}
        return cls(create_engine(database_uri, **_engine_args), **kwargs)

    @property
    def dialect(self) -> str:
        """Return string representation of dialect to use."""
        return self._engine.dialect.name

    def get_usable_table_names(self) -> Iterable[str]:
        """Get names of tables available."""
        if self._include_tables:
            return sorted(self._include_tables)
        return sorted(self._all_tables - self._ignore_tables)

    @property
    def table_info(self) -> str:
        """Information about all tables in the database."""
        return self.get_table_info()

    def get_table_info(self, table_names: Optional[List[str]] = None) -> str:
        """Get information about specified tables.

        Follows best practices as specified in: Rajkumar et al, 2022
        (https://arxiv.org/abs/2204.00498)

        If `sample_rows_in_table_info`, the specified number of sample rows will be
        appended to each table description. This can increase performance as
        demonstrated in the paper.
        """
        all_table_names = self.get_usable_table_names()
        if table_names is not None:
            missing_tables = set(table_names).difference(all_table_names)
            if missing_tables:
                raise ValueError(f"table_names {missing_tables} not found in database")
            all_table_names = table_names

        metadata_table_names = [tbl.name for tbl in self._metadata.sorted_tables]
        to_reflect = set(all_table_names) - set(metadata_table_names)
        if to_reflect:
            self._metadata.reflect(
                views=self._view_support,
                bind=self._engine,
                only=list(to_reflect),
                schema=self._schema,
            )

        meta_tables = [
            tbl
            for tbl in self._metadata.sorted_tables
            if tbl.name in set(all_table_names)
            and not (self.dialect == "sqlite" and tbl.name.startswith("sqlite_"))
        ]

        tables = []
        for table in meta_tables:
            if self._custom_table_info and table.name in self._custom_table_info:
                tables.append(self._custom_table_info[table.name])
                continue

            # Ignore JSON datatyped columns
            for k, v in table.columns.items():  # AttributeError: items in sqlalchemy v1
                if type(v.type) is NullType:
                    table._columns.remove(v)

            # add create table command
            create_table = str(CreateTable(table).compile(self._engine))
            table_info = f"{create_table.rstrip()}"
            has_extra_info = (
                self._indexes_in_table_info or self._sample_rows_in_table_info
            )
            if has_extra_info:
                table_info += "\n\n/*"
            if self._indexes_in_table_info:
                table_info += f"\n{self._get_table_indexes(table)}\n"
            if self._sample_rows_in_table_info:
                table_info += f"\n{self._get_sample_rows(table)}\n"
            if has_extra_info:
                table_info += "*/"
            tables.append(table_info)
        tables.sort()
        final_str = "\n\n".join(tables)
        return final_str

    def _get_table_indexes(self, table: Table) -> str:
        indexes = self._inspector.get_indexes(table.name)
        indexes_formatted = "\n".join(map(_format_index, indexes))
        return f"Table Indexes:\n{indexes_formatted}"

    def _get_sample_rows(self, table: Table) -> str:
        # build the select command
        command = select(table).limit(self._sample_rows_in_table_info)

        # save the columns in string format
        columns_str = "\t".join([col.name for col in table.columns])

        try:
            # get the sample rows
            with self._engine.connect() as connection:
                sample_rows_result = connection.execute(command)  # type: ignore
                # shorten values in the sample rows
                sample_rows = list(
                    map(lambda ls: [str(i)[:100] for i in ls], sample_rows_result)
                )

            # save the sample rows in string format
            sample_rows_str = "\n".join(["\t".join(row) for row in sample_rows])

        # in some dialects when there are no rows in the table a
        # 'ProgrammingError' is returned
        except ProgrammingError:
            sample_rows_str = ""

        return (
            f"{self._sample_rows_in_table_info} rows from {table.name} table:\n"
            f"{columns_str}\n"
            f"{sample_rows_str}"
        )

    def _execute(
        self,
        command: Union[str, Executable],
        fetch: Literal["all", "one", "cursor"] = "all",
        *,
        parameters: Optional[Dict[str, Any]] = None,
        execution_options: Optional[Dict[str, Any]] = None,
    ) -> Union[Sequence[Dict[str, Any]], Result]:
        """
        Executes SQL command through underlying engine.

        If the statement returns no rows, an empty list is returned.
        """
        parameters = parameters or {}
        execution_options = execution_options or {}
        with self._engine.begin() as connection:  # type: Connection  # type: ignore[name-defined]
            if self._schema is not None:
                if self.dialect == "snowflake":
                    connection.exec_driver_sql(
                        "ALTER SESSION SET search_path = %s",
                        (self._schema,),
                        execution_options=execution_options,
                    )
                elif self.dialect == "bigquery":
                    connection.exec_driver_sql(
                        "SET @@dataset_id=?",
                        (self._schema,),
                        execution_options=execution_options,
                    )
                elif self.dialect == "mssql":
                    pass
                elif self.dialect == "trino":
                    connection.exec_driver_sql(
                        "USE ?",
                        (self._schema,),
                        execution_options=execution_options,
                    )
                elif self.dialect == "duckdb":
                    # Unclear which parameterized argument syntax duckdb supports.
                    # The docs for the duckdb client say they support multiple,
                    # but `duckdb_engine` seemed to struggle with all of them:
                    # https://github.com/Mause/duckdb_engine/issues/796
                    connection.exec_driver_sql(
                        f"SET search_path TO {self._schema}",
                        execution_options=execution_options,
                    )
                elif self.dialect == "oracle":
                    connection.exec_driver_sql(
                        f"ALTER SESSION SET CURRENT_SCHEMA = {self._schema}",
                        execution_options=execution_options,
                    )
                elif self.dialect == "sqlany":
                    # If anybody using Sybase SQL anywhere database then it should not
                    # go to else condition. It should be same as mssql.
                    pass
                elif self.dialect == "postgresql":  # postgresql
                    connection.exec_driver_sql(
                        "SET search_path TO %s",
                        (self._schema,),
                        execution_options=execution_options,
                    )

            if isinstance(command, str):
                command = text(command)
            elif isinstance(command, Executable):
                pass
            else:
                raise TypeError(f"Query expression has unknown type: {type(command)}")
            cursor = connection.execute(
                command,
                parameters,
                execution_options=execution_options,
            )

            if cursor.returns_rows:
                if fetch == "all":
                    result = [x._asdict() for x in cursor.fetchall()]
                elif fetch == "one":
                    first_result = cursor.fetchone()
                    result = [] if first_result is None else [first_result._asdict()]
                elif fetch == "cursor":
                    return cursor
                else:
                    raise ValueError(
                        "Fetch parameter must be either 'one', 'all', or 'cursor'"
                    )
                return result
        return []

    def run(
        self,
        command: Union[str, Executable],
        fetch: Literal["all", "one", "cursor"] = "all",
        include_columns: bool = False,
        *,
        parameters: Optional[Dict[str, Any]] = None,
        execution_options: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Sequence[Dict[str, Any]], Result[Any]]:
        """Execute a SQL command and return a string representing the results.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.
        """
        result = self._execute(
            command, fetch, parameters=parameters, execution_options=execution_options
        )

        if fetch == "cursor":
            return result

        res = [
            {
                column: truncate_word(value, length=self._max_string_length)
                for column, value in r.items()
            }
            for r in result
        ]

        if not include_columns:
            res = [tuple(row.values()) for row in res]  # type: ignore[misc]

        if not res:
            return ""
        else:
            return str(res)

    def get_table_info_no_throw(self, table_names: Optional[List[str]] = None) -> str:
        """Get information about specified tables.

        Follows best practices as specified in: Rajkumar et al, 2022
        (https://arxiv.org/abs/2204.00498)

        If `sample_rows_in_table_info`, the specified number of sample rows will be
        appended to each table description. This can increase performance as
        demonstrated in the paper.
        """
        try:
            return self.get_table_info(table_names)
        except ValueError as e:
            """Format the error message"""
            return f"Error: {e}"

    def run_no_throw(
        self,
        command: str,
        fetch: Literal["all", "one"] = "all",
        include_columns: bool = False,
        *,
        parameters: Optional[Dict[str, Any]] = None,
        execution_options: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Sequence[Dict[str, Any]], Result[Any]]:
        """Execute a SQL command and return a string representing the results.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.

        If the statement throws an error, the error message is returned.
        """
        try:
            return self.run(
                command,
                fetch,
                parameters=parameters,
                execution_options=execution_options,
                include_columns=include_columns,
            )
        except SQLAlchemyError as e:
            """Format the error message"""
            return f"Error: {e}"

    def get_context(self) -> Dict[str, Any]:
        """Return db context that you may want in agent prompt."""
        table_names = list(self.get_usable_table_names())
        table_info = self.get_table_info_no_throw()
        return {"table_info": table_info, "table_names": ", ".join(table_names)}
