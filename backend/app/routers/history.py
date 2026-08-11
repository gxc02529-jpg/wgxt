# -*- coding: utf-8 -*-
"""观看历史接口：查询当前登录用户的最近观看文稿列表

记录写入在 articles.py 的文章详情接口中完成（登录用户浏览已发布文稿时自动写入），
本路由负责列表查询与观看时长上报。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..core.pagination import paginate
from ..database import get_db
from ..models.article import Article
from ..models.user import User
from ..models.view_history import ViewHistory
from ..schemas.history import DurationIn

router = APIRouter(prefix="/history", tags=["观看历史"])


@router.get("", summary="我的观看历史（分页，按最近观看时间倒序）")
def my_history(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 关联已发布文稿，避免历史列表里出现已下线或已删除的文稿
    query = (
        db.query(ViewHistory, Article)
        .join(Article, Article.id == ViewHistory.article_id)
        .filter(ViewHistory.user_id == user.id, Article.status == "published")
        .order_by(ViewHistory.viewed_at.desc(), ViewHistory.id.desc())
    )
    rows, total = paginate(query, page, page_size)
    items = []
    for history, article in rows:
        data = article.to_dict()
        data["viewed_at"] = history.viewed_at.strftime("%Y-%m-%d %H:%M:%S") if history.viewed_at else None
        data["watch_seconds"] = history.watch_seconds
        data["watch_count"] = history.watch_count
        items.append(data)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/{article_id}/duration", summary="上报观看时长（登录用户，单次上限600秒）")
def report_duration(
    article_id: int,
    body: DurationIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """累计观看时长：同一用户同一文稿累加 watch_seconds，并记录上报次数。
    前端单次会话最多上报 600 秒（10 分钟），后端同样限制单次 ≤600，防止刷时长。
    """
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    history = db.query(ViewHistory).filter_by(user_id=user.id, article_id=article_id).first()
    if not history:
        # 兜底：详情页未产生历史记录时直接创建一条（正常流程由文章详情接口创建）
        history = ViewHistory(user_id=user.id, article_id=article_id, viewed_at=datetime.now())
        db.add(history)
    history.watch_seconds += body.seconds
    history.watch_count += 1
    history.viewed_at = datetime.now()
    db.commit()
    return {
        "message": "已记录观看时长",
        "watch_seconds": history.watch_seconds,
        "watch_count": history.watch_count,
    }
