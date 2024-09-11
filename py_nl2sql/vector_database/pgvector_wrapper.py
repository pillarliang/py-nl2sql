"""
Author: pillar
Date: 2024-08-22
Description: SQLAlchemyVectorDB class for building and searching vector index using PostgreSQL and pgvector.
"""
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select, text, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, declarative_base
from pgvector.sqlalchemy import Vector
import uuid
from typing import List, Tuple, Any, Optional, Type
import logging
import os

from py_nl2sql.constants.type import RDBType
from py_nl2sql.relational_database.sql_database import SQLDatabase
from py_nl2sql.relational_database.sql_factory import create_rdb
from py_nl2sql.vector_database.base_vectordb import BaseVectorDB


logger = logging.getLogger(__name__)

# 如果Base实例在不同的文件中定义，那么它们会被视为不同的上下文环境。由于是两个不同的 Base，它们不共享同一个元数据（Metadata）。
PGVectorBase = declarative_base()


# 定义基类
class PGVectorWrapper(BaseVectorDB):
    def __init__(
            self,
            table_cls: Type[PGVectorBase],
            embedding: Any,
            db_instance: SQLDatabase,
            text_chunks: Optional[List[str]] = None,
            index_type: Optional[str] = None,
            similarity_measure: Optional[str] = None,
    ):
        """
        初始化 PGVectorWrapper 类。

        :param text_chunks: 原始文本数据集
        :param embedding: 嵌入模型实例
        :param db_instance: 数据库实例
        :param index_type: 要使用的索引类型
        :param similarity_measure: 相似度度量方法
        """
        self.text_chunks = text_chunks
        self.table_cls = table_cls
        self.embedding_model = embedding
        self.index_type = index_type
        self.similarity_measure = similarity_measure or "vector_l2_ops"
        self.vector_index = None
        self.db = db_instance
        self._create_vector_extension()

        if self.text_chunks:
            if not self._is_table_exists():
                # 创建表
                PGVectorBase.metadata.create_all(self.db.engine)
                # 创建索引
                self._create_index()

            self._initialize_embeddings()
        else:
            if not self._is_table_exists():
                raise ValueError("当前表不存在，请提供文本块以初始化表格。")

    def _is_table_exists(self) -> bool:
        return self.db.inspector.has_table(self.table_cls.__tablename__)

    def _create_vector_extension(self):
        """初始化 PostgreSQL 扩展。"""
        with self.db.Session() as session:
            session.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
            session.execute(text('CREATE EXTENSION IF NOT EXISTS hstore'))
            session.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            session.commit()

    def _create_index(self):
        """创建索引实例。"""
        # ⚠️⚠️⚠️
        # 在 Psycopg 3 下使用下面这种方式
        # （source from:https://github.com/pgvector/pgvector-python/blob/master/README.md#sqlalchemy ）
        # 报错：# (psycopg.errors.UndefinedObject) operator class "vector_l2_ops" does not exist for access method "btree"
        # 所以使用 connection.execute 的方式创建索引。
        # ⚠️⚠️⚠️

        # self.vector_index = Index(
        #     'vector_store_embedding_hnsw_idx',
        #     VectorStore.embedding,
        #     postgresql_using=self.index_type,
        #     postgresql_ops={'embedding': 'vector_l2_ops'}
        # )

        with self.db.engine.connect() as connection:
            try:
                create_index_sql = f"""
                CREATE INDEX IF NOT EXISTS vector_store_embedding_hnsw_idx 
                ON {self.table_cls.__tablename__}
                USING hnsw (embedding vector_cosine_ops);
                """
                connection.execute(text(create_index_sql))
                connection.commit()
                # self.vector_index.create(connection)
            # (psycopg.errors.UndefinedObject) operator class "vector_l2_ops" does not exist for access method "btree"
            except Exception as e:
                logger.error(f"创建索引时出错: {e}")
                connection.rollback()
                raise

    def _initialize_embeddings(self):
        """初始化嵌入并添加到数据库。"""
        embeddings = self.get_chunks_embedding(self.text_chunks)
        self.add(embeddings)

    def get_chunks_embedding(self, chunks: List[str], chunk_size: Optional[int] = 0) -> List[List[float]]:
        """
        获取文本块的嵌入向量。

        :param chunks: 文本块列表。
        :param chunk_size: 每次处理的文本块数量，0 表示一次处理所有。
        :return: 嵌入向量列表。
        """
        return self.embedding_model.embed_documents(chunks, chunk_size=chunk_size)

    def get_query_embedding(self, query: str) -> List[float]:
        """
        获取查询文本的嵌入向量。

        :param query: 查询文本。
        :return: 查询文本的嵌入向量。
        """
        return self.embedding_model.embed_query(query)

    def add(self, vectors: List[List[float]]) -> None:
        """
        向索引中添加向量。

        :param vectors: 要添加到索引的向量列表。
        """
        if len(vectors) != len(self.text_chunks):
            raise ValueError("向量数量必须与文本块数量匹配。")

        with self.db.Session() as session:
            try:
                new_items = [
                    self.table_cls(
                        content=self.text_chunks[i],
                        additional_metadata={},
                        embedding=vector,
                    ) for i, vector in enumerate(vectors)
                ]
                session.bulk_save_objects(new_items)
                session.commit()
                logger.info(f"成功添加 {len(new_items)} 个项目到数据库。")
            except Exception as e:
                session.rollback()
                logger.error(f"插入数据时出错: {e}")
                raise

    def search_for_chunks(self, query: str, top_k: int = 3) -> List[str]:
        """
        搜索并返回排好序的文本块。

        :param query: 查询文本。
        :param top_k: 返回最相似的 top_k 个文本块。
        :return: 排好序的文本块列表。
        """
        query_embedding = self.get_query_embedding(query)
        with self.db.Session() as session:
            results = session.scalars(
                select(self.table_cls.content)
                .order_by(self.table_cls.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            ).all()
        return results

    def search_for_scores(self, query: str, top_k: int) -> List[float]:
        """
        搜索并返回原始块对应的分数。

        :param query: 查询文本。
        :param top_k: 返回最相似的 top_k 个文本块的分数。
        :return: 原始块对应的分数列表。
        """
        query_embedding = self.get_query_embedding(query)
        with self.db.Session() as session:
            results = session.execute(
                select(
                    (1 - self.table_cls.embedding.cosine_distance(query_embedding)).label('score')
                )
                .order_by(self.table_cls.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            ).scalars().all()
        return results

    def search_for_chunks_with_scores(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """
        搜索并返回排好序的文本块及其对应的分数。

        :param query: 查询文本。
        :param top_k: 返回最相似的 top_k 个文本块及其分数。
        :return: 包含排好序的文本块及其对应分数的列表。
        """
        query_embedding = self.get_query_embedding(query)
        with self.db.Session() as session:
            results = session.execute(
                select(
                    self.table_cls.content,
                    (1 - self.table_cls.embedding.cosine_distance(query_embedding)).label('score')
                )
                .order_by(self.table_cls.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            ).all()
        return results


if __name__ == "__main__":
    query = "清华大学"
    text_chunk = [
        "他来到了网易杭研大厦",
        "我来到北京清华大学",
        "小明硕士毕业于中国科学院计算所",
        "我爱北京天安门",
    ]

    # 从环境变量获取数据库连接信息
    db_instance = create_rdb(
        db_type=RDBType.Postgresql,
        db_name=os.getenv("DB_NAME", "nl2sql"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_user=os.getenv("DB_USER", "liangzhu"),
        db_password=os.getenv("DB_PASSWORD", ""),
    )

    class VectorStore(PGVectorBase):
        __tablename__ = 'aab'
        id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        content: Mapped[str] = mapped_column(Text)
        additional_metadata: Mapped[dict] = mapped_column(JSON)
        embedding: Mapped[list] = mapped_column(Vector(1536))


    PGVectorBase.metadata.create_all(db_instance.engine)

    pgvector_wrapper = PGVectorWrapper(text_chunks=text_chunk, table_cls=VectorStore, embedding=OpenAIEmbeddings(), db_instance=db_instance)
    # pgvector_wrapper = PGVectorWrapper(table_cls=VectorStore, embedding=OpenAIEmbeddings(), db_instance=db_instance)
    sorted_chunks = pgvector_wrapper.search_for_chunks(query, top_k=2)
    print(sorted_chunks)

    # scores = pgvector_wrapper.search_for_scores(query, top_k=2)
    # print(scores)
    #
    # sorted_chunks_with_scores = pgvector_wrapper.search_for_chunks_with_scores(query, top_k=2)
    # print(sorted_chunks_with_scores)
