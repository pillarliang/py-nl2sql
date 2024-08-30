"""
Author: pillar
Date: 2024-08-30
Description: RetrievalService class for searching text chunks.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class RetrievalService:
    @staticmethod
    def retrieval(query: str, semantic_index, method="semantic", top_k: int = 3):
        if method == "hybrid":
            return RetrievalService.hybrid_search(query)
        elif method == "sql":
            return RetrievalService.sql_search(query)
        elif method == "semantic":
            return RetrievalService.semantic_search(query, semantic_index, top_k)

    @staticmethod
    def hybrid_search(query: str):
        # TODO: Implement hybrid search
        return query

    @staticmethod
    def sql_search(query: str):
        # TODO: Implement SQL search
        return query

    @staticmethod
    def semantic_search(query: str, semantic_index, top_k: int) -> List[str]:
        return semantic_index.search_for_chunks(query, top_k)

    @staticmethod
    def multimodal_search(query: str, multimodal_index, top_k: int):
        return multimodal_index.search_for_multimodal(query, top_k)

