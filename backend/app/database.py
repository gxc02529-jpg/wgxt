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


def get_db():
    """FastAPI 依赖：每个请求一个数据库会话，请求结束自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
