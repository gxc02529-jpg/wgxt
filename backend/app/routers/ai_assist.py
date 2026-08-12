# -*- coding: utf-8 -*-
"""AI 协作台接口：写稿页面的 AI 辅助功能（当前为空实现，返回固定数据便于联调）

说明：
- 所有辅助功能均为占位实现，返回固定结果；后续在对应位置接入真实 AI 能力即可。
- 每次调用都会写入 ai_call_logs（见 services/ai_call_service.py），后台可查看调用记录。
- 接口要求登录（写手 / 管理员），用于记录调用人。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_roles
from ..core.pagination import paginate
from ..database import get_db
from ..models.ai_call import AICallLog
from ..models.user import User
from ..schemas.ai import AIAssistIn
from ..services.ai_call_service import log_ai_call

# 功能类型常量：与 ai_call_logs.feature_type 注释保持一致
FEATURE_CLASSIFY = 1  # AI 分类
FEATURE_SUMMARY = 2   # AI 生成摘要
FEATURE_REVIEW = 3    # AI 多维度审核
FEATURE_CHECK = 4     # AI 内容校验
FEATURE_SCORE = 5     # AI 文稿打分

FEATURE_NAMES = {
    FEATURE_CLASSIFY: "AI 分类",
    FEATURE_SUMMARY: "AI 生成摘要",
    FEATURE_REVIEW: "AI 多维度审核",
    FEATURE_CHECK: "AI 内容校验",
    FEATURE_SCORE: "AI 文稿打分",
}

router = APIRouter(prefix="/ai/assist", tags=["AI 协作台"])
admin_router = APIRouter(prefix="/admin/ai-calls", tags=["后台-AI 调用记录"])


@router.post("/classify", summary="AI 分类：根据标题自动选择栏目（空实现，默认返回“时政”）")
def ai_classify(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """入参仅需标题；占位返回固定栏目名“时政”，前端按栏目中文名自动选中对应栏目"""
    result = {"category_name": "时政"}
    log_ai_call(db, user, FEATURE_CLASSIFY, body.model_dump(), result)
    return {"message": "AI 分类完成", "data": result}


@router.post("/summary", summary="AI 生成摘要：根据标题与正文生成摘要（空实现，默认返回“这是摘要”）")
def ai_summary(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """入参为标题 + 正文；占位返回固定摘要，前端回写到摘要输入框"""
    result = {"summary": "这是摘要"}
    log_ai_call(db, user, FEATURE_SUMMARY, body.model_dump(), result)
    return {"message": "AI 摘要生成完成", "data": result}


@router.post("/review", summary="AI 多维度审核（空实现，默认返回固定维度结论）")
def ai_review(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """入参为标题 + 正文；占位返回各审核维度是否通过（布尔值），前端展示为通过/未通过"""
    result = {
        "色情内容": False,
        "暴力内容": False,
        "用语文明": True,
        "涉政内容": True,
    }
    log_ai_call(db, user, FEATURE_REVIEW, body.model_dump(), result)
    return {"message": "AI 审核完成", "data": result}


@router.post("/check", summary="AI 内容校验：错别字/标点等错误检测（空实现，默认返回两条示例错误）")
def ai_check(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """入参为正文；占位返回错误数组，前端点击错误项在正文中高亮原文位置"""
    result = {
        "items": [
            {
                "错误类型": "标点错误",
                "原文位置": "的问题。因此",
                "修改结果": "的问题？因此",
                "修改建议": "提出疑问要用问号",
            },
            {
                "错误类型": "错别字",
                "原文位置": "用户登陆的问题",
                "修改结果": "用户登录的问题",
                "修改建议": "登陆为错别字",
            },
        ]
    }
    log_ai_call(db, user, FEATURE_CHECK, body.model_dump(), result)
    return {"message": "AI 校验完成", "data": result}


@router.post("/score", summary="AI 文稿打分（空实现，默认返回固定维度得分与总分）")
def ai_score(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """入参为正文（可带标题）；占位返回各维度得分与总分，前端展示评分卡片"""
    result = {
        "items": [
            {"维度": "标题与正文适配程度", "得分": "15/20", "建议": "标题与正文匹配程度高"},
            {"维度": "用语规范", "得分": "10/20", "建议": "文稿用语偏口语化"},
        ],
        "总分": "80/100",
    }
    log_ai_call(db, user, FEATURE_SCORE, body.model_dump(), result)
    return {"message": "AI 打分完成", "data": result}


@admin_router.get("", summary="AI 调用记录列表（管理员，可按用户/功能类型筛选）")
def admin_ai_calls(
    keyword: str | None = Query(default=None, description="按用户名/昵称模糊搜索"),
    feature_type: int | None = Query(default=None, description="AI 功能类型（1=AI分类 2=AI生成摘要 3=AI多维度审核 4=AI内容校验 5=AI文稿打分）"),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    """后台查看 AI 调用记录：入参、返回值、调用人与时间"""
    query = db.query(AICallLog, User).join(User, User.id == AICallLog.user_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(User.username.like(like), User.nickname.like(like)))
    if feature_type is not None:
        query = query.filter(AICallLog.feature_type == feature_type)
    query = query.order_by(AICallLog.created_at.desc(), AICallLog.id.desc())
    rows, total = paginate(query, page, page_size)

    items = []
    for log, user in rows:
        items.append({
            "id": log.id,
            "user_id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "feature_type": log.feature_type,
            "feature_name": FEATURE_NAMES.get(log.feature_type, "未知"),
            "input_params": log.input_params,
            "output_data": log.output_data,
            "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else None,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}
