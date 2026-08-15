# -*- coding: utf-8 -*-
"""同一采编任务内新闻线索之间的只读语义相似度分析。"""
from dataclasses import dataclass
import math

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..models.smart_collect import NewsClue, SmartCollectTask, SmartCollectTaskClue
from ..models.user import User
from .embedding_service import EmbeddingServiceError, PassageEmbedder
from .smart_collect_service import SmartCollectTaskNotFoundError


@dataclass(frozen=True)
class SimilarityClueSnapshot:
    """模型线程使用的普通Python快照，不携带Session或ORM对象。"""

    clue_id: int
    rank: int
    title: str
    source: str
    text: str

    def to_public_dict(self) -> dict:
        return {
            "clue_id": self.clue_id,
            "rank": self.rank,
            "title": self.title,
            "source": self.source,
        }


class SmartCollectSimilarityService:
    """读取任务线索、批量Embedding并计算不重复的i<j相似pair。"""

    def __init__(self, embedding_service: PassageEmbedder):
        self.embedding_service = embedding_service

    @staticmethod
    def _build_clue_text(title: str, snippet: str) -> str:
        clean_title = title.strip()
        clean_snippet = snippet.strip()
        return f"{clean_title}\n{clean_snippet}" if clean_snippet else clean_title

    @classmethod
    def _load_snapshot(
        cls,
        db: Session,
        task_id: int,
        user: User,
    ) -> tuple[str, list[SimilarityClueSnapshot]]:
        """完成数据库读取后回滚只读事务，再返回普通Python数据。"""
        try:
            task = db.get(SmartCollectTask, task_id)
            if not task or (user.role != "admin" and task.creator_id != user.id):
                raise SmartCollectTaskNotFoundError

            rows = (
                db.query(
                    SmartCollectTaskClue.clue_id.label("clue_id"),
                    SmartCollectTaskClue.rank.label("rank"),
                    NewsClue.title.label("title"),
                    NewsClue.source.label("source"),
                    NewsClue.snippet.label("snippet"),
                )
                .join(NewsClue, NewsClue.id == SmartCollectTaskClue.clue_id)
                .filter(SmartCollectTaskClue.task_id == task_id)
                .order_by(SmartCollectTaskClue.rank, SmartCollectTaskClue.clue_id)
                .all()
            )
            snapshots = [
                SimilarityClueSnapshot(
                    clue_id=row.clue_id,
                    rank=row.rank,
                    title=row.title,
                    source=row.source,
                    text=cls._build_clue_text(row.title, row.snippet),
                )
                for row in rows
            ]
            return task.query, snapshots
        finally:
            # SQLAlchemy读取会自动开启事务；模型推理前必须结束并归还连接。
            db.rollback()

    @staticmethod
    def _validate_embeddings(embeddings, expected_count: int) -> list[list[float]]:
        if len(embeddings) != expected_count:
            raise EmbeddingServiceError
        vectors: list[list[float]] = []
        dimension: int | None = None
        for embedding in embeddings:
            try:
                values = [float(value) for value in embedding]
            except (TypeError, ValueError):
                raise EmbeddingServiceError from None
            if not values or any(not math.isfinite(value) for value in values):
                raise EmbeddingServiceError
            if dimension is None:
                dimension = len(values)
            elif len(values) != dimension:
                raise EmbeddingServiceError
            vectors.append(values)
        return vectors

    @staticmethod
    def _dot_product(left: list[float], right: list[float]) -> float:
        score = sum(a * b for a, b in zip(left, right))
        if not math.isfinite(score):
            raise EmbeddingServiceError
        # 归一化向量理论上处于[-1, 1]，仅截断浮点计算产生的极小越界。
        return max(-1.0, min(1.0, score))

    async def analyze(
        self,
        db: Session,
        task_id: int,
        user: User,
        limit: int = 10,
    ) -> dict:
        if not 1 <= limit <= 50:
            raise ValueError("limit必须在1到50之间")

        query, clues = self._load_snapshot(db, task_id, user)
        clue_count = len(clues)
        pair_count = clue_count * (clue_count - 1) // 2
        if clue_count < 2:
            return {
                "task_id": task_id,
                "query": query,
                "clue_count": clue_count,
                "pair_count": pair_count,
                "items": [],
            }

        # 只向线程传递普通字符串；一次调用批量生成当前任务全部新闻向量。
        embeddings = await run_in_threadpool(
            self.embedding_service.embed_passages,
            [clue.text for clue in clues],
        )
        vectors = self._validate_embeddings(embeddings, clue_count)

        pairs = []
        for left_index, left in enumerate(clues):
            for right_index in range(left_index + 1, clue_count):
                right = clues[right_index]
                pairs.append(
                    {
                        "left": left.to_public_dict(),
                        "right": right.to_public_dict(),
                        "similarity_score": self._dot_product(
                            vectors[left_index],
                            vectors[right_index],
                        ),
                    }
                )

        pairs.sort(
            key=lambda pair: (
                -pair["similarity_score"],
                pair["left"]["rank"],
                pair["right"]["rank"],
                pair["left"]["clue_id"],
                pair["right"]["clue_id"],
            )
        )
        return {
            "task_id": task_id,
            "query": query,
            "clue_count": clue_count,
            "pair_count": pair_count,
            "items": pairs[:limit],
        }
