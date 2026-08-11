# -*- coding: utf-8 -*-
"""初始化数据库：自动建库（若不存在）+ 建表 + 表结构兼容迁移 + 写入种子数据

用法：在 backend 目录下执行 python init_db.py
"""
from app.database import Base, engine, SessionLocal, ensure_database, ensure_schema_compat
from app.models import (  # noqa: F401
    user, category, channel, article, review, resource, portal, event, interaction,
    anonymous_action, system_setting, dify_workflow, view_history,
)
from app.core.security import hash_password
from app.models.user import User
from app.models.category import Category
from app.models.channel import Channel
from app.models.portal import PortalModule
from app.models.system_setting import SystemSetting


def seed():
    """写入种子数据（幂等：已存在则跳过）"""
    db = SessionLocal()
    try:
        # 1. 初始化账号：admin/admin123（管理员）、editor/editor123（编辑）、user/user123（普通用户）
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password_hash=hash_password("admin123"),
                        nickname="系统管理员", role="admin", status="active"))
        if not db.query(User).filter(User.username == "editor").first():
            db.add(User(username="editor", password_hash=hash_password("editor123"),
                        nickname="演示编辑", role="editor", status="active",
                        bio="负责科技、文化等栏目的稿件写作。"))
        if not db.query(User).filter(User.username == "user").first():
            db.add(User(username="user", password_hash=hash_password("user123"),
                        nickname="演示用户", role="user", status="active"))

        # 2. 示例栏目（可按需增删改）
        demo_categories = [
            ("shizheng", "时政", "时政要闻与政策解读", 1),
            ("jingji", "经济", "财经资讯与市场观察", 2),
            ("keji", "科技", "前沿科技与创新动态", 3),
            ("wenhua", "文化", "文化、艺术与人文阅读", 4),
            ("tiyu", "体育", "体育赛事与运动健康", 5),
            ("shehui", "社会", "社会新闻与民生话题", 6),
        ]
        for slug, name, desc, sort in demo_categories:
            if not db.query(Category).filter(Category.slug == slug).first():
                db.add(Category(slug=slug, name=name, description=desc, sort_order=sort))

        # 3. 默认分发渠道：门户（基础渠道，所有文稿默认包含且不可移除）
        if not db.query(Channel).filter(Channel.slug == "portal").first():
            db.add(Channel(
                name="门户",
                slug="portal",
                description="前台门户基础渠道，所有文稿默认分发，不可移除",
                is_default=True,
                status="active",
                sort_order=0,
            ))

        # 4. 默认门户模块：首页轮播图（空数据，管理员可在后台配置）
        if not db.query(PortalModule).filter(PortalModule.module_key == "banner").first():
            db.add(PortalModule(module_key="banner", title="首页轮播",
                                content=[], enabled=True))
        if not db.query(PortalModule).filter(PortalModule.module_key == "notice").first():
            db.add(PortalModule(module_key="notice", title="站内公告",
                                content="欢迎使用文稿发布系统！", enabled=True))

        # 5. 默认后台配置：自动审核开关（默认关闭，管理员可在后台「系统设置」中开启）
        if not db.query(SystemSetting).filter(SystemSetting.config_key == "auto_review").first():
            db.add(SystemSetting(
                config_key="auto_review",
                config_value="false",
                value_type="bool",
                description="开启后，文稿提交审核即自动通过两级审核并发布，无需人工审核",
            ))
        if not db.query(SystemSetting).filter(SystemSetting.config_key == "portal_theme").first():
            db.add(SystemSetting(
                config_key="portal_theme",
                config_value="editorial",
                value_type="string",
                description="前台门户主题：editorial 经典编辑 / cyber 赛博霓虹 / comic 漫画波普",
            ))
        if not db.query(SystemSetting).filter(SystemSetting.config_key == "site_grayscale").first():
            db.add(SystemSetting(
                config_key="site_grayscale",
                config_value="false",
                value_type="bool",
                description="哀悼灰度模式：开启后前台门户全站显示为黑白（用于名人逝世等场景）",
            ))

        db.commit()
        print("种子数据写入完成。")
        print("管理员账号: admin / admin123")
        print("编辑账号:   editor / editor123")
        print("用户账号:   user / user123")
    finally:
        db.close()


if __name__ == "__main__":
    print("正在检查/创建数据库 ...")
    ensure_database()
    print("正在创建数据表 ...")
    Base.metadata.create_all(bind=engine)
    print("正在检查表结构兼容性 ...")
    ensure_schema_compat()
    print("数据表创建完成。")
    seed()
