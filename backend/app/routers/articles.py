# -*- coding: utf-8 -*-
"""文稿接口：前台浏览 + 编辑写作 + 管理列表

审核状态机：draft(草稿) → pending_first(待一审) → pending_second(待二审) → published(已发布)
                                                              ↘ rejected(已驳回，可修改后重新提交)
              published → offline(已下线，可重新编辑后再次提审) → pending_first → ... → published
开启系统配置 auto_review（自动审核）后，提审即自动通过两级审核并发布。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_optional_user, require_roles
from ..core.pagination import paginate
from ..database import get_db
from ..models.article import Article, article_categories
from ..models.category import Category
from ..models.channel import Channel
from ..models.review import ArticleReview
from ..models.user import User
from ..models.view_history import ViewHistory
from ..schemas.article import ArticleIn
from ..services import embedding_service
from ..services.article_import_service import import_excel
from ..services.recommendation_service import recommend_articles
from ..services.settings_service import get_setting
from ..services.text_utils import strip_html

router = APIRouter(prefix="/articles", tags=["文稿"])

# 可编辑状态：草稿 / 驳回稿 / 已下线稿（下线稿编辑后状态保持 offline，重新提审再进入审核流）
EDITABLE_STATUS = ("draft", "rejected", "offline")

# 后台列表可排序字段白名单（sort_by 参数 → ORM 列），防止注入任意排序列
ADMIN_SORT_FIELDS = {
    "updated_at": Article.updated_at,
    "created_at": Article.created_at,
    "published_at": Article.published_at,
    "view_count": Article.view_count,
    "like_count": Article.like_count,
    "favorite_count": Article.favorite_count,
    "share_count": Article.share_count,
}

# sort_by 查询参数校验模式（与 ADMIN_SORT_FIELDS 保持同步）
SORT_BY_PATTERN = "^(updated_at|created_at|published_at|view_count|like_count|favorite_count|share_count)$"


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


def _apply_channels(db: Session, article: Article, channel_ids: list[int]):
    """重置文稿分发渠道：基础渠道（is_default）始终包含且不可移除"""
    default = db.query(Channel).filter(Channel.is_default.is_(True)).first()
    ids = list(dict.fromkeys([*(channel_ids or []), default.id])) if default else list(dict.fromkeys(channel_ids or []))
    channels = db.query(Channel).filter(Channel.id.in_(ids), Channel.status == "active").all() if ids else []
    if default and default not in channels:
        channels.append(default)
    article.channels = channels


@router.get("", summary="前台文稿列表（仅已发布）")
def list_articles(
    category_id: int | None = Query(default=None, description="按栏目筛选"),
    keyword: str | None = Query(default=None, description="标题/摘要关键词"),
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

    if sort == "hot":
        query = query.order_by(Article.view_count.desc(), Article.published_at.desc())
    else:
        query = query.order_by(Article.published_at.desc())

    rows, total = paginate(query, page, page_size)
    return {"items": [a.to_dict() for a in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/mine", summary="我的文稿（编辑/管理员）")
def my_articles(
    status: str | None = Query(default=None, description="按状态筛选"),
    keyword: str | None = Query(default=None, description="标题/摘要关键词"),
    category_id: int | None = Query(default=None, description="按栏目筛选"),
    sort_by: str = Query(default="created_at", pattern=SORT_BY_PATTERN, description="排序字段"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="排序方向"),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 编辑功能：编辑 / 管理员（moderator）/ 系统管理员
    if user.role not in ("editor", "moderator", "admin"):
        raise HTTPException(403, "仅编辑可写作文稿")
    query = db.query(Article).filter(Article.author_id == user.id)
    if status:
        query = query.filter(Article.status == status)
    if keyword:
        query = query.filter(or_(Article.title.like(f"%{keyword}%"), Article.summary.like(f"%{keyword}%")))
    if category_id:
        query = query.join(article_categories, Article.id == article_categories.c.article_id) \
                     .filter(article_categories.c.category_id == category_id)
    sort_column = ADMIN_SORT_FIELDS.get(sort_by, Article.created_at)
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
    rows, total = paginate(query, page, page_size)
    return {"items": [a.to_dict() for a in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/admin", summary="后台全部文稿（管理员）")
def admin_articles(
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    sort_by: str = Query(default="created_at", pattern=SORT_BY_PATTERN, description="排序字段"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="排序方向"),
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
    # 服务端排序：白名单字段 + 方向，默认 created_at 降序（新文稿优先）
    sort_column = ADMIN_SORT_FIELDS.get(sort_by, Article.created_at)
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
    rows, total = paginate(query, page, page_size)
    return {"items": [a.to_dict() for a in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/recommend", summary="用户个性化推荐（可选登录，默认 8 篇）")
def user_recommend_articles(
    limit: int = Query(default=8, ge=1, le=20, description="返回推荐文稿数量"),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """按用户观看偏好 + 新鲜度/热度 + 随机扰动推荐已发布文稿

    登录用户会排除已观看与已标记不感兴趣的文稿；未登录用户走通用推荐。
    算法详见 docs/article_recommend_spec.md。
    """
    items = recommend_articles(db, user, limit)
    if not items:
        raise HTTPException(400, "暂无已发布文稿可推荐")
    return {"items": [a.to_dict() for a in items], "total": len(items)}


@router.get("/{article_id}", summary="文稿详情（未发布稿仅作者/系统管理员/审核管理员可见）")
def get_article(article_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    # 未发布文稿仅作者、系统管理员、审核管理员（moderator）可见：
    # 审核人需要读取待审/待二审稿件的正文内容，否则无法执行审核
    if article.status != "published" and not (
        _can_manage(article, user) or (user is not None and user.role in ("admin", "moderator"))
    ):
        raise HTTPException(403, "该文稿尚未发布")
    # 记录观看历史：登录用户浏览已发布文稿时写入/更新 view_history
    # （同一文稿重复观看仅更新时间，历史列表按最近观看时间倒序）
    if user is not None and article.status == "published":
        history = db.query(ViewHistory).filter_by(user_id=user.id, article_id=article.id).first()
        if history:
            history.viewed_at = datetime.now()
        else:
            db.add(ViewHistory(user_id=user.id, article_id=article.id, viewed_at=datetime.now()))
        db.commit()
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
    # 编辑功能：编辑 / 管理员（moderator）/ 系统管理员
    if user.role not in ("editor", "moderator", "admin"):
        raise HTTPException(403, "仅编辑可写作文稿")
    article = Article(
        title=body.title,
        summary=body.summary,
        content=body.content,
        # 纯文本正文：前端随稿提交，缺失时后端从 HTML 剥离兜底
        content_source=body.content_source or strip_html(body.content),
        cover_url=body.cover_url,
        author_id=user.id,
        status="draft",
    )
    db.add(article)
    db.flush()
    _apply_categories(db, article, body.category_ids)
    _apply_channels(db, article, body.channel_ids)
    db.commit()
    db.refresh(article)
    # 向量化入库：尽力而为，向量化失败不影响草稿保存（全量回填接口可修复）
    if embedding_service.sync_article_embedding(db, article):
        db.commit()
    return {"message": "草稿已保存", "article": article.to_dict()}


@router.post("/import", summary="批量导入文稿（Excel：封面/标题/分类/正文，编辑/管理员）")
def import_articles(
    file: UploadFile = File(..., description=".xlsx 文件"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传 Excel 批量创建草稿；封面缺失/下载失败不丢弃文稿（封面留空），结果逐行统计"""
    if user.role not in ("editor", "moderator", "admin"):
        raise HTTPException(403, "仅编辑可导入文稿")
    data = file.file.read()
    result = import_excel(db, user, data, file.filename or "")
    return {
        "message": f"导入完成：成功 {result['imported']}，跳过 {len(result['skipped'])}，失败 {len(result['failed'])}",
        **result,
    }


@router.put("/{article_id}", summary="编辑文稿（作者或管理员，草稿/驳回稿/已下线稿可编辑）")
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
    article.content_source = body.content_source or strip_html(body.content)
    article.cover_url = body.cover_url
    _apply_categories(db, article, body.category_ids)
    _apply_channels(db, article, body.channel_ids)
    db.commit()
    db.refresh(article)
    # 向量化入库：标题/分类未变时跳过；尽力而为，失败不影响保存
    if embedding_service.sync_article_embedding(db, article):
        db.commit()
    return {"message": "保存成功", "article": article.to_dict()}


@router.post("/{article_id}/submit", summary="提交审核（草稿/驳回稿/已下线稿 → 待一审）")
def submit_article(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "文稿不存在")
    if not _can_manage(article, user):
        raise HTTPException(403, "只能提交自己的文稿")
    if article.status not in ("draft", "rejected", "offline"):
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
