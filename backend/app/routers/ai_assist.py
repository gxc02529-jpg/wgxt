# -*- coding: utf-8 -*-
"""AI 协作台接口：写稿页面的 AI 辅助功能（异步任务 + 轮询）

说明：
- 5 个 AI 功能接口改为"提交任务"：入参校验通过后立即返回 task_id，由后台线程池执行
  （见 services/ai_assist_worker.py），前端每 2 秒轮询任务状态获取结果。
- 当前任务执行体为占位假实现（秒级完成）；后续接入真实 AI 能力时只需替换
  services/ai_assist_worker.py 的 dispatch()，接口契约与前端无需改动。
- 任务执行完成后自动写入 ai_call_logs（成功写返回值、失败写错误信息），后台可查看调用记录。
- 接口要求登录（写手 / 管理员），用于记录调用人与任务归属。
- 规格文档：docs/ai_assist_async.md
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_roles
from ..core.pagination import paginate
from ..database import get_db
from ..models.ai_call import AICallLog
from ..models.ai_task import AITask
from ..models.user import User
from ..schemas.ai import AIAssistIn, AITaskOut, AITaskStatusOut
from ..services.ai_assist_worker import submit_task

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

# 各功能的前置输入条件：与前端 AIAssistDrawer.vue 的 canUse 保持一致
FEATURE_NEEDS = {
    FEATURE_CLASSIFY: ["title"],
    FEATURE_SUMMARY: ["title", "content"],
    FEATURE_REVIEW: ["title", "content"],
    FEATURE_CHECK: ["content"],
    FEATURE_SCORE: ["content"],
}

router = APIRouter(prefix="/ai/assist", tags=["AI 协作台"])
admin_router = APIRouter(prefix="/admin/ai-calls", tags=["后台-AI 调用记录"])


def _check_ai_inputs(feature_type: int, body: AIAssistIn) -> None:
    """提交任务前的前置校验：与前端按钮禁用条件一致，缺输入直接拒绝"""
    text_map = {
        "title": body.title.strip(),
        "content": body.content.strip(),
    }
    for field in FEATURE_NEEDS.get(feature_type, []):
        if not text_map.get(field):
            names = {"title": "文稿标题", "content": "文稿正文"}
            raise HTTPException(400, f"请先填写{names[field]}再调用 AI 功能")


def _create_task(db: Session, user: User, feature_type: int, body: AIAssistIn) -> AITask:
    """落库任务（pending）并提交到后台线程池，返回任务实体"""
    task = AITask(
        user_id=user.id,
        feature_type=feature_type,
        status="pending",
        input_params=body.model_dump(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    submit_task(task.id)
    return task


@router.post("/classify", summary="AI 分类：提交任务，根据标题自动选择栏目（异步执行）")
def ai_classify(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AITaskOut:
    """入参仅需标题；提交异步任务，前端轮询后按栏目中文名自动选中对应栏目"""
    _check_ai_inputs(FEATURE_CLASSIFY, body)
    task = _create_task(db, user, FEATURE_CLASSIFY, body)
    return {"task_id": task.id, "status": task.status}


@router.post("/summary", summary="AI 生成摘要：提交任务，根据标题与正文生成摘要（异步执行）")
def ai_summary(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AITaskOut:
    """入参为标题 + 正文；提交异步任务，前端轮询后把摘要回写到摘要输入框"""
    _check_ai_inputs(FEATURE_SUMMARY, body)
    task = _create_task(db, user, FEATURE_SUMMARY, body)
    return {"task_id": task.id, "status": task.status}


@router.post("/review", summary="AI 多维度审核：提交任务（异步执行）")
def ai_review(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AITaskOut:
    """入参为标题 + 正文；提交异步任务，前端轮询后展示各审核维度结论"""
    _check_ai_inputs(FEATURE_REVIEW, body)
    task = _create_task(db, user, FEATURE_REVIEW, body)
    return {"task_id": task.id, "status": task.status}


@router.post("/check", summary="AI 内容校验：提交任务，错别字/标点等错误检测（异步执行）")
def ai_check(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AITaskOut:
    """入参为正文；提交异步任务，前端轮询后展示错误列表并支持定位高亮"""
    _check_ai_inputs(FEATURE_CHECK, body)
    task = _create_task(db, user, FEATURE_CHECK, body)
    return {"task_id": task.id, "status": task.status}


@router.post("/score", summary="AI 文稿打分：提交任务（异步执行）")
def ai_score(
    body: AIAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AITaskOut:
    """入参为正文（可带标题）；提交异步任务，前端轮询后展示评分卡片"""
    _check_ai_inputs(FEATURE_SCORE, body)
    task = _create_task(db, user, FEATURE_SCORE, body)
    return {"task_id": task.id, "status": task.status}


@router.get("/tasks/{task_id}", summary="查询 AI 任务状态（本人或管理员）", response_model=AITaskStatusOut)
def ai_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """前端轮询任务状态；仅任务发起人本人或管理员可查看"""
    task = db.get(AITask, task_id)
    if not task:
        raise HTTPException(404, "AI 任务不存在")
    if task.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "无权查看他人的 AI 任务")
    return {
        "task_id": task.id,
        "feature_type": task.feature_type,
        "feature_name": FEATURE_NAMES.get(task.feature_type, "未知"),
        "status": task.status,
        "result": task.result_data,
        "error": task.error_message,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


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
