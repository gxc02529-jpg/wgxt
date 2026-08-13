# -*- coding: utf-8 -*-
"""数据库引擎与会话管理（SQLAlchemy + PyMySQL），含自动建库工具"""
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text

from .config import settings

# 连接串：使用 utf8mb4 以完整支持中文与 emoji
DATABASE_URL = (
    f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,     # 取连接前先 ping，避免断线后拿到失效连接
    pool_recycle=3600,      # 连接 1 小时回收，防止 MySQL wait_timeout 断开
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _server_engine():
    """创建不指定数据库的服务器级连接（用于建库等管理操作）"""
    server_url = (
        f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/?charset=utf8mb4"
    )
    return create_engine(server_url, pool_pre_ping=True)


def ensure_database() -> None:
    """初始化数据库：若目标库不存在则自动创建（utf8mb4），已存在则跳过（幂等）。

    注意：需要 MySQL 账号具备 CREATE DATABASE 权限；若权限不足，
    可手动执行：
      CREATE DATABASE wengaofabu DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """
    # 校验库名，防止特殊字符注入到 CREATE DATABASE 语句中
    if not re.fullmatch(r"[A-Za-z0-9_]+", settings.DB_NAME):
        raise ValueError(f"数据库名不合法: {settings.DB_NAME}")

    server = _server_engine()
    try:
        with server.connect() as conn:
            exists = conn.execute(
                text("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = :name"),
                {"name": settings.DB_NAME},
            ).scalar()
            if not exists:
                conn.execute(
                    text(
                        f"CREATE DATABASE `{settings.DB_NAME}` "
                        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
                print(f"数据库 {settings.DB_NAME} 创建成功")
            else:
                print(f"数据库 {settings.DB_NAME} 已存在，跳过创建")
    finally:
        server.dispose()


def ensure_schema_compat() -> None:
    """幂等兼容迁移：article_reviews.reviewer_id 允许为空（系统自动审核时无人工审核人）。

    新建库时 create_all 已按新模型建表；旧库执行一次 MODIFY 即可，重复执行无副作用。
    """
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT IS_NULLABLE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'article_reviews' "
                "AND COLUMN_NAME = 'reviewer_id'"
            )
        ).first()
        if row and str(row[0]).upper() != "YES":
            conn.execute(text("ALTER TABLE article_reviews MODIFY COLUMN reviewer_id INT NULL"))
            print("已迁移：article_reviews.reviewer_id 允许为空（支持系统自动审核）")

    # 幂等新增 view_history 观看时长字段（老库补列，重复执行无副作用）
    with engine.begin() as conn:
        for col, ddl in (
            ("watch_seconds", "ALTER TABLE view_history ADD COLUMN watch_seconds INT NOT NULL DEFAULT 0"),
            ("watch_count", "ALTER TABLE view_history ADD COLUMN watch_count INT NOT NULL DEFAULT 0"),
        ):
            exists = conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'view_history' AND COLUMN_NAME = :col"
                ),
                {"col": col},
            ).first()
            if not exists:
                conn.execute(text(ddl))
                print(f"已迁移：view_history.{col} 新增成功")

    # 幂等新增 articles.content_source 纯文本字段，并从已有 content 剥离 HTML 回填
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'articles' AND COLUMN_NAME = 'content_source'"
            )
        ).first()
        if not exists:
            conn.execute(
                text(
                    "ALTER TABLE articles ADD COLUMN content_source TEXT NULL "
                    "COMMENT '正文纯文本（无HTML标签）'"
                )
            )
            print("已迁移：articles.content_source 新增成功")

    # 幂等新增 users.points 积分字段（老库补列，重复执行无副作用）
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'points'"
            )
        ).first()
        if not exists:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN points INT NOT NULL DEFAULT 0 "
                    "COMMENT '用户积分'"
                )
            )
            print("已迁移：users.points 新增成功")

    # 幂等新增 resources.storage 存储位置字段（local/oss，老库补列）
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resources' AND COLUMN_NAME = 'storage'"
            )
        ).first()
        if not exists:
            conn.execute(
                text(
                    "ALTER TABLE resources ADD COLUMN storage VARCHAR(10) NOT NULL DEFAULT 'local' "
                    "COMMENT '存储位置（local/oss）'"
                )
            )
            print("已迁移：resources.storage 新增成功")

    # 老数据回填：content_source 为空的行从 content 剥离 HTML 生成纯文本
    from sqlalchemy import or_

    from .models.article import Article
    from .services.text_utils import strip_html

    with SessionLocal() as db:
        rows = (
            db.query(Article.id, Article.content)
            .filter(or_(Article.content_source.is_(None), Article.content_source == ""))
            .all()
        )
        if rows:
            for aid, content in rows:
                db.query(Article).filter(Article.id == aid).update(
                    {"content_source": strip_html(content)},
                    synchronize_session=False,
                )
            db.commit()
            print(f"已回填 {len(rows)} 篇文章的 content_source")

        # 数据修复（幂等）：历史批量导入把 HTML 写进了摘要/纯文本，统一剥离为纯文本；
        # 并把旧导入产生的嵌套 <p><p>…</p></p> 还原为单层段落
        html_rows = (
            db.query(Article.id, Article.summary)
            .filter(Article.summary.like("%<%"), Article.summary.like("%>%"))
            .all()
        )
        if html_rows:
            for aid, summary in html_rows:
                db.query(Article).filter(Article.id == aid).update(
                    {"summary": strip_html(summary)[:200]},
                    synchronize_session=False,
                )
            db.commit()
            print(f"已修复 {len(html_rows)} 篇摘要中的 HTML 标签")

        src_html_rows = (
            db.query(Article.id, Article.content_source)
            .filter(Article.content_source.like("%<p%"))
            .all()
        )
        if src_html_rows:
            for aid, source in src_html_rows:
                db.query(Article).filter(Article.id == aid).update(
                    {"content_source": strip_html(source)},
                    synchronize_session=False,
                )
            db.commit()
            print(f"已修复 {len(src_html_rows)} 篇 content_source 中的 HTML 标签")

        nested_rows = (
            db.query(Article.id, Article.content)
            .filter(Article.content.like("%<p><p>%"))
            .all()
        )
        if nested_rows:
            for aid, content in nested_rows:
                fixed = content.replace("<p><p>", "<p>").replace("</p></p>", "</p>")
                db.query(Article).filter(Article.id == aid).update(
                    {"content": fixed},
                    synchronize_session=False,
                )
            db.commit()
            print(f"已修复 {len(nested_rows)} 篇正文的嵌套 <p> 标签")


def get_db():
    """FastAPI 依赖：每个请求一个数据库会话，请求结束自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
