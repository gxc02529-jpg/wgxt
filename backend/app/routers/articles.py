# -*- coding: utf-8 -*-
"""文稿接口：前台浏览 + 编辑写作 + 管理列表

审核状态机：draft(草稿) → pending_first(待一审) → pending_second(待二审) → published(已发布)
                                                              ↘ rejected(已驳回，可修改后重新提交)
开启系统配置 auto_review（自动审核）后，提审即自动通过两级审核并发布。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_optional_user, require_roles
from ..core.pagination import paginate
from ..database import get_db
from ..models.article import Article, article_categories
from ..models.category import Category
from ..models.review import ArticleReview
from ..models.user import User
from ..schemas.article import ArticleIn
from ..services.settings_service import get_setting

router = APIRouter(prefix="/articles", tags=["文稿"])

# 编辑可提交审核的状态；草稿与驳回稿可修改
EDITABLE_STATUS = ("draft", "rejected")


def _can_manage(article: Article, user: User) -> bool:
    """判断用户是否为作者或管理员"""
    if user is None:
        return False
    return user.role == "admin" or article.author_id == user.id


def _apply_categories(db: Session, article: Article, category_ids: list[int]):
    """重新设置文稿所属栏目（多对多）"""
    ids = list(dict.fromkeys(category_ids))  # 去重
    cats = db.query(Category).filter(Category.id.in_(ids)).all() if ids else []
    article.categories = cats


@router.get("", summary="前台文稿列表（仅已发布）")
def list_articles(
    category_id: int | None = Query(default=None, description="按栏目筛选"),
    keyword: str | None = Query(default=None, description="标题/摘要关键词"),
    city: str | None = Query(default=None, description="按城市筛选（同城搜索），如 深圳"),
    sort: str = Query(default="latest", pattern="^(latest|hot)$", description="latest 最新 / hot 最热"),
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
):
    query = db.query(Article).filter(Article.status == "published")
    if category_id:
        query = query.join(article_categories, Article.id == article_categories.c.article_id) \
                     .filter(article_categories.c.category_id == category_id)
    if keyword:
        query = query.filter(or_(Article.title.like(f"%{keyword}%"), Article.summary.like(f"%{keyword}%")))
    if city:
        query = query.filter(Article.city == city)

    if sort == "hot":
        query = query.order_by(Article.view_count.desc(), Article.published_at.desc())
    else:
        query = query.order_by(Article.published_at.desc())

    rows, total = paginate(query, page, page_size)
    return {"items": [a.to_dict() for a in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/cities", summary="已发布文稿覆盖的城市列表（同城搜索下拉）")
def list_cities(db: Session = Depends(get_db)):
    """返回所有已发布文稿中出现过的城市（去重、非空），供前台城市下拉选择。"""
    rows = (
        db.query(Article.city)
        .filter(
            Article.status == "published",
            Article.city.isnot(None),
            Article.city != "",
        )
        .distinct()
        .order_by(Article.city.asc())
        .all()
    )
    return {"items": [r[0] for r in rows]}


@router.get("/mine", summary="我的文稿（编辑/管理员）")
def my_articles(
    status: str | None = Query(default=None, description="按状态筛选"),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("editor", "admin"):
        raise HTTPException(403, "仅编辑可写作文稿")
    query = db.query(Article).filter(Article.author_id == user.id)
    if status:
        query = query.filter(Article.status == status)
    query = query.order_by(Article.updated_at.desc())
    rows, total = paginate(query, page, page_size)
    return {"items": [a.to_dict() for a in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/admin", summary="后台全部文稿（管理员）")
def admin_articles(
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    query = db.query(Article)
    if status:
        query = query.filter(Article.status == status)
    if keyword:
        query = query.filter(or_(Article.title.like(f"%{keyword}%"), Article.summary.like(f"%{keyword}%")))
    if category_id:
        query = query.join(article_categories, Article.id == article_categories.c.article_id) \
                     .filter(article_categories.c.category_id == category_id)
    query = query.order_by(Article.updated_at.desc())
    rows, total = paginate(query, page, page_size)
    return {"items": [a.to_dict() for a in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/{article_id}", summary="文稿详情（未发布稿仅作者/管理员可见）")
def get_article(article_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    if article.status != "published" and not _can_manage(article, user):
        raise HTTPException(403, "该文稿尚未发布")
    return article.to_dict(include_content=True, include_reviews=_can_manage(article, user))


@router.get("/{article_id}/related", summary="相关推荐（同栏目已发布文稿，按发布时间新到旧）")
def related_articles(
    article_id: int,
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """查找与当前文稿同栏目的其他已发布文稿，按发布时间倒序返回。
    若文稿未挂任何栏目，则兜底返回最新发布的文稿，避免推荐区为空。
    """
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")

    query = db.query(Article).filter(
        Article.status == "published",
        Article.id != article_id,
    )
    category_ids = [c.id for c in article.categories]
    if category_ids:
        # 同栏目：与该文稿共享任一栏目的其他已发布文稿（join 会重复，需去重）
        query = (
            query.join(article_categories, Article.id == article_categories.c.article_id)
            .filter(article_categories.c.category_id.in_(category_ids))
            .distinct()
        )

    rows = (
        query.order_by(Article.published_at.desc(), Article.id.desc())
        .limit(limit)
        .all()
    )
    return {"items": [a.to_dict() for a in rows]}


@router.post("", summary="创建文稿（编辑/管理员，先存为草稿）")
def create_article(body: ArticleIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("editor", "admin"):
        raise HTTPException(403, "仅编辑可写作文稿")
    article = Article(
        title=body.title,
        summary=body.summary,
        content=body.content,
        cover_url=body.cover_url,
        author_id=user.id,
        status="draft",
    )
    db.add(article)
    db.flush()
    _apply_categories(db, article, body.category_ids)
    db.commit()
    db.refresh(article)
    return {"message": "草稿已保存", "article": article.to_dict()}


@router.put("/{article_id}", summary="编辑文稿（作者或管理员，仅草稿/驳回稿可编辑）")
def update_article(article_id: int, body: ArticleIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    if not _can_manage(article, user):
        raise HTTPException(403, "只能编辑自己的文稿")
    if article.status not in EDITABLE_STATUS:
        raise HTTPException(400, f"当前状态（{article.status}）不允许编辑，请先驳回或新建草稿")

    article.title = body.title
    article.summary = body.summary
    article.content = body.content
    article.cover_url = body.cover_url
    _apply_categories(db, article, body.category_ids)
    db.commit()
    db.refresh(article)
    return {"message": "保存成功", "article": article.to_dict()}


@router.post("/{article_id}/submit", summary="提交审核（草稿/驳回稿 → 待一审）")
def submit_article(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    if not _can_manage(article, user):
        raise HTTPException(403, "只能提交自己的文稿")
    if article.status not in ("draft", "rejected"):
        raise HTTPException(400, f"当前状态（{article.status}）不能提交审核")
    if not article.categories:
        raise HTTPException(400, "请先选择至少一个栏目再提交审核")

    # 自动审核开关：开启后提审即自动通过一审、二审并发布，同时写入两条系统审核记录
    if get_setting(db, "auto_review", default=False):
        article.status = "published"
        article.published_at = datetime.now()
        db.add(ArticleReview(
            article_id=article.id, reviewer_id=None, review_level=1,
            action="approve", comment="系统自动审核：一审通过",
        ))
        db.add(ArticleReview(
            article_id=article.id, reviewer_id=None, review_level=2,
            action="approve", comment="系统自动审核：二审通过",
        ))
        db.commit()
        return {"message": "自动审核已开启，文稿已自动通过并发布", "article": article.to_dict()}

    article.status = "pending_first"
    db.commit()
    return {"message": "已提交一审", "article": article.to_dict()}


@router.post("/{article_id}/offline", summary="下线已发布文稿（管理员）")
def offline_article(article_id: int, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    if article.status != "published":
        raise HTTPException(400, "仅已发布文稿可下线")
    article.status = "offline"
    db.commit()
    return {"message": "文稿已下线", "article": article.to_dict()}


@router.delete("/{article_id}", summary="删除文稿（作者或管理员）")
def delete_article(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    if not _can_manage(article, user):
        raise HTTPException(403, "只能删除自己的文稿")
    db.delete(article)
    db.commit()
    return {"message": "删除成功"}
