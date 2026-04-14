import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, func
from core.infrastructure.database import Base


class McpServerConfig(Base):
    __tablename__ = "mcp_server_config"
    __table_args__ = {'comment': 'MCP服务配置记录'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    name = Column(String(64), nullable=False, unique=True, comment="mcp服务名称")
    mcp_type = Column(String(32), nullable=False, comment="mcp服务类型 可选: sse / streamable_http")
    mcp_url = Column(String(512), nullable=False,
                     comment="mcp服务地址,例如高德地图的mcp: http://mcp.amap.com:80/mcp?key=c5497868ffeaad370b702f94820d3602")
    connected_status = Column(String(32), default='dis_connected', comment="mcp服务状态 not_connected 未连接 connected 已连接")
    description = Column(Text, comment="mcp服务描述,一般由ai生成")
    # 审计字段 - 与 FileRecord 保持一致
    created_by = Column(String(36), nullable=False, index=True, comment="创建人id")
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
