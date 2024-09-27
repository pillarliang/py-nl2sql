from enum import Enum

user_query = "Retrieve the names and total sales of all salespeople with sales exceeding 100,000, and sort the results in descending order of total sales."


class SubtaskName(Enum):
    SELECT = "Generate the SELECT clause"


class SubtaskQuestion(Enum):
    SELECT = "Which columns and aggregation functions should be included in the SELECT clause?"


class SubtaskOutputFormat(Enum):
    SELECT = "Please provide the output in JSON format with the key 'select_columns'."


SELECT_PROMPT = """
You are an expert SQL query builder. Based on the user's request, perform the following subtask:

**Subtask:** {subtask_name}

User's request: "{user_query}"

Previous selections:
{previous_selections}

Question: {subtask_question}

{output_format}

Answer:
"""

