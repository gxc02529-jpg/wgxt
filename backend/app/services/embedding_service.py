# -*- coding: utf-8 -*-
"""文稿向量 CRUD 服务（article_embeddings 表）

供个性化推荐召回链路使用：文稿"标题+分类"向量化结果的增删改查。
约定：
- 所有函数不 commit，由调用方统一 db.commit()（项目事务约定：一个请求一个 Session）
- 向量以 float32 小端字节流存储，pack_vector/unpack_vector 负责与 list[float] 互转；
  批量解码追求性能时可用 np.frombuffer(data, dtype="<f4")
- model_version 区分嵌入模型/文本配方版本，换模型时 bump 版本全量重算即可，表结构不变
"""
import hashlib
import struct
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.article import Article
from ..models.article_embedding import ArticleEmbedding


# ---------------- 字节流辅助 ----------------

def pack_vector(vector) -> bytes:
    """list/tuple[float] → float32 小端字节流（入库格式）"""
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_vector(data: bytes) -> list:
    """float32 小端字节流 → list[float]"""
    return list(struct.unpack(f"<{len(data) // 4}f", data))


def hash_source_text(text: str) -> str:
    """计算源文本（标题+分类）的 SHA-256，用于判断是否需要重新向量化"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------- 增 / 改 ----------------

def upsert_embedding(
    db: Session,
    article_id: int,
    vector,
    model_version: str,
    source_hash: str,
) -> ArticleEmbedding:
    """新建或覆盖指定文稿的向量（调用方 commit）。

    典型用法：
        text = f"{article.title} [SEP] {','.join(c.name for c in article.categories)}"
        new_hash = hash_source_text(text)
        old = get_embedding(db, article.id)
        if old and old.source_hash == new_hash:  # 源文本未变，跳过重算
            return old
        vector = encode(text)                    # 调用向量模型（后续切片接入）
        upsert_embedding(db, article.id, vector, "bge-small-zh-v1", new_hash)
    """
    row = db.get(ArticleEmbedding, article_id)
    data = pack_vector(vector)
    if row is None:
        row = ArticleEmbedding(
            article_id=article_id,
            embedding=data,
            dim=len(vector),
            model_version=model_version,
            source_hash=source_hash,
        )
        db.add(row)
    else:
        row.embedding = data
        row.dim = len(vector)
        row.model_version = model_version
        row.source_hash = source_hash
        row.updated_at = datetime.now()
    return row


# ---------------- 查 ----------------

def get_embedding(db: Session, article_id: int):
    """读取单篇文稿的向量记录；不存在返回 None"""
    return db.get(ArticleEmbedding, article_id)


def list_embeddings(db: Session, article_ids: list) -> dict:
    """批量读取：{article_id: ArticleEmbedding}；不存在的 id 不出现在结果中"""
    if not article_ids:
        return {}
    rows = (
        db.query(ArticleEmbedding)
        .filter(ArticleEmbedding.article_id.in_(article_ids))
        .all()
    )
    return {row.article_id: row for row in rows}


def load_published_matrix(db: Session, model_version: str = None) -> list:
    """加载全部已发布文稿的向量，供启动时构建内存计算矩阵。

    返回 [(article_id, list[float]), ...]；model_version 不为空时仅加载该版本。
    """
    query = (
        db.query(ArticleEmbedding)
        .join(Article, Article.id == ArticleEmbedding.article_id)
        .filter(Article.status == "published")
    )
    if model_version:
        query = query.filter(ArticleEmbedding.model_version == model_version)
    return [(row.article_id, unpack_vector(row.embedding)) for row in query.all()]


def find_missing_article_ids(db: Session, model_version: str, limit: int = None) -> list:
    """找出指定版本下尚未向量化的文稿 ID（存量回填/补算用）。

    逻辑：articles 中不存在"该版本"向量行的文稿（含从未向量化与旧版本行两种情况）。
    """
    sub = (
        db.query(ArticleEmbedding.article_id)
        .filter(ArticleEmbedding.model_version == model_version)
    )
    query = db.query(Article.id).filter(~Article.id.in_(sub))
    if limit:
        query = query.limit(limit)
    return [row[0] for row in query.all()]


def stats(db: Session) -> dict:
    """向量化统计：总数与按模型版本分布（后台管理/回填进度展示用）"""
    rows = (
        db.query(ArticleEmbedding.model_version, func.count(ArticleEmbedding.article_id))
        .group_by(ArticleEmbedding.model_version)
        .all()
    )
    by_version = {version: count for version, count in rows}
    return {"total": sum(by_version.values()), "by_version": by_version}


# ---------------- 删 ----------------

def delete_embedding(db: Session, article_id: int) -> bool:
    """删除指定文稿的向量记录（调用方 commit）；返回是否确实删除了记录。

    说明：删除文稿时无需手动调用——外键 ON DELETE CASCADE 会自动清理；
    本方法用于"保留文稿但重算/清空向量"等运维场景。
    """
    deleted = (
        db.query(ArticleEmbedding)
        .filter(ArticleEmbedding.article_id == article_id)
        .delete()
    )
    return deleted > 0