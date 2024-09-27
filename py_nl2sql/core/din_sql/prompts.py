

from enum import Enum

user_query = "Retrieve the names and total sales of all salespeople with sales exceeding 100,000, and sort the results in descending order of total sales."

QUESTION_UNDERSTANDING = """
You are a professional database analyst skilled at extracting key information from natural language queries.

The user's query is: {query}

Please extract the following information from the query:

1. **Target Columns (Select Columns)** (The fields or values to be selected or calculated)
2. **Involved Tables (Tables)**
3. **Filtering Conditions (Conditions)** (WHERE conditions)
4. **Operations (Operations)** (Such as aggregate functions, sorting, grouping, etc.)
"""


class SubtaskName(Enum):
    SELECT = "Generate the SELECT clause"
    FROM = "Determine the FROM clause"
    WHERE = "Construct the WHERE clause"
    GROUP_BY = "Construct the GROUP BY clause"
    HAVING = "Construct the HAVING clause"
    ORDER_BY = "Construct the ORDER BY clause"


class SubtaskQuestion(Enum):
    SELECT = "Which columns and aggregation functions should be included in the SELECT clause?"
    FROM = "Which table should be used in the FROM clause?"
    WHERE = "Is a WHERE clause needed? If so, which conditions should it contain?"
    GROUP_BY = "Is a GROUP BY clause needed? If so, which columns should be used for grouping?"
    HAVING = "Is a HAVING clause needed? If so, which conditions should it contain?"
    ORDER_BY = "Is an ORDER BY clause needed? If so, how should the results be ordered?"


class SubtaskOutputFormat(Enum):
    SELECT = "Please provide the output in JSON format with the key 'select_columns'."
    FROM = "Please provide the output in JSON format with the key 'tables'."
    WHERE = "Please provide the output in JSON format with the key 'where_conditions'."
    GROUP_BY = "Please provide the output in JSON format with the key 'group_by_columns'."
    HAVING = "Please provide the output in JSON format with the key 'having_conditions'."
    ORDER_BY = "Please provide the output in JSON format with the key 'order_by'."


DIN_TASK_PROMPT = """
You are an expert SQL query builder. Based on the user's request, perform the following subtask:

**Subtask:** {subtask_name}

User's request: "{user_query}"

Previous selections:
{previous_selections}

Question: {subtask_question}

{output_format}

Answer:
"""

