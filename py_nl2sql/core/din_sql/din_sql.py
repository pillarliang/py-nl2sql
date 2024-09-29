"""
This system is based on the paper "DINSQL:
A Deep Interaction Network based Sequence-to-Sequence Model for Global Legal Judgment Prediction"
"""
from py_nl2sql.core.din_sql.prompts import (
    QUESTION_UNDERSTANDING,
    DIN_TASK_PROMPT,
    SubtaskName,
    SubtaskQuestion,
    SubtaskOutputFormat,
)
from py_nl2sql.core.din_sql.type import (
    DINQuestionUnderstanding,
    DINSelectResponse,
    DINFromResponse,
    DINGroupByResponse,
    DINHavingResponse,
    DINOrderByResponse,
    DINWhereResponse
)
from py_nl2sql.models.llm import LLM

class DINSQLWorkflow:
    def __init__(self, query: str):
        self.llm = LLM()
        self.query = query
        self.previous_selections = dict()

    def question_understanding(self) -> DINQuestionUnderstanding:
        """
        The first step in the workflow is to understand the question.
        The aim is to extract key points from the user's query.
        """
        llm_query = QUESTION_UNDERSTANDING.format(query=self.query)
        res = self.llm.get_structured_response(query=llm_query, response_format=DINQuestionUnderstanding)
        return res

    def task_decomposition(self, extracted_elements):
        """
        The second step in the workflow is to decompose the task.
        """

        subtasks = []

        # Task 1：Generate a SELECT clause
        if extracted_elements.get('select_columns'):
            subtasks.append(SubtaskName.SELECT)

        # Task 2：确定 FROM 子句
        if extracted_elements.get('tables'):
            subtasks.append(SubtaskName.FROM)

        # Task 3：构建 WHERE 子句
        # 假设条件中不包含聚合函数的部分用于 WHERE 子句
        where_conditions = []
        having_conditions = []
        if extracted_elements.get('conditions'):
            for condition in extracted_elements['conditions']:
                if any(func in condition.upper() for func in ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN']):
                    having_conditions.append(condition)
                else:
                    where_conditions.append(condition)
            if where_conditions:
                subtasks.append(SubtaskName.WHERE)

        # 子任务 4：构建 GROUP BY 子句
        if extracted_elements['operations'].get('group_by'):
            subtasks.append(SubtaskName.GROUP_BY)

        # 子任务 5：构建 HAVING 子句
        if having_conditions:
            subtasks.append(SubtaskName.HAVING)

        # 子任务 6：构建 ORDER BY 子句
        if extracted_elements['operations'].get('order_by'):
            subtasks.append(SubtaskName.ORDER_BY)

        return subtasks

    def _select_clause(self):
        select_prompt = DIN_TASK_PROMPT.format(
            user_query=self.query,
            previous_selections='',
            subtask_name=SubtaskName.SELECT,
            output_format=SubtaskOutputFormat.SELECT,
            subtask_question=SubtaskQuestion.SELECT,
        )
        res = self.llm.get_structured_response(query=select_prompt, response_format=DINSelectResponse)
        return res

    def _from_clause(self):
        from_prompt = DIN_TASK_PROMPT.format(
            user_query=self.query,
            previous_selections=self.previous_selections,
            subtask_name=SubtaskName.FROM,
            output_format=SubtaskOutputFormat.FROM,
            subtask_question=SubtaskQuestion.FROM,
        )
        res = self.llm.get_structured_response(query=from_prompt, response_format=DINFromResponse)
        return res

    def _where_clause(self):
        where_prompt = DIN_TASK_PROMPT.format(
            user_query=self.query,
            previous_selections=self.previous_selections,
            subtask_name=SubtaskName.WHERE,
            output_format=SubtaskOutputFormat.WHERE,
            subtask_question=SubtaskQuestion.WHERE,
        )
        res = self.llm.get_structured_response(query=where_prompt, response_format=DINWhereResponse)
        return res

    def _group_by_clause(self):
        group_by_prompt = DIN_TASK_PROMPT.format(
            user_query=self.query,
            previous_selections=self.previous_selections,
            subtask_name=SubtaskName.GROUP_BY,
            output_format=SubtaskOutputFormat.GROUP_BY,
            subtask_question=SubtaskQuestion.GROUP_BY,
        )
        res = self.llm.get_structured_response(query=group_by_prompt, response_format=DINGroupByResponse)
        return res

    def _having_clause(self):
        having_prompt = DIN_TASK_PROMPT.format(
            user_query=self.query,
            previous_selections=self.previous_selections,
            subtask_name=SubtaskName.HAVING,
            output_format=SubtaskOutputFormat.HAVING,
            subtask_question=SubtaskQuestion.HAVING,
        )
        res = self.llm.get_structured_response(query=having_prompt, response_format=DINHavingResponse)
        return res

    def _order_by_clause(self):
        order_by_prompt = DIN_TASK_PROMPT.format(
            user_query=self.query,
            previous_selections=self.previous_selections,
            subtask_name=SubtaskName.ORDER_BY,
            output_format=SubtaskOutputFormat.ORDER_BY,
            subtask_question=SubtaskQuestion.ORDER_BY,
        )
        res = self.llm.get_structured_response(query=order_by_prompt, response_format=DINOrderByResponse)
        return res

    def sub_task_resolution(self):
        select_clause = self._select_clause()
        self.previous_selections.update(select_clause)
        from_clause = self._from_clause()
        self.previous_selections.update(from_clause)
        where_clause = self._where_clause()
        self.previous_selections.update(where_clause)
        group_by_clause = self._group_by_clause()
        self.previous_selections.update(group_by_clause)
        having_clause = self._having_clause()
        self.previous_selections.update(having_clause)
        order_by_clause = self._order_by_clause()
        self.previous_selections.update(order_by_clause)
        return self.previous_selections

    def sql_assembly(self):
        # Build SELECT clause
        select_clause = f"SELECT {', '.join(self.previous_selections['select_columns'])}"

        # Build FROM clause
        from_clause = f"FROM {self.previous_selections['tables']}"

        # Build GROUP BY clause
        group_by_clause = ""
        if 'group_by_columns' in self.previous_selections:
            group_by_clause = f"GROUP BY {', '.join(self.previous_selections['group_by_columns'])}"

        # Build HAVING clause
        having_clause = ""
        if 'having_conditions' in self.previous_selections:
            having_clause = f"HAVING {' AND '.join(self.previous_selections['having_conditions'])}"

        # Build ORDER BY clause
        order_by_clause = ""
        if 'order_by' in self.previous_selections:
            order_by = self.previous_selections['order_by']
            order_by_clause = f"ORDER BY {order_by['column']} {order_by['direction']}"

        # Combine clauses
        sql_query = "\n".join([clause for clause in [
            select_clause,
            from_clause,
            group_by_clause,
            having_clause,
            order_by_clause
        ] if clause]) + ";"

        return sql_query

    def execute(self):
        extracted_elements = self.question_understanding()
        self.task_decomposition(extracted_elements)
        self.sub_task_resolution()
        res = self.sql_assembly()
        return res


if __name__ == "__main__":
    query = "Retrieve the names and total sales of all salespeople with sales exceeding 100,000, and sort the results in descending order of total sales."
    workflow = DINSQLWorkflow(query)
    res = workflow.execute()
    print(res)
