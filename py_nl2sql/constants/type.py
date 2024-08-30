"""
Author: pillar
Date: 2024-08-30
Description: prompts
Note: Different languages should use prompts that are appropriate for that language.
"""
from pydantic import BaseModel
from typing import List
from enum import Enum


class RAGRequest(BaseModel):
    query: str
    chunks: List[str]


class RephraseQueryResponse(BaseModel):
    original_query: str
    rephrased_query: List[str]


class HydeResponse(BaseModel):
    original_query: str
    hyde: str


class DecomposeQueryResponse(BaseModel):
    text_to_sql_query: str
    interpretation_query: str


class GenerateSQLResponse(BaseModel):
    original_query: str
    sql_query: str


class GenerateSampleSQLResponse(BaseModel):
    sql_list: List[str]


class LLMModel(Enum):
    Default = "gpt-4o-mini"
    GPT_latest = "chatgpt-4o-latest"
    GPT_4o = "gpt-4o"
    GPT_4o_mini = "gpt-4o-mini"
    GPT_35 = "gpt-3.5-turbo"
    Moonshoot_v1_8k = "moonshot-v1-8k"


class RDBType(Enum):
    """Database type enumeration."""
    MySQL = "mysql"
    SQLite = "sqlite"
    Postgresql = "postgresql"
