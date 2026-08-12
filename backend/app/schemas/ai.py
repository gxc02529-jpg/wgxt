# -*- coding: utf-8 -*-
"""AI 协作台相关请求体 Schema"""
from pydantic import BaseModel, Field


class AIAssistIn(BaseModel):
    """AI 协作台通用入参：各功能按需取用其中字段"""
    title: str = Field(default="", max_length=500, description="文稿标题")
    summary: str = Field(default="", max_length=1000, description="文稿摘要（生成摘要功能不需要传）")
    content: str = Field(default="", description="文稿正文（HTML 原文）")
    category_ids: list[int] = Field(default_factory=list, description="当前已选栏目ID列表（可选，供 AI 参考）")
