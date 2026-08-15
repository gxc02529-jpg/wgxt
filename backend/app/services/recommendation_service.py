# -*- coding: utf-8 -*-
"""用户个性化推荐文章算法（混合加权评分 + 随机扰动 + 分类多样性）

评分公式：
    base = 0.30 * 偏好分 + 0.40 * 新鲜度 + 0.30 * 热度
    score = base * (0.75 + 0.5 * rand)   # 每次请求每篇文章独立随机扰动
按 score 贪心选取 limit 篇，已入选栏目会惩罚同栏目剩余候选（0.8 ** 已选数），
保证推荐结果不同用户/不同请求不同，且新热文稿权重更高。

规格见 docs/article_recommend_spec.md。
"""
import math
import random
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.article import Article, article_categories
from ..models.interaction import UserAction
from ..models.user import User
from ..models.view_history import ViewHistory


# 用户偏好画像最多回溯的观看记录条数
PREF_HISTORY_LIMIT = 20
# 推荐结果最大条数（接口层 Query(le=20) 已约束，这里兜底）
MAX_LIMIT = 20
# 新鲜度指数衰减的半衰参数（天）：30 天内衰减明显，越新分数越高
FRESH_DECAY_DAYS = 30
# 热度评分中各类互动的加权系数
HOT_WEIGHTS = {
    "view_count": 1,
    "like_count": 3,
    "favorite_count": 5,
    "share_count": 2,
}
# 基础分权重：新+热合计 0.7，略高于个性化 0.3
W_PREF, W_FRESH, W_HOT = 0.30, 0.40, 0.30
# 随机扰动系数：score = base * (0.75 + 0.5 * rand)
NOISE_MIN, NOISE_SPAN = 0.75, 0.50
# 分类多样性惩罚底数：同栏目已选 k 篇后，该栏目候选得分乘 0.8 ** k
DIVERSITY_DECAY = 0.8


def _build_user_preference(db: Session, user: User | None) -> dict[int, float]:
    """构建用户栏目偏好画像：最近 20 条观看记录中各栏目出现占比（0~1）"""
    if user is None:
        return {}
    history = (
        db.query(ViewHistory)
        .filter(ViewHistory.user_id == user.id)
        .order_by(ViewHistory.viewed_at.desc())
        .limit(PREF_HISTORY_LIMIT)
        .all()
    )
    if not history:
        return {}
    ids = [h.article_id for h in history]
    rows = (
        db.query(article_categories.c.article_id, article_categories.c.category_id)
        .filter(article_categories.c.article_id.in_(ids))
        .all()
    )
    counts: dict[int, int] = defaultdict(int)
    for _, category_id in rows:
        counts[category_id] += 1
    total = len(ids) or 1
    return {cid: cnt / total for cid, cnt in counts.items()}


def _collect_category_map(db: Session, article_ids: list[int]) -> dict[int, list[int]]:
    """一次性查询文稿-栏目映射，避免逐篇加载关系造成 N+1 查询"""
    if not article_ids:
        return {}
    rows = (
        db.query(article_categories.c.article_id, article_categories.c.category_id)
        .filter(article_categories.c.article_id.in_(article_ids))
        .all()
    )
    mapping: dict[int, list[int]] = defaultdict(list)
    for article_id, category_id in rows:
        mapping[article_id].append(category_id)
    return mapping


def recommend_articles(db: Session, user: User | None, limit: int) -> list[Article]:
    """返回推荐文稿列表（按评分降序，最多 limit 篇）

    - 登录用户：排除已观看与已标记不感兴趣的文稿，按观看历史构建偏好
    - 未登录用户：退化为 新鲜度 + 热度 + 随机扰动 的通用推荐
    """
    limit = max(1, min(int(limit), MAX_LIMIT))
    query = db.query(Article).filter(Article.status == "published")

    if user is not None:
        # 排除已观看与不感兴趣，避免重复推荐同一内容
        watched_ids = {
            row[0]
            for row in db.query(ViewHistory.article_id).filter(ViewHistory.user_id == user.id).all()
        }
        disliked_ids = {
            row[0]
            for row in db.query(UserAction.article_id).filter(
                UserAction.user_id == user.id, UserAction.action_type == "dislike"
            ).all()
        }
        excluded = watched_ids | disliked_ids
        if excluded:
            query = query.filter(~Article.id.in_(excluded))

    candidates = query.all()
    if not candidates:
        return []

    article_ids = [a.id for a in candidates]
    category_map = _collect_category_map(db, article_ids)
    pref = _build_user_preference(db, user)

    now = datetime.now()
    # 热度 min-max 归一化（候选集内）
    hot_raw = [
        a.view_count * HOT_WEIGHTS["view_count"]
        + a.like_count * HOT_WEIGHTS["like_count"]
        + a.favorite_count * HOT_WEIGHTS["favorite_count"]
        + a.share_count * HOT_WEIGHTS["share_count"]
        for a in candidates
    ]
    hot_max = max(hot_raw) if hot_raw else 0
    hot_min = min(hot_raw) if hot_raw else 0
    hot_span = hot_max - hot_min

    scored: list[tuple[Article, float]] = []
    for article, raw_hot in zip(candidates, hot_raw):
        # 新鲜度：指数衰减，距发布越久权重越低
        published = article.published_at or article.created_at
        age_days = max(0, (now - published).days)
        fresh = math.exp(-age_days / FRESH_DECAY_DAYS)
        # 热度归一化
        hot = (raw_hot - hot_min) / hot_span if hot_span > 0 else 0.0
        # 偏好分：文章所属栏目中用户偏好最高的权重
        pref_score = max((pref.get(cid, 0.0) for cid in category_map.get(article.id, [])), default=0.0)
        base = W_PREF * pref_score + W_FRESH * fresh + W_HOT * hot
        score = base * (NOISE_MIN + NOISE_SPAN * random.random())
        scored.append((article, score))

    # 贪心选取 + 分类多样性惩罚：同栏目已选 k 篇后，该栏目剩余候选降权
    selected: list[Article] = []
    selected_by_category: dict[int, int] = defaultdict(int)
    for _ in range(min(limit, len(scored))):
        def effective(item: tuple[Article, float]) -> float:
            article, score = item
            cats = category_map.get(article.id, [])
            hit = max((selected_by_category.get(cid, 0) for cid in cats), default=0)
            return score * (DIVERSITY_DECAY ** hit)

        best = max(scored, key=effective)
        scored.remove(best)
        selected.append(best[0])
        for cid in category_map.get(best[0].id, []):
            selected_by_category[cid] += 1

    return selected
