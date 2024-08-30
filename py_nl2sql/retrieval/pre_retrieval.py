"""
Author: pillar
Date: 2024-08-30
Description: RetrievalService class for searching text chunks.
"""

from py_nl2sql.constants.prompts import DECOMPOSE_QUERY_FOR_SQL
from py_nl2sql.constants.type import RephraseQueryResponse, HydeResponse, DecomposeQueryResponse
from py_nl2sql.models.llm import LLM

"""
⚠️⚠️⚠️
This part of the effect accuracy has not been quantitatively analyzed, and is only used to run the demo. 
Actual use requires evaluation on the actual dataset to see which combination is better.
"""


class PreRetrievalService:
    llm = LLM()

    @classmethod
    def rephrase_sub_queries(cls, query: str) -> str:
        prompts = f"Please rephrase the question {query} to better suit the search. If {query} is a complex question, break it down into multiple sub-questions. If it can be broken down into sub-questions, the number of sub-questions cannot exceed 5."
        response = cls.llm.get_structured_response(prompts, RephraseQueryResponse)

        return response["rephrased_query"]

    @classmethod
    def hype(cls, query: str) -> str:
        prompts = f"Please provide a hypothetical answer to the question {query}. The answer should be concise and not require detailed explanations."
        response = cls.llm.get_structured_response(prompts, HydeResponse)
        return response["hyde"]

    @classmethod
    def decompose_for_sql(cls, query: str) -> DecomposeQueryResponse:
        response = cls.llm.get_structured_response(DECOMPOSE_QUERY_FOR_SQL.format(question=query), DecomposeQueryResponse)
        # convert dict to pydantic model
        return DecomposeQueryResponse(**response)

