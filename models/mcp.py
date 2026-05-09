import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import Base


class McpServerConfig(Base):
    __tablename__ = "mcp_server_config"
    __table_args__ = {'comment': 'MCP服务配置记录'}

    # 主键 ID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="主键id"
    )

    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        comment="mcp服务名称"
    )

    mcp_type: Mapped[str] = mapped_column(
        String(32),
        comment="mcp服务类型 可选: sse / streamable_http"
    )

    mcp_url: Mapped[str] = mapped_column(
        String(512),
        comment="mcp服务地址,例如高德地图的mcp: http://mcp.amap.com:80/mcp?key=..."
    )

    # 状态字段
    connected_status: Mapped[str] = mapped_column(
        String(32),
        default='dis_connected',
        comment="mcp服务状态 not_connected 未连接 connected 已连接"
    )

    # 可选字段 (Mapped[str | None] 自动推导 nullable=True)
    description: Mapped[str | None] = mapped_column(
        Text,
        comment="mcp服务描述,一般由ai生成"
    )

    # 审计字段
    created_by: Mapped[str] = mapped_column(
        String(36),
        index=True,
        comment="创建人id"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间"
    )