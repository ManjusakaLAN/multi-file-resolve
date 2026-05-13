from typing import List, Optional, Any, Dict
from fastapi import Depends, Request, Query, Body
from api.kb import kb_router
from api.deps import get_folder_service
from schemas.general import Result
from services.kb.folder_service import FolderService


# --- 1. 创建目录 ---
@kb_router.post("/folder/create", response_model=Result[Any], description="在知识库中创建文件夹")
async def create_folder(
        kb_id: str = Body(..., description="知识库ID", embed=True),
        name: str = Body(..., description="文件夹名称", embed=True),
        parent_id: Optional[str] = Body(None, description="父目录ID", embed=True),
        folder_service: FolderService = Depends(get_folder_service),
):
    if parent_id == "":
        parent_id = None

    new_folder = await folder_service.create_kb_folder(
        kb_id=kb_id,
        name=name,
        parent_id=parent_id
    )
    return Result.success(message="目录创建成功", data={"id": new_folder.id})


# 修改目录名称
@kb_router.put("/folder/update", response_model=Result[Any], description="修改目录名称")
async def update_folder(
        folder_id: str = Body(..., description="目录ID", embed=True),
        name: str = Body(..., description="目录名称", embed=True),
        folder_service: FolderService = Depends(get_folder_service),
):
    await folder_service.update_kb_folder(
        folder_id=folder_id,
        name=name
    )


# --- 2. 获取目录树 (纯目录) ---
@kb_router.get("/folder/tree", response_model=Result[List[Dict[str, Any]]], description="获取知识库目录树结构")
async def get_folder_tree(
        kb_id: str = Query(..., description="知识库ID"),
        folder_service: FolderService = Depends(get_folder_service)
):
    tree = await folder_service.tree_list_folder(kb_id=kb_id)
    return Result.success(data=tree)


# --- 3. 获取目录及文件树 ---
@kb_router.get("/folder/full_tree", response_model=Result[Dict[str, Any]], description="获取知识库完整的目录及文件树")
async def get_full_tree(
        kb_id: str = Query(..., description="知识库ID"),
        folder_service: FolderService = Depends(get_folder_service)
):
    full_tree = await folder_service.tree_list_folder_and_file(kb_id=kb_id)
    return Result.success(data=full_tree)


# --- 4. 删除目录 ---
@kb_router.delete("/folder/{folder_id}", response_model=Result, description="删除文件夹")
async def delete_folder(
        folder_id: str,
        recursive: bool = Query(False, description="是否递归删除子目录"),
        folder_service: FolderService = Depends(get_folder_service)
):
    success, message = await folder_service.delete_folder(
        folder_id=folder_id,
        recursive=recursive
    )
    if not success:
        return Result.fail(message=message)
    return Result.success(message=message)


# --- 5. 移动文件到目录 ---
@kb_router.put("/folder/move_file", response_model=Result, description="移动文件到指定文件夹")
async def move_file(
        file_id: str = Body(..., description="文件ID", embed=True),
        target_folder_id: Optional[str] = Body(None, description="目标文件夹ID，为空则移至根目录", embed=True),
        folder_service: FolderService = Depends(get_folder_service)
):
    if target_folder_id == "":
        target_folder_id = None

    await folder_service.move_file_to_folder(
        file_id=file_id,
        target_folder_id=target_folder_id
    )
    return Result.success(message="移动成功")
