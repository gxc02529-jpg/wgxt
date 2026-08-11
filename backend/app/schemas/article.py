# -*- coding: utf-8 -*-
"""文稿相关请求体 Schema"""
from typing import List

from pydantic import BaseModel, Field


class ArticleIn(BaseModel):
    """创建/编辑文稿"""
    title: str = Field(min_length=1, max_length=200, description="标题")
    summary: str = Field(default="", max_length=500, description="摘要")
    content: str = Field(default="", description="正文（HTML）")
    cover_url: str = Field(default="", max_length=255, description="封面图URL")
    category_ids: List[int] = Field(default_factory=list, description="所属栏目ID列表（可多选）")


class ReviewIn(BaseModel):
    """审核请求"""
    article_id: int
    level: int = Field(ge=1, le=2, description="审核级别：1 一审 / 2 二审")
    action: str = Field(pattern="^(approve|reject)$", description="approve 通过 / reject 驳回")
    comment: str = Field(default="", max_length=500, description="审核意见")

