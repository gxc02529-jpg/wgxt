# -*- coding: utf-8 -*-
"""AI 协作台异步任务执行器

职责：
- 后台线程池执行 AI 任务（当前为占位假实现，秒级完成；后续接入真实模型/Dify 工作流时
  只需替换 dispatch() 内部逻辑，接口契约与前端无需改动）
- 任务状态持久化到 ai_tasks（pending → running → success / failed）
- 任务执行完成后向 ai_call_logs 写调用记录（成功写返回值，失败写错误信息）

注意：后台线程不能复用请求级数据库 Session，必须自行通过 SessionLocal 开新会话。
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ..database import SessionLocal
from ..models.ai_task import AITask
from ..models.user import User
from ..services.ai_call_service import log_ai_call
from ..services.dify_service import DifyError, run_workflow

# 功能类型常量：与 ai_call_logs / ai_tasks.feature_type 注释保持一致
FEATURE_CLASSIFY = 1  # AI 分类
FEATURE_SUMMARY = 2   # AI 生成摘要
FEATURE_REVIEW = 3    # AI 多维度审核
FEATURE_CHECK = 4     # AI 内容校验
FEATURE_SCORE = 5     # AI 文稿打分

# 后台任务并发数：单机场景 4 个 worker 足够，可按需通过环境变量 AI_TASK_MAX_WORKERS 调大
_MAX_WORKERS = int(os.environ.get("AI_TASK_MAX_WORKERS", "4"))
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="ai-assist")




def _extract_summary_from_outputs(outputs) -> str:
    """从 Dify outputs 中提取可展示的摘要文本。

    Dify 工作流结束节点常返回 {"text": "..."}，text 可能是纯文本或 JSON 字符串；
    同时兼容 summary/text/result/one_sentence_summary 等常见字段。
    """
    if isinstance(outputs, str):
        text = outputs
    elif isinstance(outputs, dict):
        text = outputs.get("text") or outputs.get("summary") or outputs.get("result") or ""
        if not text and isinstance(outputs.get("outputs"), (str, dict)):
            text = outputs.get("outputs")
    else:
        text = ""

    if isinstance(text, dict):
        text = text.get("one_sentence_summary") or text.get("summary") or text.get("text") or ""
    if isinstance(text, str) and text.strip().startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = parsed.get("one_sentence_summary") or parsed.get("summary") or parsed.get("text") or text
        except (ValueError, TypeError):
            pass

    result = " ".join(str(text).split()).strip()
    if not result:
        raise ValueError("Dify工作流未返回可识别的摘要内容")
    return result



def _try_json(text: str):
    """尝试把字符串按 JSON 解析，失败返回 None"""
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def _load_prev_check(task_id, article_id, draft_key):
    """查询同一文稿上次内容校验的结果与正文，作为 last_llm / old_text 入参

    按当前任务归属的文稿（已保存用 article_id，未保存草稿用 draft_key）取最近一次成功任务；
    首次调用或没有历史时返回空串，避免把无关文稿的历史带进来。
    """
    db = SessionLocal()
    try:
        query = db.query(AITask).filter(
            AITask.feature_type == FEATURE_CHECK,
            AITask.status == "success",
        )
        if article_id is not None:
            query = query.filter(AITask.article_id == article_id)
        elif draft_key:
            query = query.filter(AITask.draft_key == draft_key)
        else:
            return "", ""
        if task_id is not None:
            query = query.filter(AITask.id != task_id)
        prev = query.order_by(AITask.id.desc()).first()
        if not prev:
            return "", ""
        # last_llm = 上次 Dify 工作流返回结果（JSON 串）；old_text = 上次调用时的正文
        last_llm = json.dumps(prev.result_data, ensure_ascii=False) if prev.result_data else ""
        old_text = (prev.input_params or {}).get("content") or ""
        return last_llm, old_text
    finally:
        db.close()


def _extract_check_items(outputs) -> list:
    """从 Dify outputs 中提取内容校验错误列表（[{错误类型,原文位置,修改结果,修改建议}, ...]）

    Dify 结束节点可能直接返回数组，也可能返回 {"text": "[...json 数组...]"} 等包装结构，统一解析。
    """
    raw = outputs
    if isinstance(raw, str):
        raw = _try_json(raw) or raw
    if isinstance(raw, dict):
        for key in ("items", "result", "outputs", "data", "text"):
            if isinstance(raw.get(key), (list, str)):
                raw = raw[key]
                break
    if isinstance(raw, str):
        raw = _try_json(raw) or []
    if not isinstance(raw, list):
        return []
    return [it for it in raw if isinstance(it, dict)]


def dispatch(feature_type: int, inputs: dict, context: dict | None = None) -> dict:
    """AI 功能执行入口（占位假实现）

    接入真实 AI 能力时，仅需在本函数内按 feature_type 调用真实模型 / Dify 工作流
    （如 run_workflow），保持返回值结构与假实现一致即可。
    context 可选：携带当前任务信息（task_id 等），用于查询同一文稿的历史调用。
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
        # 登记的工作流输入变量为 title + context（见 dify_workflows.input_schema）
        db = SessionLocal()
        try:
            data = run_workflow(
                db,
                inputs={"title": title, "context": content},
                name="article_summary",
            )
        finally:
            db.close()
        summary = _extract_summary_from_outputs(data.get("outputs") or {})
        return {"summary": summary}

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

        # 内容校验：把上一次校验的结果(last_llm)与当时正文(old_text)连同本次正文(now_text)
        # 一起传给 Dify 工作流 article_neirong，支持基于历史错误的增量纠错；首次调用历史为空串
        article_id = inputs.get("article_id") or None
        draft_key = inputs.get("draft_key") or None
        last_llm, old_text = _load_prev_check((context or {}).get("task_id"), article_id, draft_key)
        db = SessionLocal()
        try:
            data = run_workflow(
                db,
                inputs={
                    "last_llm": last_llm,
                    "now_text": content,
                    "old_text": old_text,
                },
                name="article_neirong",
            )
        finally:
            db.close()
        # 返回结构固定为 {"items": [...]}，前端 checkItems 直接渲染并支持高亮定位
        return {"items": _extract_check_items(data.get("outputs") or {})}

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
            result = dispatch(task.feature_type, task.input_params or {}, context={"task_id": task.id})
            task.status = "success"
            task.result_data = result
            task.error_message = None
            db.commit()
            # 成功调用记录（若用户已被删除则跳过记录，任务结果仍保留）
            if user:
                log_ai_call(db, user, task.feature_type, task.input_params or {}, result, article_id=task.article_id, draft_key=task.draft_key)
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
                        article_id=task.article_id,
                        draft_key=task.draft_key,
                    )
                except Exception:  # noqa: BLE001 - 记录失败不阻塞任务状态更新
                    db.rollback()
    finally:
        db.close()


def submit_task(task_id: int) -> None:
    """提交任务到后台线程池执行（提交接口调用）"""
    _executor.submit(_execute_task, task_id)