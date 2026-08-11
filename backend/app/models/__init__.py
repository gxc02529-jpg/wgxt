# -*- coding: utf-8 -*-
"""模型包：集中导入所有模型，确保 Base.metadata 能发现全部表"""
from .user import User
from .category import Category
from .article import Article, article_categories
from .review import ArticleReview
from .resource import Resource
from .portal import PortalModule
from .event import EventLog
from .interaction import UserAction
from .system_setting import SystemSetting
from .dify_workflow import DifyWorkflow

__all__ = [
    "User", "Category", "Article", "article_categories", "ArticleReview",
    "Resource", "PortalModule", "EventLog", "UserAction", "SystemSetting", "DifyWorkflow",
]
