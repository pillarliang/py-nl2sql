import json

from py_nl2sql.workflow import NL2SQLWorkflow
from py_nl2sql.db_instance import DBInstance
from py_nl2sql.models.llm import LLM

llm = LLM()
instance = DBInstance(
    db_type="mysql",
    db_name="bird",
    need_sql_sample=True,
    db_user="root",
    db_password="",
    db_host="127.0.0.1",
    db_port="3306",
    llm=llm,
)

with open("./mini_dev_mysql.json", "r") as file:
    data = json.load(file)

results = {}
print()

for index, item in enumerate(data[:30]):
    question = item["question"]
    db_id = item["db_id"]
    service = NL2SQLWorkflow(instance, question, llm)
    final_sql_query = service.final_sql_query
    result = f"{final_sql_query}\t----- bird -----\t{db_id}"
    print(result)
    results.update({f"{index}": result})

with open("results-all.json", "w") as outfile:
    json.dump(results, outfile, ensure_ascii=False, indent=4)
