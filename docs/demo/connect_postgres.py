from py_nl2sql.vector_database import PGVectorWrapper,PGVectorBase
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, declarative_base
from pgvector.sqlalchemy import Vector
import uuid
import logging
import os

from py_nl2sql.constants.type import RDBType
from py_nl2sql.relational_database.sql_factory import create_rdb

logger = logging.getLogger(__name__)


def get_db_result(query: str):

    class VectorStore(PGVectorBase):
        __tablename__ = 'customer01w'
        id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        content: Mapped[str] = mapped_column(Text)
        additional_metadata: Mapped[dict] = mapped_column(JSON)
        embedding: Mapped[list] = mapped_column(Vector(1536))

    # 从环境变量获取数据库连接信息
    db_instance = create_rdb(
        db_type=RDBType.Postgresql,
        db_name=os.getenv("DB_NAME", "nl2sql"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_user=os.getenv("DB_USER", "liangzhu"),
        db_password=os.getenv("DB_PASSWORD", ""),
    )

    PGVectorBase.metadata.create_all(db_instance.engine)

    query = "清华大学"
    text_chunk = [
        "他来到了网易杭研大厦",
        "我来到北京清华大学",
        "小明硕士毕业于中国科学院计算所",
        "我爱北京天安门",
    ]
    pgvector_wrapper = PGVectorWrapper(text_chunks=text_chunk, table_cls=VectorStore, embedding=OpenAIEmbeddings(), db_instance=db_instance)
    # pgvector_wrapper = PGVectorWrapper(table_cls=VectorStore, embedding=OpenAIEmbeddings(), db_instance=db_instance)
    sorted_chunks = pgvector_wrapper.search_for_chunks(query, top_k=1)
    print(sorted_chunks)
    return sorted_chunks


get_db_result("清华大学")
