from fastapi import Depends, Request, Body
from starlette.responses import StreamingResponse
from api.deps import get_chat_service
from api.kb import kb_router
from schemas.general import Result
from services.kb.chat_service import ChatService
from typing import List, Any


@kb_router.post("/rag/chat", description="知识库增强检索对话 (SSE流式)")
async def rag_chat(
        request: Request,
        conversation_id: str = Body(..., description="会话ID", embed=True),
        query: str = Body(..., description="查询内容", embed=True),
        kb_ids: List[str] = Body(..., description="知识库ID列表", embed=True),
        model_id: str = Body(..., description="模型ID", embed=True),
        chat_service: ChatService = Depends(get_chat_service),
):
    """
    知识库 RAG 对话接口：
    1. 支持 SSE 流式返回
    2. 自动管理会话生命周期
    3. 返回包含元数据(检索来源)和正文内容
    """

    # 从 request.state 中获取由 Auth 中间件注入的用户 ID
    user_id = request.state.user_id

    # 封装流式响应头，确保前端正确识别流
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
        "X-Accel-Buffering": "no",  # 禁用 Nginx 缓存，确保实时性
    }

    return StreamingResponse(
        chat_service.rag_chat_stream(
            user_id=user_id,
            session_id=conversation_id,
            query=query,
            kb_ids=kb_ids,
            model_id=model_id,
            history_limit=6  # 可根据需要调整历史记录条数
        ),
        media_type="text/event-stream",
        headers=headers
    )


@kb_router.get("/rag/history/{conversation_id}", response_model=Result[Any], description="获取指定会话的历史记录")
async def get_chat_history(
        conversation_id: str,
        limit: int = 10,
        chat_service: ChatService = Depends(get_chat_service)
):
    history = await chat_service.get_history_messages(conversation_id, limit=limit)
    # 格式化输出
    data = []
    for msg in history:
        data.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "source_context": msg.source_context,  # 这里的 JSON 包含了点赞回显状态
            "create_time": msg.create_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    return Result.success(data=data)


@kb_router.post("/recall/file/evaluate", response_model=Result[bool], description="检索文件点评")
async def recall_file_evaluate(
        request: Request,
        message_id: str = Body(..., description="会话ID", embed=True),
        file_key: str = Body(..., description="文件key", embed=True),
        evaluate_result: str = Body(..., description="文件点评结果 like dislike 或 ''", embed=True),
        chat_service: ChatService = Depends(get_chat_service),
):
    return Result.success(message="点评成功",
                          data=await chat_service.recall_file_evaluate(message_id, file_key, evaluate_result,
                                                                       request.state.user_id))
