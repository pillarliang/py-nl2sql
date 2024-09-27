"""
Author: pillar
Date: 2024-09-27
"""
from pydantic import BaseModel
from typing import List


class OrderBy(BaseModel):
    column: str
    direction: str


class SQLOperation(BaseModel):
    aggregation: bool
    group_by: List[str]
    order_by: OrderBy


class DINQuestionUnderstanding(BaseModel):
    tables: List[str]
    select_columns: List[str]
    conditions: List[str]
    operations: SQLOperation


class DINSQLResponse(BaseModel):
    sql: str
    subtasks: List[str]


class DINSelectResponse(BaseModel):
    select_columns: List[str]


class DINFromResponse(BaseModel):
    tables: List[str]


class DINWhereResponse(BaseModel):
    where_conditions: List[str]


class DINGroupByResponse(BaseModel):
    group_by_columns: List[str]


class DINHavingResponse(BaseModel):
    having_conditions: List[str]


class DINOrderByResponse(BaseModel):
    order_by: OrderBy
