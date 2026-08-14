# -*- coding: utf-8 -*-
"""AI 协作台相关请求体 Schema"""
from datetime import datetime

from pydantic import BaseModel, Field


class AIAssistIn(BaseModel):
    """AI 协作台通用入参：各功能按需取用其中字段"""
    title: str = Field(default="", max_length=500, description="文稿标题")
    summary: str = Field(default="", max_length=1000, description="文稿摘要（生成摘要功能不需要传）")
    content: str = Field(default="", description="文稿正文（HTML 原文）")
    category_ids: list[int] = Field(default_factory=list, description="当前已选栏目ID列表（可选，供 AI 参考）")


class AITaskOut(BaseModel):
    """AI 任务提交响应：立即返回 task_id，结果异步产生"""
    task_id: int = Field(description="任务ID，前端据此轮询状态")
    status: str = Field(description="任务初始状态：pending")


class AITaskStatusOut(BaseModel):
    """AI 任务状态查询响应"""
    task_id: int = Field(description="任务ID")
    feature_type: int = Field(description="AI功能类型（1~5）")
    feature_name: str = Field(description="AI功能中文名")
    status: str = Field(description="任务状态：pending/running/success/failed")
    result: dict | None = Field(default=None, description="任务成功后的业务返回数据")
    error: str | None = Field(default=None, description="失败原因（status=failed 时非空）")
    created_at: datetime | None = Field(default=None, description="任务提交时间")
    started_at: datetime | None = Field(default=None, description="任务开始执行时间")
    finished_at: datetime | None = Field(default=None, description="任务完成时间")
