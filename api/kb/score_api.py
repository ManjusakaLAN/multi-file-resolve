from typing import List, Optional, Any, Dict
from fastapi import Depends, Request, Query, Body
from api.kb import kb_router
from api.deps import get_folder_service, get_point_service
from schemas.general import Result
from services.kb.folder_service import FolderService
from services.kb.point_service import PointService


# --- 1. 创建目录 ---
@kb_router.post("/score/file_read", response_model=Result[Any], description="阅读文件后增加积分")
async def file_read_point_add(
        request: Request,
        file_id: str = Body(..., description="文件ID", embed=True),
        point_service: PointService = Depends(get_point_service),
):
    return Result.success(message="添加积分成功",
                          data=await point_service.file_read_point_add(file_id=file_id, user_id=request.state.user_id))

@kb_router.post("/score/file_like", response_model=Result[Any], description="对文件检索结果进行点赞")
async def file_like_point_change(
        request: Request,
        file_id: str = Body(..., description="文件ID", embed=True),
        is_like: bool = Body(..., description="是否点赞", embed=True),
        point_service: PointService = Depends(get_point_service),
):
    # is_like bool值转换
    # --- is_like 兼容性增强处理 ---
    if isinstance(is_like, str):
        # 处理字符串：只有当明确为 true, 1, yes 时才为 True
        is_like_bool = is_like.lower() in ("true", "1", "yes", "y", "on")
    elif isinstance(is_like, (int, float)):
        # 处理数字：非 0 即为 True
        is_like_bool = bool(is_like)
    else:
        # 已经是布尔值或其他情况
        is_like_bool = bool(is_like)


    return Result.success(message="添加积分成功",
                          data=await point_service.file_like_dislike_point_change(operator_id=request.state.user_id,file_id=file_id, is_like=is_like_bool)
    )