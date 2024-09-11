from abc import ABC, abstractmethod
from typing import List, Tuple, Any
import numpy as np


class BaseVectorDB(ABC):
    @abstractmethod
    def __init__(self, text_chunks: List[str], embedding: Any, index_type: str, similarity_measure: str, **kwargs):
        """
        初始化向量数据库

        :param text_chunks: 原始文本数据集
        :param embedding: 嵌入模型实例
        :param index_type: 索引类型
        :param similarity_measure: 相似度度量
        :param kwargs: 其他可能的参数
        """
        pass

    @abstractmethod
    def get_chunks_embedding(self, text_chunks: List[str]) -> np.ndarray:
        """
        获取文本块的嵌入向量

        :param text_chunks: 文本块列表
        :return: 嵌入向量数组
        """
        pass

    @abstractmethod
    def get_query_embedding(self, query: str) -> np.ndarray:
        """
        获取查询文本的嵌入向量

        :param query: 查询文本
        :return: 查询文本的嵌入向量
        """
        pass


    @abstractmethod
    def search_for_chunks(self, query: str, top_k: int = 3) -> List[str]:
        """
        搜索并返回排好序的文本块

        :param query: 查询文本
        :param top_k: 返回最相似的 top_k 个文本块
        :return: 排好序的文本块列表
        """
        pass

    @abstractmethod
    def search_for_scores(self, query: str, top_k: int) -> List[float]:
        """
        搜索并返回原始块对应的分数

        :param query: 查询文本
        :param top_k: 返回最相似的 top_k 个文本块的分数
        :return: 原始块对应的分数列表
        """
        pass

    @abstractmethod
    def search_for_chunks_with_scores(
        self, query: str, top_k: int
    ) -> List[List[Tuple[str, float]]]:
        """
        搜索并返回排好序的文本块及其对应的分数

        :param query: 查询文本
        :param top_k: 返回最相似的 top_k 个文本块及其分数
        :return: 包含排好序的文本块及其对应分数的列表
        """
        pass
