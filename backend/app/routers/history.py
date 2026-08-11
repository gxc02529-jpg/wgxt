# -*- coding: utf-8 -*-
"""观看历史接口：查询当前登录用户的最近观看文稿列表

记录写入在 articles.py 的文章详情接口中完成（登录用户浏览已发布文稿时自动写入），
本路由只负责列表查询。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..core.pagination import paginate
from ..database import get_db
from ..models.article import Article
from ..models.user import User
from ..models.view_history import ViewHistory

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
        items.append(data)
    return {"items": items, "total": total, "page": page, "page_size": page_size}
