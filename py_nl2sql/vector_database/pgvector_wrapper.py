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
from typing import List, Tuple, Any, Optional, Type, Dict
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
            dict_data: Optional[dict] = None,
            index_type: Optional[str] = None,
            similarity_measure: Optional[str] = None,
    ):
        # TODO：增加检测 embedding 不能作为 dict_data 的键。
        """
        初始化 PGVectorWrapper 类。

        :param text_chunks: 原始文本数据集
        :param dict_data: 原始字典数据集
        :param embedding: 嵌入模型实例
        :param db_instance: 数据库实例
        :param index_type: 要使用的索引类型
        :param similarity_measure: 相似度度量方法
        """
        self.text_chunks = text_chunks
        self.dict_data = dict_data
        self.table_cls = table_cls
        self.embedding_model = embedding
        self.index_type = index_type
        self.similarity_measure = similarity_measure or "vector_l2_ops"
        self.vector_index = None
        self.db = db_instance
        self._create_vector_extension()

        if self.text_chunks or self.dict_data:
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
        if self.text_chunks:
            embeddings = self.get_chunks_embedding(self.text_chunks)
            self.add_one_content_to_embedding(embeddings)
        else:
            original_data = self.dict_data["original_data"]
            embedding_col = self.dict_data["embedding_col"]
            for data in original_data:
                embedding = self.embedding_model.embed_query(data[embedding_col])
                data["embedding"] = embedding

            self.add_multiple_content(original_data)

    def get_chunks_embedding(self, chunks: List[str], chunk_size: Optional[int] = 0) -> List[List[float]]:
        """
        获取文本块的嵌入向量。

        :param chunks: 文本块列表。
        :param chunk_size: 每次处理的文本块数量，0 表示一次处理所有。
        :return: 嵌入向量列表。
        """
        return self.embedding_model.embed_documents(chunks, chunk_size=chunk_size)

    def get_query_embedding(self, query: str) -> List[float]:
        # TODO： query 在这儿表示不准确。
        """
        获取查询文本的嵌入向量。

        :param query: 查询文本。
        :return: 查询文本的嵌入向量。
        """
        return self.embedding_model.embed_query(query)

    def add_one_content_to_embedding(self, vectors: List[List[float]]) -> None:
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

    def add_multiple_content(self, table_data: List[Dict]) -> None:
        """
        添加多列数据到数据库表，其中一列 embedding 了。

        :param table_data : 包含原始数据和嵌入向量的字典数据。
        """

        with self.db.Session() as session:
            try:
                new_items = []
                for item in table_data:
                    new_items.append(self.table_cls(**item))
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

    def search_for_row(self, query: str, top_k: int = 3) -> List[Any]:
        """
        搜索并返回排好序的文本块。

        :param query: 查询文本。
        :param top_k: 返回最相似的 top_k 个文本块。
        :return: 排好序的文本块列表。
        """
        query_embedding = self.get_query_embedding(query)
        with self.db.Session() as session:
            db_results = session.execute(
                select(self.table_cls)
                .order_by(self.table_cls.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            ).all()
        results = [result[0] for result in db_results]
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
    query = "Belum ada Dana"
    text_chunk = [
        "他来到了网易杭研大厦",
        "我来到北京清华大学",
        "小明硕士毕业于中国科学院计算所",
        "我爱北京天安门",
    ]

    data_test = [
        {'question': 'Belum ada Dana ', 'before_date': 'masih banyak waktu buat usahakan lagi dananya pak, minimal ajuin perpanjngan masih bisa', 'due_date': 'hari ini sduah japo, dari 3 hr yg lalu sdh dingetin juga, dicarikan lagi kurangnya kami tunggu maks jam 3 sore min perpanjngan dulu', 'overdue': 'Apalagi yang ditunggu? Tagihan anda hari ini sudah telat, dari kemarin sudah ditawarkan PERPANJANGAN, tapi masih ga di bayar juga, lantas mau diselesain gimana?'},
        {'question': 'besok baru ada dana', 'before_date': 'pemabayarn di hari ini lebihbaik, karena bisa mneningkatkan credit score anda diapk. Diushain sj pembayarn hrini min perpanjngan ya ', 'due_date': 'memangnya sudah terkumpul dana berapa ? Kalo emang dana belum cukup ajuin perpamnjngan dulu  sy tunggu maks jam 3 sore ini ', 'overdue': 'Dari 3 hari sebelum jatuh tempo udh di ingetin, terus masih bilang besok besok aja? Selama ini apa yg anda usahain? Jgn terlalu santai menghadapi tagihan, giliran konsekuensi kami jalanin, anda ga terima'},
        {'question': 'lagi diluar kota tidak ada atm', 'before_date': 'bisa minta tolong dulu orang rumah buat bayarkan ya, anda bisa langsung kasih saja kodenya ', 'due_date': 'Dari kemarin alesannya juga diluar kota pak, masa anda ga usahain untuk cari alternatif lain?', 'overdue': 'Luar kota mana? Anda jgn mempersulit pembayaran sendiri, kalo emg dari kemarin lagi diluar kota, harusnya sempetin waktunya buat bayar tagihan disini, jgn seenaknya gini jadi nasabah'},
        {'question': 'nanti sore saya bayar ', 'before_date': 'pembayaran lebih awal lebih baik ya kak', 'due_date': 'bayar tenor, pelunasan/ perpanjngan? Kalo perpanjngan terbatas kami tunggu siang ini sblm jam 12 siang', 'overdue': 'Anda gausah ngomong sore-sore terus sama saya, udh 4x sore yg anda lewatin dari sebelum jatuh tempo, sampe sekarang masih sama aja alesannya?'},
        {'question': 'saya akan ajuin keringanan', 'before_date': 'kendalanya apa ? Jika dana belum cukup ajuin perpanjnagn dulu saja kak utk menignkatkan credit score', 'due_date': 'hari in jatuh tempo keringan restruktur sdh tdk bisa, solusi terakhir perpanjngan tenor', 'overdue': 'Alasan anda minta keringanan apa? Jelaskan ke saya kendalanya, dan kita cari solusinya bersama untuk keringanan yg anda inginkan'}
    ]
    dict_data = {
        "original_data": data_test,
        "embedding_col": "question"
    }

    class CustomerQuestion(PGVectorBase):
        __tablename__ = 'customer_question'
        id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        question: Mapped[str] = mapped_column(Text)
        before_date: Mapped[str] = mapped_column(Text)
        due_date: Mapped[str] = mapped_column(Text)
        overdue: Mapped[str] = mapped_column(Text)
        embedding: Mapped[list] = mapped_column(Vector(1536))


    # 从环境变量获取数据库连接信息
    db_instance = create_rdb(
        db_type=RDBType.Postgresql,
        db_name=os.getenv("DB_NAME", "nl2sql"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_user=os.getenv("DB_USER", "liangzhu"),
        db_password=os.getenv("DB_PASSWORD", ""),
    )

    class VectorStore(PGVectorBase):
        __tablename__ = 'cus'
        id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        content: Mapped[str] = mapped_column(Text)
        additional_metadata: Mapped[dict] = mapped_column(JSON)
        embedding: Mapped[list] = mapped_column(Vector(1536))

    # pgvector_wrapper = PGVectorWrapper(dict_data=dict_data, table_cls=CustomerQuestion, embedding=OpenAIEmbeddings(), db_instance=db_instance)
    pgvector_wrapper = PGVectorWrapper(table_cls=CustomerQuestion, embedding=OpenAIEmbeddings(), db_instance=db_instance)
    sorted_chunks = pgvector_wrapper.search_for_row(query, top_k=2)
    for item in sorted_chunks:
        print(item.id, item.question, item.before_date, item.due_date, item.overdue)

    # scores = pgvector_wrapper.search_for_scores(query, top_k=2)
    # print(scores)
    #
    # sorted_chunks_with_scores = pgvector_wrapper.search_for_chunks_with_scores(query, top_k=2)
    # print(sorted_chunks_with_scores)
