"""
Author: pillar
Date: 2024-08-30
Description: prompts
Note: Different languages should use prompts that are appropriate for that language.
"""


class NL2SQLPrompts:
    GENERATE_SQL = """
        You are a MySQL expert. 
    
        Given an input question, first create a syntactically correct MySQL query to run, then look at the results of the query and return the answer to the input question.
    
        Unless the user specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT clause as per MySQL. 
    
        You can order the results to return the most informative data in the database.
    
        Never query for all columns from a table. You must query only the columns that are needed to answer the question. 
        Wrap each column name in backticks (`) to denote them as delimited identifiers.
    
        Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
    
        Pay attention to use CURDATE() function to get the current date, if the question involves "today".
    
        Use the following format:
    
        Question: Question here
        SQLQuery: SQL Query to run
    
        Only use the following tables:
        {table_info}
    
        Question: {input}
    """

    GENERATE_SQL_WITH_SIMILARITY = """
        You are a MySQL expert. 
    
        Given an input question, first create a syntactically correct MySQL query to run, then look at the results of the query and return the answer to the input question.
    
        Unless the user specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT clause as per MySQL. 
    
        You can order the results to return the most informative data in the database.
    
        Never query for all columns from a table. You must query only the columns that are needed to answer the question. 
        Wrap each column name in backticks (`) to denote them as delimited identifiers.
    
        Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
    
        Pay attention to use CURDATE() function to get the current date, if the question involves "today".
    
        Use the following format:
    
        Question: Question here
        SQLQuery: SQL Query to run
    
    
        Only use the following tables:
        {table_info}
    
        Similarity SQL for reference:
        {similarity_sql}
    
        Question: {input}
    """

    SQL_QUERY_ANSWER = """
        Given the following user question, corresponding SQL query, and SQL result, answer the user question.
    
        Question: {question}
        SQL Query: {sql_query}
        SQL Result: {sql_result}
        Answer: 
    """


EN_RAG_PROMPTS = """
CONTEXTS:
{contexts}

QUESTION:
{question}

INSTRUCTIONS:
Answer the users QUESTION using the CONTEXTS text above.
Keep your answer ground in the facts of the DOCUMENT.
If the [CONTEXTS] doesn’t contain the facts to answer the QUESTION return NONE.
"""

CN_RAG_PROMPTS = """
上下文:
{contexts}

问题:
{question}

说明:
根据上下文回答问题，如果上下文无法回答问题，请返回:[暂找不到相关问题，请重新提供问题。]
"""


DECOMPOSE_QUERY_FOR_SQL = """
  Your task is to decompose the given question into the following two questions.

  1. Question in natural language that needs to be asked to retrieve results from the table.
  2. Question that needs to be asked on the top of the result from the first question to provide the final answer.

  Example:

  Input:
  How is the culture of countries whose population is more than 5000000

  Output:
  1. Get the reviews of countries whose population is more than 5000000
  2. Provide the culture of countries
  
  Question: {question}
"""


CREATE_SAMPLE_SQL_FROM_TABLE = """
You're a SQL expert. Given the DDL of a table and sample data in the table, write 1-5 representative SQL queries.
These SQL queries should cover all the data in the table and provide useful information.


Input: table information: {table_info}

Output: list of SQL queries
"""