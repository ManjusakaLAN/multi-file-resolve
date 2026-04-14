import logging
from typing import Optional, List, Any, Coroutine, Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from core.enum.mcp import McpConnectedStatus
from core.exception.llm_exception import McpException
from models.mcp import McpServerConfig as McpModel, McpServerConfig
from schemas.mcp import McpServerCreate, McpServerUpdate
from schemas.general import PageResponse
from services.mcp.mcp_manager import MCPManager
from util.db_util import paginate

logger = logging.getLogger(__name__)


class McpService:
    def __init__(self, db: AsyncSession, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.db = db

    async def page_list_mcp(
            self,
            name: Optional[str],
            mcp_type: Optional[str],
            connected_status: Optional[McpConnectedStatus],
            page: int = 1,
            page_size: int = 10
    ) -> PageResponse:
        """
        分页查询 MCP 服务配置
        """
        stmt = select(McpModel)

        filters = []
        if name:
            filters.append(McpModel.name.contains(name))
        if mcp_type:
            filters.append(McpModel.mcp_type == mcp_type)
        if connected_status:
            filters.append(McpModel.connected_status == connected_status)

        if filters:
            stmt = stmt.where(and_(*filters))

        # 按创建时间倒序排列
        stmt = stmt.order_by(McpModel.created_at.desc())
        return await paginate(self.db, stmt, page, page_size)

    async def list_mcp(self,
                       name: Optional[str],
                       mcp_type: Optional[str],
                       connected_status: Optional[McpConnectedStatus],
                       ) -> Sequence[McpServerConfig]:
        """
        获取所有 MCP 服务列表（不分页，通常用于初始化连接）
        """
        stmt = select(McpModel)
        filters = []
        if name:
            filters.append(McpModel.name.contains(name))
        if mcp_type:
            filters.append(McpModel.mcp_type == mcp_type)
        if connected_status:
            filters.append(McpModel.connected_status == connected_status)

        if filters:
            stmt = stmt.where(and_(*filters))

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_mcp_by_id(self, mcp_id: str) -> McpModel:
        """
        根据 ID 获取 MCP 配置
        """
        stmt = select(McpModel).where(McpModel.id == mcp_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise McpException(message="MCP 服务配置不存在")
        return item

    async def create_mcp(self, mcp_in: McpServerCreate, account_id: str) -> McpModel:
        """
        创建 MCP 服务配置
        """
        # 校验名称唯一性
        stmt = select(McpModel).where(McpModel.name == mcp_in.name)
        existing = await self.db.execute(stmt)
        if existing.scalar_one_or_none():
            raise McpException(message=f"服务名称 '{mcp_in.name}' 已存在")

        new_mcp = McpModel(
            **mcp_in.model_dump(),
            created_by=account_id
        )

        self.db.add(new_mcp)
        try:
            await self.db.commit()
            await self.db.refresh(new_mcp)
            return new_mcp
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建 MCP 服务失败: {e}")
            raise McpException(message="数据库写入失败")

    async def update_mcp(self, mcp_update: McpServerUpdate) -> McpModel:
        """
        更新 MCP 服务配置
        """
        # 1. 获取原记录
        mcp_item = await self.get_mcp_by_id(mcp_update.id)

        # 2. 名称唯一性校验（如果改了名字的话）
        if mcp_update.name and mcp_update.name != mcp_item.name:
            stmt = select(McpModel).where(
                and_(McpModel.name == mcp_update.name, McpModel.id != mcp_update.id)
            )
            existing = await self.db.execute(stmt)
            if existing.scalar_one_or_none():
                raise McpException(message=f"服务名称 '{mcp_update.name}' 已被占用")

        # 3. 动态更新字段
        update_data = mcp_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(mcp_item, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(mcp_item)
            # mcp配置被更改了 关闭原来的mcp连接
            await self.mcp_manager.close_client(mcp_item.id)
            await self.update_mcp_status(mcp_item.id, McpConnectedStatus.NOT_CONNECTED)

            return mcp_item
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新 MCP 服务失败: {e}")
            raise McpException(message="数据库更新失败")

    async def delete_mcp(self, mcp_id: str) -> bool:
        """
        删除 MCP 服务配置
        """
        mcp_item = await self.get_mcp_by_id(mcp_id)
        try:
            await self.db.delete(mcp_item)
            await self.db.commit()
            # 关闭mcp连接
            await self.mcp_manager.close_client(mcp_id)
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除 MCP 服务失败: {e}")
            raise McpException(message="数据库删除失败")

    async def update_mcp_status(self, mcp_id: str, connect_status: McpConnectedStatus):
        """
        更新 MCP 连接状态 (供 MCPManager 调用)
        """
        mcp_item = await self.get_mcp_by_id(mcp_id)
        mcp_item.connected_status = connect_status
        await self.db.commit()