# -*- coding: utf-8 -*-
"""资源管理接口：上传、列表、删除（素材供文稿封面/正文引用）"""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..core.deps import get_current_user, require_roles
from ..core.pagination import paginate
from ..database import get_db
from ..models.resource import Resource
from ..models.user import User

router = APIRouter(prefix="/resources", tags=["资源"])

# 允许上传的文件类型
ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    "video/mp4", "video/webm",
    "audio/mpeg", "application/pdf",
}


@router.post("/upload", summary="上传资源文件（图片/视频/PDF）")
async def upload_resource(
    file: UploadFile = File(..., description="上传的文件"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"不支持的文件类型：{file.content_type}")

    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(400, f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")
    if not data:
        raise HTTPException(400, "文件为空")

    # 使用 UUID 重命名，避免重名与路径注入
    ext = os.path.splitext(file.filename or "")[1].lower()
    stored_name = f"{datetime.now():%Y%m%d}_{uuid.uuid4().hex}{ext}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(data)

    resource = Resource(
        user_id=user.id,
        filename=file.filename or stored_name,
        stored_name=stored_name,
        url=f"{settings.BASE_URL}/static/{stored_name}",
        file_type=file.content_type,
        file_size=len(data),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {"message": "上传成功", "resource": resource.to_dict()}


@router.get("", summary="资源列表（管理员看全部，其他人看自己的）")
def list_resources(
    keyword: str | None = Query(default=None),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Resource)
    if user.role != "admin":
        query = query.filter(Resource.user_id == user.id)
    if keyword:
        query = query.filter(Resource.filename.like(f"%{keyword}%"))
    query = query.order_by(Resource.id.desc())
    rows, total = paginate(query, page, page_size)
    return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "page_size": page_size}


@router.delete("/{resource_id}", summary="删除资源（上传者或管理员）")
def delete_resource(resource_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(404, "资源不存在")
    if user.role != "admin" and resource.user_id != user.id:
        raise HTTPException(403, "只能删除自己上传的资源")

    # 删除物理文件（校验路径在上传目录内）
    file_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, resource.stored_name))
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    if os.path.commonpath([file_path, upload_dir]) == upload_dir and os.path.isfile(file_path):
        os.remove(file_path)

    db.delete(resource)
    db.commit()
    return {"message": "删除成功"}

