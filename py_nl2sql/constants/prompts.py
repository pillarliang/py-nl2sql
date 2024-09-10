"""
Author: pillar
Date: 2024-08-30
Description: prompts
Note: Different languages should use prompts that are appropriate for that language.
"""


class NL2SQLPrompts:
    GENERATE_SQL = """
    You are a database expert. 
    Please create a syntactically correct SQL query based on the user's question and some of the available table structure definitions of the database.

    Table structure information:
        {table_info}
        
    Constraint:
    1.Please understand the user's intention based on the user's question, and use the given table structure definition to create a grammatically correct {dialect} sql. 
    2.You can only use the tables provided in the table structure information to generate sql. If you cannot generate sql based on the provided table structure, please say: "The table structure information provided is not enough to generate sql queries." It is prohibited to fabricate information at will.
    3.Please be careful not to mistake the relationship between tables and columns when generating SQL.
    4.Please check the correctness of the SQL and ensure that the query performance is optimized under correct conditions. Your returned SQL should start with the `SELECT` keyword.
     
    User Question:
        {input}
    Please think step by step and ensure the response is correct json and can be parsed by Python json.loads.
    """

    GENERATE_SQL_WITH_SIMILARITY_SQL = """
    You are a database expert. 
    Please create a syntactically correct SQL query based on the user's question and some of the available table structure definitions of the database, and some related SQl.

    Table structure information:
        {table_info}
    Related SQL:
        {similarity_sql}
        
    Constraint:
    1.Please understand the user's intention based on the user's question, and use the given table structure definition and related SQls to create a grammatically correct {dialect} sql. 
    2.You can only use the tables provided in the table structure information to generate sql. If you cannot generate sql based on the provided table structure, please say: "The table structure information provided is not enough to generate sql queries." It is prohibited to fabricate information at will.
    3.Please be careful not to mistake the relationship between tables and columns when generating SQL.
    4.Please check the correctness of the SQL and ensure that the query performance is optimized under correct conditions. Your returned SQL should start with the `SELECT` keyword.
     
    User Question:
        {input}
    Please think step by step and ensure the response is correct json and can be parsed by Python json.loads.
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