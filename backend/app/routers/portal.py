# -*- coding: utf-8 -*-
"""门户模块接口：前台读取，后台（管理员）配置轮播/公告；门户主题切换"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.deps import require_roles
from ..database import get_db
from ..models.portal import PortalModule
from ..models.user import User
from ..schemas.portal import PortalModuleIn, ThemeSwitchIn
from ..services.settings_service import get_setting, set_setting

router = APIRouter(prefix="/portal", tags=["门户"])

# 门户可选主题：扩充新风格时在此登记，并同步 frontend/src/styles/themes.css 的 .theme-* 覆盖块
PORTAL_THEMES = ["editorial", "cyber", "comic"]


@router.get("/theme", summary="获取当前门户主题（公开）")
def get_portal_theme(db: Session = Depends(get_db)):
    theme = get_setting(db, "portal_theme", default="editorial")
    if theme not in PORTAL_THEMES:
        theme = "editorial"
    return {"theme": theme}


@router.put("/theme", summary="切换门户主题（管理员）")
def set_portal_theme(
    body: ThemeSwitchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    if body.theme not in PORTAL_THEMES:
        raise HTTPException(400, f"不支持的风格：{body.theme}，可选：{', '.join(PORTAL_THEMES)}")
    set_setting(
        db,
        "portal_theme",
        body.theme,
        value_type="string",
        description="前台门户主题：editorial 经典编辑 / cyber 赛博霓虹 / comic 漫画波普",
    )
    db.commit()
    return {"message": "主题已切换", "theme": body.theme}


@router.get("/modules", summary="获取启用的门户模块（前台）")
def get_modules(db: Session = Depends(get_db)):
    modules = db.query(PortalModule).filter(PortalModule.enabled.is_(True)).all()
    return {"items": [m.to_dict() for m in modules]}


@router.post("/modules", summary="新建门户模块（管理员）")
def create_module(body: PortalModuleIn, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    if db.query(PortalModule).filter(PortalModule.module_key == body.module_key).first():
        raise HTTPException(400, "模块标识已存在")
    module = PortalModule(module_key=body.module_key, title=body.title,
                          content=body.content if body.content is not None else {}, enabled=body.enabled)
    db.add(module)
    db.commit()
    db.refresh(module)
    return {"message": "创建成功", "module": module.to_dict()}


@router.put("/modules/{module_key}", summary="编辑门户模块（管理员，如首页轮播）")
def update_module(module_key: str, body: PortalModuleIn, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    module = db.query(PortalModule).filter(PortalModule.module_key == module_key).first()
    if not module:
        raise HTTPException(404, "模块不存在")
    module.title = body.title
    module.content = body.content if body.content is not None else module.content
    module.enabled = body.enabled
    db.commit()
    db.refresh(module)
    return {"message": "保存成功", "module": module.to_dict()}

