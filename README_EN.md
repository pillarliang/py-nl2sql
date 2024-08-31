# PY-NL2SQL: A Python library for out-of-the-box natural language to SQL query generation


<div align="center">
  <p>
    <a href="https://opensource.org/licenses/MIT">
      <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" />
    </a>
     <a href="https://github.com/pillarliang/py-nl2sql/releases">
      <img alt="Release Notes" src="https://img.shields.io/github/release/pillarliang/py-nl2sql" />
    </a>
    <a href="https://github.com/eosphoros-ai/DB-GPT/issues">
      <img alt="Open Issues" src="https://img.shields.io/github/issues-raw/pillarliang/py-nl2sql" />
    </a>
    <a href="https://codespaces.new/pillarliang/py-nl2sql">
      <img alt="Open in GitHub Codespaces" src="https://github.com/codespaces/badge.svg" />
    </a>
  </p>

[**English**](README_EN.md) | [**中文**](README.md)
</div>


## Table of Contents
- [Architecture](#Architecture)

- [Install and Usage](#Install_and_Usage)

- [User Guide](#User_Guide)

## Architecture

<p align="center">
  <img src="./assets/nl2sql_structure.png" width="800px" />
</p>


## Install_and_Usage
```python
# pip install py_nl2sql  
from py_nl2sql import LLM,DBInstance,NL2SQLWorkflow

llm = LLM() 
instance = DBInstance(
    db_type="mysql",     
    db_name="classicmodels",     
    need_sql_sample=True,     
    db_user="root",     
    db_password="",     
    db_host="127.0.0.1",     
    db_port="3306",     
    llm=llm, 
   )  
query = "what is price of `1968 Ford Mustang`" 
service = NL2SQLWorkflow(instance, query, llm)
res = service.get_response() 
print(res)
```
## User_Guide
When using this project, users need to provide the following three pieces of information:
### 1. OpenAI Key

Users can provide `api_key` and `base_url` in two ways: directly pass the parameters, or set `OPENAI_API_KEY` and `OPENAI_BASE_URL` in the environment variables.

- Currently, the large model used in this project is only compatible with OpenAI models, and local models and other models will be supported in the future.
- Due to the need to use OpenAI's structured output feature, the default model is set to `gpt-4o-mini`.
 ```python
  from py_nl2sql.models.llm import LLM base_url
  
  llm = LLM(api_key="sk-xx",base_url="https://xxx")
 ```

### 2. Database Configuration Information

When creating a new database instance, you need to pass in the LLM (Large Language Model). During the instantiation process, the following operations will be executed:

1. Use the embedding model to embed the database table information and store the results in the vector database (this step is mandatory).
2. Generate sample SQL based on the database information, which will serve as a reference for converting user queries into SQL later (this step is optional). By default, this feature is enabled; if you do not need to generate sample SQL, you can set `need_sql_sample` to `False`.

 ```python
 instance = DBInstance(
     db_type="mysql",
     db_name="classicmodels",
     need_sql_sample=True,
     db_user="root",
     db_password="",
     db_host="127.0.0.1",
     db_port="3306",
     llm=llm,
 )
 ```

Features:

1. Supports the initialization of multiple database instances for management in scenarios with multiple databases.
2. If there are changes to the database, you can directly call the `instance.db_update()` method to update the database. During the update process, the database table information will be re-embedded and stored in the vector database.

Note:

The design of DBInstance adopts a multi-instance pattern combined with a state machine. Different objects are instantiated based on db_type + db_name.


### 3. User Query

User only needs to pass the database instance to be queried and the corresponding query statement, and then call the `get_response()` method to get the final result.

```python
service = NL2SQLWorkflow(instance, query) 
res = service.get_response()
```

Meantime, the NL2SQLWorkflow object saves a series of intermediate process metadata, such as
```
service.text_to_sql_query # used for sql generation
service.interpretation_query # used for final response generation
service.related_table_summary  # Table information related to the query
service.first_sql_query  # SQL query generated from the query for the first time
service.final_sql_query  # SQL query generated from the query using the similarity SQL
...
```

## Licence

The MIT License (MIT)
