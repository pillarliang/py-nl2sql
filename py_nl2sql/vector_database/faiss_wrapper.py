"""
Author: pillar
Date: 2024-08-22
Description: FaissWrapper class for building and searching Faiss index.
"""
from typing import List, Tuple
import faiss
import numpy as np


class FaissWrapper:
    def __init__(
            self,
            text_chunks,
            embedding,
            index_type="Flat",
            metric=faiss.METRIC_L2,
            nlist=100,
            hnsw_m=32
    ):
        """
        init FaissWrapper class.

        :param text_chunks: original text dataset
        :param embedding: embedding model instance. If not provided, the default HuggingFaceEmbeddings is used.
        :param index_type: the type of index to use, can be 'Flat', 'IVFFlat' or 'HNSW'.
        :param metric: the method to measure similarity, can be faiss.METRIC_L2 (default) or faiss.METRIC_INNER_PRODUCT.
        :param nlist: the number of clusters (only for IVFFlat index).
        :param hnsw_m: the parameter for HNSW index, representing the number of neighbors for each node.
        """
        self.text_chunks = text_chunks
        self.embedding = embedding
        self.index_type = index_type
        self.metric = metric
        self.nlist = nlist
        self.hnsw_m = hnsw_m

        # compute embeddings and get dimension
        embeddings = self.get_chunks_embedding(text_chunks)
        self.d = embeddings.shape[1]

        self.index = self._create_index()
        self.trained = False
        self.cache = {}  # cache distances and indices

        # add embeddings to index
        self.add(embeddings)

    def get_chunks_embedding(self, text_chunks: List[str]):
        """
        get the embedding of text chunks.
        """
        return np.array(self.embedding.embed_documents(text_chunks)).astype("float32")

    def get_query_embedding(self, query: str):
        """
        get the embedding of query text.
        """
        return np.array(self.embedding.embed_query(query)).astype("float32").reshape(1, -1)

    def _create_index(self):
        """
        create index instance.
        """
        if self.index_type == "Flat":
            return self._create_flat_index()
        elif self.index_type == "IVFFlat":
            return self._create_ivfflat_index()
        elif self.index_type == "HNSW":
            return self._create_hnsw_index()
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")

    def _create_flat_index(self):
        """
        create Flat index instance.
        """
        if self.metric == faiss.METRIC_L2:
            return faiss.IndexFlatL2(self.d)
        elif self.metric == faiss.METRIC_INNER_PRODUCT:
            return faiss.IndexFlatIP(self.d)
        else:
            raise ValueError(f"Unsupported metric: {self.metric}")

    def _create_ivfflat_index(self):
        """
        创建 IVFFlat 索引实例。
        """
        quantizer = self._create_flat_index()
        return faiss.IndexIVFFlat(quantizer, self.d, self.nlist, self.metric)

    def _create_hnsw_index(self):
        """
        创建 HNSW 索引实例。
        """
        index = faiss.IndexHNSWFlat(self.d, self.hnsw_m)
        if self.metric == faiss.METRIC_INNER_PRODUCT:
            faiss.normalize_L2(index)
        return index

    def train(self, vectors):
        """
        训练索引（仅适用于需要训练的索引类型，如 IVFFlat）。

        :param vectors: 用于训练的向量。
        """
        if self.index_type == "IVFFlat" and not self.trained:
            self.index.train(vectors)
            self.trained = True

    def add(self, vectors):
        """
        添加向量到索引。如果是 IVFFlat 索引且未训练，则自动训练。

        :param vectors: 要添加到索引的向量。
        """
        if self.index_type == "IVFFlat" and not self.trained:
            self.train(vectors)
        self.index.add(vectors)

    def search(self, query_vectors, k) -> Tuple[np.ndarray, np.ndarray]:
        """
        搜索与查询向量最相似的 k 个向量。

        :param query_vectors: 查询向量。
        :param k: 返回最相似的 k 个向量。
        :return: 返回距离和索引。
        """
        cache_key = (tuple(map(tuple, query_vectors)), k)
        if cache_key not in self.cache:
            distances, indices = self.index.search(query_vectors, k)
            self.cache[cache_key] = (distances, indices)
        return self.cache[cache_key]

    def save(self, file_path):
        """
        保存索引到文件。

        :param file_path: 索引文件的路径。
        """
        faiss.write_index(self.index, file_path)

    def load(self, file_path):
        """
        从文件加载索引。

        :param file_path: 索引文件的路径。
        """
        self.index = faiss.read_index(file_path)

    def get_sorted_chunks(self, indices, chunks) -> List[str]:
        """
        根据索引返回排好序的文本 chunk。

        :param indices: 最近邻向量的索引。
        :param chunks: 原始文本数据集。
        :return: 排好序的文本 chunk 列表。
        """
        sorted_chunks = []
        for idx_list in indices:
            sorted_chunks.extend([chunks[idx] for idx in idx_list])
        return sorted_chunks

    def get_scores(self, distances, indices, num_chunks) -> List[float]:
        """
        返回原始 chunk 对应的分数。

        :param distances: 最近邻向量的距离。
        :param indices: 最近邻向量的索引。
        :param num_chunks: 原始文本数据集的数量。
        :return: 原始 chunk 对应的分数列表。
        """
        scores = [float('inf')] * num_chunks
        for i in range(len(indices)):
            for j in range(len(indices[i])):
                idx = indices[i][j]
                scores[idx] = distances[i][j]
        return scores

    def search_for_chunks(self, query, top_k=3):
        """
        search and return sorted text chunks.

        :param query: 查询文本。
        :param top_k: 返回最相似的 top_k 个文本 chunk。
        :return: 排好序的文本 chunk 列表。
        """
        query_vectors = self.get_query_embedding(query)
        distances, indices = self.search(query_vectors, top_k)
        return self.get_sorted_chunks(indices, self.text_chunks)

    def search_for_scores(self, query: str, top_k: int):
        """
        搜索并返回原始 chunk 对应的分数。

        :param query: 查询文本。
        :param top_k: 返回最相似的 top_k 个文本 chunk 的分数。
        :return: 原始 chunk 对应的分数列表。
        """
        query_vectors = self.get_query_embedding(query)
        num_chunks = len(self.text_chunks)
        distances, indices = self.search(query_vectors, top_k)
        return self.get_scores(distances, indices, num_chunks)

    def search_for_chunks_with_scores(self, query: str, top_k: int):
        """
        搜索并返回排好序的文本 chunk 及其对应的分数。

        :param query: 查询文本。
        :param top_k: 返回最相似的 top_k 个文本 chunk 及其分数。
        :return: 一个包含排好序的文本 chunk 及其对应分数的列表。
        """
        query_vectors = self.get_query_embedding(query)
        distances, indices = self.search(query_vectors, top_k)
        sorted_chunks_with_scores = []
        for i in range(len(indices)):
            sorted_chunks_with_scores.append(
                [(self.text_chunks[idx], distances[i][j]) for j, idx in enumerate(indices[i])])

        return sorted_chunks_with_scores

    def clear_cache(self):
        """
        清除缓存以释放内存。
        """
        self.cache.clear()

    def destroy_index(self):
        """
        释放索引以释放内存。
        """
        del self.index
        self.index = None
