import asyncio
import logging
import traceback
from contextlib import AsyncExitStack
from datetime import datetime
from typing import List, Optional, Any, Dict

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool, CallToolResult

from core.enum.mcp import McpType
from core.exception.llm_exception import McpException

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_remote_server(self, mcp_server_url: str, mcp_type: McpType):
        """
        仅负责建立传输层连接并挂载到 ExitStack。
        不在此时执行协议 initialize()，以防由于阻塞导致 ExitStack 状态异常。
        """
        try:
            if mcp_type == McpType.STREAMABLE_HTTP:
                transport_cm = streamable_http_client(mcp_server_url)
                # 获取读写流，并将 transport 上下文注册到 stack
                stdio, write, _ = await self.exit_stack.enter_async_context(transport_cm)
                # 将 session 注册到 stack，确保 session 随 stack 一起关闭
                self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

            elif mcp_type == McpType.SSE:
                transport_cm = sse_client(mcp_server_url)
                stdio, write = await self.exit_stack.enter_async_context(transport_cm)
                self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

            if not self.session:
                raise ConnectionError(f"未能初始化 {mcp_type} 会话结构")

        except Exception as e:
            logger.error(f"MCP 物理层连接失败: {str(e)}")
            await self.close()
            raise e

    async def list_tools(self) -> List[Tool]:
        """获取工具列表"""
        if not self.session:
            raise RuntimeError("MCP 会话未就绪")
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """调用工具"""
        if not self.session:
            raise RuntimeError("MCP 会话未就绪")
        return await self.session.call_tool(tool_name, arguments)

    async def close(self):
        """极致防御性清理：防止任何清理阶段的报错向上抛出"""
        try:
            if self.exit_stack:
                await self.exit_stack.aclose()
        except Exception as e:
            logger.debug(f"清理 MCP 资源时忽略预期内异常: {e}")
        finally:
            self.session = None
            logger.debug("MCP 客户端资源已完全释放")


async def test_connection(url: str, mcp_type: McpType | str, timeout: int = 10):
    """
    分段式连通性测试：物理连接 -> 协议握手 -> 数据验证
    """
    start_time = datetime.now()
    test_client = MCPClient()

    try:
        # 1. 第一阶段：测试物理连接 (HTTP/SSE 握手)
        # 这一步如果不通（如 502/404），会立即报错，不会等 10s
        await asyncio.wait_for(
            test_client.connect_to_remote_server(url, mcp_type),
            timeout=max(2.0, timeout / 3)
        )

        # 2. 第二阶段：测试 MCP 协议握手 (Initialize)
        # initialize() 是最容易产生 anyio WouldBlock 的地方，必须单独控制
        if test_client.session:
            await asyncio.wait_for(
                test_client.session.initialize(),
                timeout=timeout / 2
            )

        # 3. 第三阶段：获取数据验证
        tools = await test_client.list_tools()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"MCP 测试通过: {url} | 耗时: {duration}s | 工具数: {len(tools)}")

        return {
            "success": True,
            "latency_sec": round(duration, 3),
            "tool_count": len(tools),
            "message": "连接成功"
        }

    except (asyncio.TimeoutError, asyncio.exceptions.CancelledError):
        logger.warning(f"MCP 测试超时: {url}")
        return {"success": False, "message": f"连接失败：远程服务在未响应"}
    except Exception as e:
        err_msg = str(e)
        traceback.print_exc()
        # 优化常见 HTTP 错误展示
        if "502" in err_msg:
            err_msg = "502 Bad Gateway (目标服务未启动或网关配置错误)"
        elif "404" in err_msg:
            err_msg = "404 Not Found (请检查 MCP 接口路径是否正确)"

        logger.error(f"MCP 测试失败: {url} | 原因: {err_msg}")
        return {"success": False, "message": f"连接失败: {err_msg}"}
    finally:
        # 必须确保资源回收
        await test_client.close()


class MCPManager:
    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}

    async def get_or_create_client(self, server_id: str, url: str, mcp_type: McpType) -> MCPClient:
        if server_id in self._clients:
            client = self._clients[server_id]
            if client.session:
                return client
            # 如果 session 为空（之前的死连接），清理掉
            await self.close_client(server_id)

        client = MCPClient()
        try:
            # 正常业务连接逻辑，可以不分段，但要保证初始化
            await client.connect_to_remote_server(url, mcp_type)
            if client.session:
                await client.session.initialize()

            self._clients[server_id] = client
            return client
        except Exception as e:
            await client.close()
            logger.error(f"创建 MCP 客户端失败 [{server_id}]: {e}")
            raise McpException(f"无法连接 MCP 服务: {str(e)}")

    async def close_client(self, server_id: str):
        client = self._clients.pop(server_id, None)
        if client:
            await client.close()

    async def close_all(self):
        for server_id in list(self._clients.keys()):
            await self.close_client(server_id)