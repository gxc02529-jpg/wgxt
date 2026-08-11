# -*- coding: utf-8 -*-
"""观看历史模型：记录用户最近浏览的已发布文稿（同一文稿重复观看仅更新时间）"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint

from ..database import Base


class ViewHistory(Base):
    __tablename__ = "view_history"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_view_history_user_article"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="记录ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True, comment="文稿ID")
    viewed_at = Column(DateTime, default=datetime.now, nullable=False, comment="最近观看时间")
