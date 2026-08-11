# -*- coding: utf-8 -*-
"""用户互动接口：点赞、收藏、转发（同时写入埋点日志）"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..core.pagination import paginate
from ..database import get_db
from ..models.article import Article
from ..models.interaction import UserAction
from ..models.user import User
from ..schemas.article import ArticleIn
from ..services.event_service import record_event

router = APIRouter(prefix="/interactions", tags=["互动"])


def _get_published_article(db: Session, article_id: int) -> Article:
    article = db.get(Article, article_id)
    if not article or article.status != "published":
        raise HTTPException(404, "文稿不存在或未发布")
    return article


@router.post("/like", summary="点赞")
def like(article_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = _get_published_article(db, article_id)
    exists = db.query(UserAction).filter_by(user_id=user.id, article_id=article_id, action_type="like").first()
    if not exists:
        db.add(UserAction(user_id=user.id, article_id=article_id, action_type="like"))
        article.like_count += 1
        record_event(db, event_type="like", article_id=article_id, user_id=user.id, request=request)
        db.commit()
        return {"message": "点赞成功", "liked": True, "like_count": article.like_count}
    return {"message": "已点过赞", "liked": True, "like_count": article.like_count}


@router.delete("/like", summary="取消点赞")
def unlike(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    action = db.query(UserAction).filter_by(user_id=user.id, article_id=article_id, action_type="like").first()
    if action:
        article = db.get(Article, article_id)
        if article and article.like_count > 0:
            article.like_count -= 1
        db.delete(action)
        db.commit()
        return {"message": "已取消点赞", "liked": False, "like_count": article.like_count if article else 0}
    return {"message": "尚未点赞", "liked": False}


@router.post("/favorite", summary="收藏")
def favorite(article_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = _get_published_article(db, article_id)
    exists = db.query(UserAction).filter_by(user_id=user.id, article_id=article_id, action_type="favorite").first()
    if not exists:
        db.add(UserAction(user_id=user.id, article_id=article_id, action_type="favorite"))
        article.favorite_count += 1
        record_event(db, event_type="favorite", article_id=article_id, user_id=user.id, request=request)
        db.commit()
        return {"message": "收藏成功", "favorited": True, "favorite_count": article.favorite_count}
    return {"message": "已收藏", "favorited": True, "favorite_count": article.favorite_count}


@router.delete("/favorite", summary="取消收藏")
def unfavorite(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    action = db.query(UserAction).filter_by(user_id=user.id, article_id=article_id, action_type="favorite").first()
    if action:
        article = db.get(Article, article_id)
        if article and article.favorite_count > 0:
            article.favorite_count -= 1
        db.delete(action)
        db.commit()
        return {"message": "已取消收藏", "favorited": False, "favorite_count": article.favorite_count if article else 0}
    return {"message": "尚未收藏", "favorited": False}


@router.post("/share", summary="转发（记录转发行为）")
def share(article_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = _get_published_article(db, article_id)
    article.share_count += 1
    record_event(db, event_type="share", article_id=article_id, user_id=user.id, request=request)
    db.commit()
    return {"message": "转发成功", "share_count": article.share_count}


@router.get("/status", summary="查询当前用户对文稿的点赞/收藏状态")
def my_status(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    liked = db.query(UserAction).filter_by(user_id=user.id, article_id=article_id, action_type="like").first()
    favorited = db.query(UserAction).filter_by(user_id=user.id, article_id=article_id, action_type="favorite").first()
    return {"liked": liked is not None, "favorited": favorited is not None}


@router.get("/favorites", summary="我的收藏列表")
def my_favorites(page: int = 1, page_size: int = 10, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = (
        db.query(Article)
        .join(UserAction, UserAction.article_id == Article.id)
        .filter(UserAction.user_id == user.id, UserAction.action_type == "favorite", Article.status == "published")
        .order_by(UserAction.id.desc())
    )
    rows, total = paginate(query, page, page_size)
    return {"items": [a.to_dict() for a in rows], "total": total, "page": page, "page_size": page_size}

