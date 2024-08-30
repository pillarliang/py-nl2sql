import pytest
from py_nl2sql.workflow import NL2SQLWorkflow
from py_nl2sql.db_instance import DBInstance
from py_nl2sql.models.llm import LLM


def test_nl2sql_workflow():
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

    service = NL2SQLWorkflow(instance, query)

    res = service.get_response()

    assert res is not None, "The response should not be None"


if __name__ == "__main__":
    pytest.main()
