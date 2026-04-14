from enum import StrEnum

class McpType(StrEnum):
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"

    @classmethod
    def get_desc(cls, mcp_type):
        mapping = {
            cls.SSE: "SSE",
            cls.STREAMABLE_HTTP: "StreamableHttp"
        }
        return mapping.get(mcp_type, "未知类型")

class McpConnectedStatus(StrEnum):
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"

    @classmethod
    def get_desc(cls, status):
        mapping = {
            cls.NOT_CONNECTED: "未连接",
            cls.CONNECTED: "已连接"
        }
        return mapping.get(status, "未知状态")