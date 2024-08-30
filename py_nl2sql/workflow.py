import logging
from typing import Optional, List

from py_nl2sql.constants.prompts import NL2SQLPrompts
from py_nl2sql.constants.type import GenerateSQLResponse, RDBType
from py_nl2sql.retrieval.pre_retrieval import PreRetrievalService
from py_nl2sql.models.llm import LLM
from py_nl2sql.db_instance import DBInstance


logger = logging.getLogger(__name__)


class NL2SQLWorkflow:
    def __init__(self, db_instance: DBInstance, query: str, llm: LLM, need_similarity_sql: bool = True):
        self.db_instance = db_instance
        self.llm = llm  # init LLM model
        self.origin_query = query
        self.text_to_sql_query: Optional[str] = None  # used for sql generation
        self.interpretation_query: Optional[str] = None  # used for final response generation
        self.related_table_summary: Optional[str] = None  # Table information related to the query
        self.first_sql_query: Optional[str] = None  # SQL query generated from the query for the first time
        self.final_sql_query: Optional[str] = None  # SQL query generated from the query using the similarity SQL
        self.similarity_sql: Optional[List[str]] = None  #
        self.need_similarity_sql = need_similarity_sql
        self.sql_result: Optional[str] = None
        self.__init_basic_info()

    def __init_basic_info(self):
        self.related_table_summary = self._get_related_table_summary()
        query_response = PreRetrievalService.decompose_for_sql(self.origin_query)
        self.text_to_sql_query = query_response.text_to_sql_query
        self.interpretation_query = query_response.interpretation_query
        self.first_sql_query = self._get_first_sql_query()
        self.similarity_sql = self._get_similarity_query()
        self.final_sql_query = self._get_final_sql_query()
        self.sql_result = self._get_sql_result()

    def _get_related_table_summary(self, top_k: int = 5):
        """Get related chunks based on the query."""
        return self.db_instance.summary_index.search_for_chunks(self.origin_query, top_k=top_k)

    def _get_first_sql_query(self):
        """Get SQL query from the given query."""
        if self.text_to_sql_query:
            return self.text_to_sql_query

        sql_res = self.llm.get_structured_response(
            NL2SQLPrompts.GENERATE_SQL.format(table_info=self.related_table_summary, input=self.text_to_sql_query),
            response_format=GenerateSQLResponse,
        )

        self.first_sql_query = sql_res["sql_query"]
        logging.info(f"sql_query:{self.first_sql_query}")
        return self.first_sql_query

    def _get_similarity_query(self, top_k: int = 5) -> List[str]:
        """Get similar SQL query based on the query."""
        return self.db_instance.sql_example_index.search_for_chunks(self.first_sql_query, top_k)

    def _get_final_sql_query(self):
        """Get the final SQL query."""
        if self.final_sql_query:
            return self.final_sql_query

        if not self.need_similarity_sql:
            self.final_sql_query = self.first_sql_query
            return self.final_sql_query

        self.final_sql_query = self.llm.get_structured_response(
            NL2SQLPrompts.GENERATE_SQL_WITH_SIMILARITY.format(
                table_info=self.related_table_summary,
                input=self.text_to_sql_query,
                similarity_sql=self.similarity_sql,
            ), response_format=GenerateSQLResponse,
        )["sql_query"]

        return self.final_sql_query

    def _get_sql_result(self):
        """executing the sql query."""
        logging.info(f"sql_query:{self.final_sql_query}")
        return self.db_instance.db.run_no_throw(self.final_sql_query)

    def get_response(self):
        """Get response based on the query."""
        llm_res = self.llm.get_response(
            query=NL2SQLPrompts.SQL_QUERY_ANSWER.format(question=self.origin_query, sql_query=self.final_sql_query, sql_result=self.sql_result))

        return llm_res
    