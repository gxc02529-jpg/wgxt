# -*- coding: utf-8 -*-
"""AI 协作台异步任务执行器

职责：
- 后台线程池执行 AI 任务（当前为占位假实现，秒级完成；后续接入真实模型/Dify 工作流时
  只需替换 dispatch() 内部逻辑，接口契约与前端无需改动）
- 任务状态持久化到 ai_tasks（pending → running → success / failed）
- 任务执行完成后向 ai_call_logs 写调用记录（成功写返回值，失败写错误信息）

注意：后台线程不能复用请求级数据库 Session，必须自行通过 SessionLocal 开新会话。
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ..database import SessionLocal
from ..models.ai_task import AITask
from ..models.user import User
from ..services.ai_call_service import log_ai_call

# 功能类型常量：与 ai_call_logs / ai_tasks.feature_type 注释保持一致
FEATURE_CLASSIFY = 1  # AI 分类
FEATURE_SUMMARY = 2   # AI 生成摘要
FEATURE_REVIEW = 3    # AI 多维度审核
FEATURE_CHECK = 4     # AI 内容校验
FEATURE_SCORE = 5     # AI 文稿打分

# 后台任务并发数：单机场景 4 个 worker 足够，可按需通过环境变量 AI_TASK_MAX_WORKERS 调大
_MAX_WORKERS = int(os.environ.get("AI_TASK_MAX_WORKERS", "4"))
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="ai-assist")


def dispatch(feature_type: int, inputs: dict) -> dict:
    """AI 功能执行入口（占位假实现）

    接入真实 AI 能力时，仅需在本函数内按 feature_type 调用真实模型 / Dify 工作流
    （如 run_workflow），保持返回值结构与假实现一致即可。
    """
    title = (inputs.get("title") or "").strip()
    content = (inputs.get("content") or "").strip()

    if feature_type == FEATURE_CLASSIFY:
        #ai文稿分类功能
        if not title:
            raise ValueError("请先填写文稿标题")
        # 调用 BERT 模型做标题分类；模型延迟加载（首次调用约 20 秒，之后复用），
        # 避免后端启动时加载模型拖慢启动并干扰 uvicorn reload
        from ..aimodel.predict import predict_fun
        result=predict_fun(title)

        return {"category_name": result}

    if feature_type == FEATURE_SUMMARY:
        if not title or not content:
            raise ValueError("请先填写文稿标题和正文")
        return {"summary": "这是摘要"}

    if feature_type == FEATURE_REVIEW:
        if not title or not content:
            raise ValueError("请先填写文稿标题和正文")
        return {
            "色情内容": False,
            "暴力内容": False,
            "用语文明": True,
            "涉政内容": True,
        }

    if feature_type == FEATURE_CHECK:
        if not content:
            raise ValueError("请先填写文稿正文")
        return {
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

    if feature_type == FEATURE_SCORE:
        if not content:
            raise ValueError("请先填写文稿正文")
        return {
            "items": [
                {"维度": "标题与正文适配程度", "得分": "15/20", "建议": "标题与正文匹配程度高"},
                {"维度": "用语规范", "得分": "10/20", "建议": "文稿用语偏口语化"},
            ],
            "总分": "80/100",
        }

    raise ValueError(f"未知的 AI 功能类型：{feature_type}")


def _execute_task(task_id: int) -> None:
    """后台线程执行单个 AI 任务（自建 Session，流程见规格文档第 4 节）"""
    db = SessionLocal()
    try:
        task = db.get(AITask, task_id)
        if not task:
            return
        task.status = "running"
        task.started_at = datetime.now()
        db.commit()

        user = db.get(User, task.user_id)
        try:
            result = dispatch(task.feature_type, task.input_params or {})
            task.status = "success"
            task.result_data = result
            task.error_message = None
            db.commit()
            # 成功调用记录（若用户已被删除则跳过记录，任务结果仍保留）
            if user:
                log_ai_call(db, user, task.feature_type, task.input_params or {}, result)
        except Exception as exc:  # noqa: BLE001 - 任务失败需完整落库供后台排查
            db.rollback()
            task = db.get(AITask, task_id)
            task.status = "failed"
            task.error_message = str(exc)[:500]
            db.commit()
            if user:
                try:
                    log_ai_call(
                        db, user, task.feature_type,
                        task.input_params or {},
                        {"error": task.error_message},
                    )
                except Exception:  # noqa: BLE001 - 记录失败不阻塞任务状态更新
                    db.rollback()
    finally:
        db.close()


def submit_task(task_id: int) -> None:
    """提交任务到后台线程池执行（提交接口调用）"""
    _executor.submit(_execute_task, task_id)
