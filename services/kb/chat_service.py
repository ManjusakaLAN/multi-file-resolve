import json
import logging
from typing import AsyncGenerator

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import SecretStr
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from core.enum.model import ModelType
from core.infrastructure.vector_db import MilvusVectorDB
from models.conversation import ChatMessage, ChatSession
from models.file import FileRecord
from models.knowledge import KnowledgeBase
from services.kb.point_service import PointService
from services.llm.model_service import ModelService

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, db: AsyncSession, vdb: MilvusVectorDB, model_service: ModelService, point_service: PointService):
        self.db = db
        self.vdb = vdb
        self.model_service = model_service
        self.point_service = point_service

    async def rag_recall(self, kb_ids: list[str],
                         query: str,
                         top_k: int,
                         confidence: float):
        """
        知识库召回：实现按文件聚类、切片排序、置信度过滤及分数百分比化
        数据结构如下:
        [
            {
                "file_id": "general/2026_05/7c4409cc76484d6fa2d14b8824ee8a0c_数字时代的个人知识管理.docx",
                "file_name": "数字时代的个人知识管理.docx",
                "score": "",
                "is_like": null,
                "chunks": [
                    {
                        "slice_index": 0,
                        "content": "# 数字时代的个人知识管理：方法、工具与\n\n# 实践路径\n\n# 引言  \n在信息爆炸的21世纪，个体每天接触的信息量已远超人类历史任何时期。据统计，成年人日均接收约10万条信息，其中有效信息占比不足5%。面对海量数据，如何系统性筛选、整合、应用知识，成为提升个人竞争力的核心命题。个人知识管理（Personal KnowledgeManagement，PKM）作为一套方法论体系，正帮助越来越多的人从信息焦虑中解脱，实现知识的有效沉淀与价值转化。本文将从理论框架、工具选择、实践策略三个维度，构建一套可落地的个人知识管理系统。\n\n# 一、个人知识管理的理论基础\n\n# 1.1 知识的层级模型  \n知识管理领域普遍将知识划分为四个层级：  \n数据层：未经处理的原始信息，如孤立的数字、文字片段；\n信息层：经过结构化处理的数据，如报告中的图表、新闻事件；\n 知识层：对信息的深度理解与关联，如通过案例总结的方法论；\n智慧层：知识的创造性应用，如解决复杂问题的创新方案。  \n个人知识管理的本质是推动信息从低层级向高层级流动，最终形成可复用的智慧资产。",
                        "score": "3.08%"
                    },
                    {
                        "slice_index": 1,
                        "content": "# 1.2 PKM 的核心原则  \n以用为导：知识采集需围绕个人目标（如职业发展、技能提升），避免无目的囤积；\n可操作性：将抽象知识转化为具体行动步骤，例如将“时间管理”拆解为“番茄工作法实施流程”；\n 动态迭代：定期回顾知识体系，删除过时内容，补充新认知，保持系统活力。\n\n# 二、知识管理工具矩阵搭建\n\n# 2.1 信息输入工具  \n碎片化信息捕获：使用“Flomo”“印象笔记”等工具，通过语音、文字、图片快速记录灵感；微信“浮窗+稍后读”功能可暂存公众号文章，避免即时阅读干扰。\n系统性学习载体：电子书采用“Kindle+MarginNote”组合，支持标注导出；在线课程搭配“XMind”梳理知识框架，将视频内容转化为思维导图。\n\n# 2.2 知识加工工具  \n结构化存储：采用“Notion”搭建双向链接知识库，按“领域-主题-子主题”三级分类，例如“职场技能>沟通表达>非暴力沟通”；\n 深度思考辅助：使用“Logseq”进行双链笔记写作，通过“块引用”功能关联不同场景下的知识应用案例，强化记忆网络。",
                        "score": "3.23%"
                    }
                ]
            },
            {

            }
        ]
        """
        # 如果没有kb_ids 直接返回 []
        if not kb_ids or len(kb_ids) == 0:
            return []

        # 1. 获取 Embedding 向量
        model_invoke_info = await self.model_service.get_model_invoke_info(model_type=ModelType.EMBEDDING)
        embedding_model_client = OpenAI(api_key=model_invoke_info.api_key, base_url=model_invoke_info.base_url)

        embedding_content = embedding_model_client.embeddings.create(
            model=model_invoke_info.model_id,
            input=query,
            encoding_format="float"
        )
        query_vector = embedding_content.data[0].embedding

        # 2. 跨知识库并行/串行检索
        all_hits = []
        for kb_id in kb_ids:
            kb_stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            kb_info = (await self.db.execute(kb_stmt)).scalars().first()
            if not kb_info: continue

            # 这里的 results 假设是 Milvus 返回的标准格式 [hits]
            results = self.vdb.search(
                collection_name=kb_info.collection_name,
                query_text=query,
                dense_vector=query_vector,
                limit=top_k,
                output_fields=["text", "meta_data"],
            )

            # 处理返回结构 (兼容 hybrid_search 或普通 search)
            hits = results[0] if isinstance(results, list) and len(results) > 0 else []
            all_hits.extend(hits)

        # 3. 按置信度初筛并全局排序 (取前 top_k)
        # 过滤掉低于置信度的原始分数
        valid_hits = [h for h in all_hits if h.get('distance', 0) >= confidence]
        valid_hits.sort(key=lambda x: x.get('distance', 0), reverse=True)
        valid_hits = valid_hits[:top_k]

        # 4. 按文件进行聚类加工
        file_map = {}

        for hit in valid_hits:
            entity = hit.get('entity', {})
            metadata = entity.get('meta_data', {})
            file_key = metadata.get('file_key')
            raw_score = hit.get('distance', 0)

            if not file_key: continue

            if file_key not in file_map:
                file_stmt = select(FileRecord).where(FileRecord.file_key == file_key)
                file_info_obj = (await self.db.execute(file_stmt)).scalars().first()

                file_map[file_key] = {
                    "file_key": file_key,
                    "file_name": file_info_obj.name if file_info_obj else file_key.split('/')[-1],
                    "max_raw_score": raw_score,  # 用于后续文件间排序
                    "score": "",  # 最终显示的百分比字符串
                    "is_like": None,
                    "chunks": []
                }

            # 更新文件的最高原始分数
            file_map[file_key]["max_raw_score"] = max(file_map[file_key]["max_raw_score"], raw_score)

            # 添加切片内容，并将切片分数转为百分比
            file_map[file_key]["chunks"].append({
                "slice_index": metadata.get('slice_index'),
                "content": entity.get('text'),
            })

        # 5. 最终结构化整合与格式化
        recall_info = []
        for f_key in file_map:
            item = file_map[f_key]
            # 按照切片在文档中的物理顺序排序
            item["chunks"].sort(key=lambda x: x["slice_index"])
            # 移除用于辅助排序的原始分数键
            temp_sort_score = item.pop("max_raw_score")
            recall_info.append((temp_sort_score, item))

        # 按文件最高原始分数降序排列文件列表
        recall_info.sort(key=lambda x: x[0], reverse=True)

        # 提取纯净的 list 结果
        final_recall_info = [data[1] for data in recall_info]

        return final_recall_info

    async def _get_or_create_session(self, user_id: str, session_id: str, query: str) -> ChatSession:
        """获取或创建会话"""
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()

        if not session:
            # 第一次对话，创建新会话
            # 默认取 query 的前 20 个字作为初始主题
            topic = query[:20] + "..." if len(query) > 20 else query
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                topic=topic,
                session_type="single"  # 默认为 single，可在 controller 层逻辑判断
            )
            self.db.add(session)
            await self.db.flush()
        return session

    async def get_history_messages(self, session_id: str, limit: int = 6) -> list[ChatMessage]:
        """获取最近 X 条历史对话记录"""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.create_time))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        # 获取后需要反转顺序，使其符合对话流（从旧到新）
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def rag_chat_stream(
            self,
            user_id: str,
            session_id: str,
            query: str,
            kb_ids: list[str],
            model_id: str,
            history_limit: int = 6
    ) -> AsyncGenerator[str, None]:

        # 1. 获取/创建会话
        session = await self._get_or_create_session(user_id, session_id, query)

        # 2. 获取历史记录并转换为 LangChain 消息格式
        history_records = await self.get_history_messages(session_id, limit=history_limit)
        chat_history = []
        for msg in history_records:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                chat_history.append(AIMessage(content=msg.content))

        # 3. 知识库召回
        final_recall_info = await self.rag_recall(kb_ids, query, 5, 0.016)

        # 将召回内容拼接成 Prompt 上下文
        context_text = ""
        if final_recall_info:
            context_segments = []
            for file in final_recall_info:
                for chunk in file["chunks"]:
                    context_segments.append(f"来自文件《{file['file_name']}》:\n{chunk['content']}")
            context_text = "\n\n".join(context_segments)

        # 4. 构造完整的消息列表
        # 系统提示词注入召回背景
        system_content = (
            "你是一个智能问答助手。请优先基于以下提供的【知识库内容】来回答用户问题。\n"
            "如果知识库内容与问题不相关，请利用你的自身知识储备进行回复。\n"
            f"【知识库内容】：\n{context_text}"
        )

        conversations = [SystemMessage(content=system_content)]
        conversations.extend(chat_history)  # 注入历史记录
        conversations.append(HumanMessage(content=query))  # 注入当前问题

        # 5. 调用大模型流式输出
        model_invoke_info = await self.model_service.get_model_invoke_info(model_id=model_id)
        llm = ChatOpenAI(
            model=model_invoke_info.model_id,
            base_url=model_invoke_info.base_url,
            api_key=SecretStr(model_invoke_info.api_key),
            streaming=True
        )

        full_ai_response = ""

        # 首先推送召回的元数据（可选，让前端知道引用了哪些文件）
        yield f"data: {json.dumps({'type': 'metadata', 'source': final_recall_info}, ensure_ascii=False)}\n\n"

        async for chunk in llm.astream(conversations):
            content = chunk.content
            if content:
                full_ai_response += content
                yield f"data: {json.dumps({'type': 'content', 'content': content}, ensure_ascii=False)}\n\n"

        # 6. 持久化存储对话记录
        try:
            # 存储用户问题
            user_msg_record = ChatMessage(
                session_id=session_id,
                role="user",
                content=query
            )
            # 存储 AI 回答及召回快照
            ai_msg_record = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=full_ai_response,
                source_context=final_recall_info  # 存储召回的 JSON 快照
            )
            self.db.add_all([user_msg_record, ai_msg_record])
            await self.db.commit()
            logger.info(f"会话 {session_id} 记录已更新")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"存储对话记录失败: {str(e)}")

        yield "data: [DONE]\n\n"

    async def recall_file_evaluate(self, message_id: str, file_key: str, evaluate_result: str, user_id: str):
        """
        更新评价：支持 like, dislike, 以及取消("")
        """
        # 1. 获取消息记录
        stmt = select(ChatMessage).where(ChatMessage.id == message_id)
        msg = (await self.db.execute(stmt)).scalars().first()

        if not msg:
            logger.error(f"未找到消息记录: {message_id}")
            return False

        # 2. 计算目标状态
        # evaluate_result 为 "like" -> True, "dislike" -> False, "" -> None
        target_is_like = None
        if evaluate_result == "like":
            target_is_like = True
        elif evaluate_result == "dislike":
            target_is_like = False

        current_context = list(msg.source_context) if msg.source_context else []
        point_increment = 0
        found_file = False

        for file_item in current_context:
            # 注意确认字段名是 file_id 还是 file_key，此处匹配你传入的 key
            if file_item.get("file_id") == file_key or file_item.get("file_key") == file_key:
                found_file = True
                current_is_like = file_item.get("is_like")  # 现有状态: True, False, None

                if current_is_like == target_is_like:
                    return True  # 状态一致，幂等返回

                # --- 核心积分逻辑变动 ---
                if target_is_like is None:
                    # 取消操作
                    if current_is_like is True:  # Like -> Cancel
                        point_increment = -1
                    elif current_is_like is False:  # Dislike -> Cancel
                        point_increment = 1
                else:
                    # 赋予新状态 (Like 或 Dislike)
                    if current_is_like is None:
                        point_increment = 1 if target_is_like else -1
                    elif current_is_like is True and target_is_like is False:
                        point_increment = -2
                    elif current_is_like is False and target_is_like is True:
                        point_increment = 2

                # 更新 JSON 快照中的字段
                file_item["is_like"] = target_is_like
                break

        if not found_file:
            logger.warning(f"在该消息的召回上下文中未找到文件: {file_key}")
            return False

        # 3. 标记 JSON 修改并保存消息状态
        msg.source_context = current_context
        flag_modified(msg, "source_context")

        # 4. 执行积分同步
        if point_increment != 0:
            file_info = (await self.db.execute(
                select(FileRecord).where(FileRecord.file_key == file_key)
            )).scalars().first()

            if file_info:
                # 注意：如果 target_is_like 为 None，代表取消评价，建议传给积分服务一个明确标识
                await self.point_service.file_like_dislike_point_change(
                    operator_id=user_id,
                    file_id=str(file_info.id),
                    is_like=target_is_like,  # 可能为 True, False, None
                    reward_amount=point_increment
                )

        # 5. 提交事务
        try:
            await self.db.commit()
            logger.info(f"用户 {user_id} 更新评价 {file_key} 为 {evaluate_result}, 积分变动: {point_increment}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"评价提交失败: {str(e)}")
            raise e
