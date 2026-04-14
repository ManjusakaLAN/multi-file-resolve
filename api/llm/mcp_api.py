from typing import Optional, List
from fastapi import Depends, Query, Body, Request
from api.deps import get_mcp_service, get_mcp_manager
from api.llm import mcp_router
from schemas.mcp import McpServerCreate, McpServerResponse, McpServerUpdate
from schemas.general import Result, PageResponse
from services.mcp.mcp_service import McpService
from services.mcp.mcp_manager import test_connection, MCPManager
from core.enum.mcp import McpType, McpConnectedStatus


@mcp_router.get("/server/page_list", response_model=PageResponse[McpServerResponse], description="分页获取MCP服务配置")
async def get_mcp_server_page_list(
        name: Optional[str] = Query(None, description="服务名称"),
        mcp_type: Optional[McpType | str] = Query(None, description="服务类型"),
        connected_status: Optional[McpConnectedStatus | str] = Query(None, description="连接状态"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1),
        mcp_service: McpService = Depends(get_mcp_service)
):
    """
    获取mcp 服务 (分页)
    :param name:
    :param mcp_type:
    :param connected_status:
    :param page:
    :param page_size:
    :param mcp_service:
    :return:
    """
    return await mcp_service.page_list_mcp(name, mcp_type, connected_status, page, page_size)


@mcp_router.get("/server/list", response_model=Result[List[McpServerResponse]], description="获取所有MCP服务配置")
async def get_mcp_server_list(
        name: Optional[str] = Query(None, description="服务名称"),
        mcp_type: Optional[str] = Query(None, description="服务类型"),
        connected_status: Optional[McpConnectedStatus | str] = Query(None, description="连接状态"),
        mcp_service: McpService = Depends(get_mcp_service)
):
    """
    获取mcp服务信息 (不分页)
    :param name:
    :param mcp_type:
    :param connected_status:
    :param mcp_service:
    :return:
    """
    return Result.success(message="获取成功", data=await mcp_service.list_mcp(name, mcp_type, connected_status))


@mcp_router.post("/server/create", response_model=Result[McpServerResponse], description="创建MCP服务配置")
async def create_mcp_server(
        mcp_in: McpServerCreate,
        request: Request,
        mcp_service: McpService = Depends(get_mcp_service),
):
    user_id = request.state.user_id
    data = await mcp_service.create_mcp(mcp_in, user_id)
    return Result.success(message="创建成功", data=data)


@mcp_router.put("/server/update", response_model=Result[McpServerResponse], description="更新MCP服务配置")
async def update_mcp_server(
        mcp_update: McpServerUpdate,
        mcp_service: McpService = Depends(get_mcp_service)
):
    data = await mcp_service.update_mcp(mcp_update)
    return Result.success(message="更新成功", data=data)


@mcp_router.delete("/server/delete", response_model=Result[bool], description="删除MCP服务配置")
async def delete_mcp_server(
        mcp_id: str = Body(..., description="服务ID", embed=True),
        mcp_service: McpService = Depends(get_mcp_service)
):
    data = await mcp_service.delete_mcp(mcp_id)
    return Result.success(message="删除成功", data=data)


@mcp_router.get("/server/test", response_model=Result, description="测试MCP连通性")
async def test_mcp_connection(
        mcp_id: str = Query(..., description="服务ID", embed=True),
        mcp_service: McpService = Depends(get_mcp_service),
):
    """
    测试 MCP 服务是否可用，但不保持连接
    """

    mcp_info = await mcp_service.get_mcp_by_id(mcp_id)
    test_result = await test_connection(mcp_info.mcp_url, mcp_info.mcp_type)
    if test_result["success"]:
        await mcp_service.update_mcp_status(mcp_id, McpConnectedStatus.CONNECTED)
        return Result.success(message="测试连接成功", data=test_result)
    else:
        await mcp_service.update_mcp_status(mcp_id, McpConnectedStatus.NOT_CONNECTED)
        return Result.fail(message=test_result["message"])
