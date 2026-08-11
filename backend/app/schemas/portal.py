# -*- coding: utf-8 -*-
"""门户模块请求体 Schema"""
from typing import Any

from pydantic import BaseModel, Field


class PortalModuleIn(BaseModel):
    module_key: str = Field(min_length=1, max_length=50, description="模块标识")
    title: str = Field(default="", max_length=100, description="模块标题")
    content: Any = None
    enabled: bool = True


class ThemeSwitchIn(BaseModel):
    """切换门户主题"""
    theme: str = Field(min_length=1, max_length=50, description="主题标识（editorial/cyber/comic）")

