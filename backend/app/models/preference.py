# -*- coding: utf-8 -*-
"""用户兴趣偏好模型：登录后选择的感兴趣栏目（多对多，多选）"""
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint

from ..database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_user_category"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="偏好ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True, comment="栏目ID")
    created_at = Column(DateTime, default=datetime.now, comment="选择时间")
