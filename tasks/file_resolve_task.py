import logging
import traceback
import asyncio
import uuid
from pathlib import Path

from fastapi import UploadFile
from openai import AsyncOpenAI  # 切换到异步客户端
from sqlalchemy import select, update
from starlette.concurrency import run_in_threadpool
from celery import shared_task

from core.config import settings
from core.enum.kb import AnalysisStatus
from core.enum.model import ModelType
from core.infrastructure.database import AsyncSessionLocal
from core.infrastructure.storage import MinioClient, minio_client
from core.infrastructure.vector_db import MilvusVectorDB
from models.file import FileRecord
from models.knowledge import FileResolveTask, FileSliceRecord, KnowledgeBase
from services.file.file_service import FileService
from services.llm.model_service import ModelService
from util import file_util, ocr_util
from util.chunk_util import LLMSmartSlicer, slice_markdown_contract
from models.user import Role, User

logger = logging.getLogger(__name__)

import asyncio

vdb = MilvusVectorDB()


@shared_task(name="file_resolve_task")
def file_resolve_task(task_id: str):
    try:
        # 初始化同步客户端
        minio_client.init_client()

        # 使用 asyncio.run 是最现代且安全的方式
        # 它会自动处理创建 loop 和最后彻底关闭 loop 的逻辑
        asyncio.run(async_file_resolve_handler(task_id, vdb))

    except Exception as e:
        logger.error(f"Celery 任务捕获到顶层异常: {e}")


async def async_file_resolve_handler(task_id: str, vdb: MilvusVectorDB):
    """
    实际的异步业务逻辑处理函数
    """

    logger.info(f"🚀 开始处理文件解析任务 [task_id: {task_id}]")
    async with AsyncSessionLocal() as db:
        file_service = FileService(db, minio_client)
        model_service = ModelService(db)

        # 1. 获取任务信息
        logger.info(f"[Step 1] 正在查询任务和知识库信息 [task_id: {task_id}]...")
        result = await db.execute(select(FileResolveTask).where(FileResolveTask.id == task_id))
        task = result.scalars().first()
        if task is None:
            logger.error(f"❌ 任务 {task_id} 不存在，处理终止")
            return

        try:
            # 获取知识库信息
            kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == task.kb_id))
            kb_info = kb_result.scalars().first()
            if kb_info is None:
                raise Exception(f"知识库 {task.kb_id} 不存在")

            file_record_result = await db.execute(select(FileRecord).where(FileRecord.file_key == task.file_key))
            file_info = file_record_result.scalars().first()

            logger.info(
                f"✅ 成功获取任务信息 - 所属知识库: {kb_info.kb_name} [kb_id: {task.kb_id}], 文件Key: {task.file_key}")

            # 准备路径
            base_dir = Path.cwd()
            task_dir = base_dir / "temp" / f"ocr_{task.id}"
            task_dir_input = task_dir / "input"
            task_dir_output = task_dir / "output"
            task_dir_input.mkdir(parents=True, exist_ok=True)
            task_dir_output.mkdir(parents=True, exist_ok=True)

            source_file_path = task_dir_input / file_info.name
            pdf_path = task_dir_output / f"{source_file_path.stem}.pdf"

            if not file_info:
                raise Exception("源文件记录不存在")

            # 2. 文件下载与转换 (使用 run_in_threadpool 处理同步 IO)
            logger.info(f"[Step 2] 开始处理文件下载与格式转换 - 源文件: {file_info.name}")
            if file_info.name.lower().endswith(".pdf"):
                if not pdf_path.exists():
                    task.analysis_status = AnalysisStatus.CONVERT
                    await db.commit()
                    logger.info(f"📥 正在从 MinIO 下载 PDF 文件到: {pdf_path}")
                    await run_in_threadpool(minio_client.download, task.file_key, str(pdf_path))
                    logger.info("✅ PDF 文件下载完成")
                else:
                    logger.info("⚡ 本地已存在 PDF 文件，跳过下载")
            else:
                if not source_file_path.exists():
                    logger.info(f"📥 正在从 MinIO 下载源文件到: {source_file_path}")
                    await run_in_threadpool(minio_client.download, task.file_key, str(source_file_path))
                    logger.info("✅ 源文件下载完成")
                if not pdf_path.exists():
                    task.analysis_status = AnalysisStatus.CONVERT
                    await db.commit()
                    # LibreOffice 转换是耗时阻塞操作
                    logger.info(f"⚙️ 正在使用 LibreOffice 将文件转换为 PDF...")
                    await run_in_threadpool(file_util.convert_with_libreoffice, str(source_file_path),
                                            str(task_dir_output))
                    logger.info("✅ 文件转 PDF 完成")

            # 3. OCR 识别
            logger.info("[Step 3] 开始进行 OCR 识别处理")
            md_path = task.md_file_path
            if not md_path:
                task.analysis_status = AnalysisStatus.OCR_RESOLVE
                await db.commit()
                logger.info(f"🔍 正在调用 Mineru API 识别 PDF 并转为 Markdown...")
                md_path = await ocr_util.invoke_mineru_to_markdown(
                    file_path=str(pdf_path),
                    save_directory=str(task_dir_output),
                    api_url=settings.MINERU_API_URL
                )
                task.md_file_path = md_path
                await db.commit()
                logger.info(f"✅ OCR 识别完成，Markdown 已保存至: {md_path}")
            else:
                logger.info("⚡ 任务已存在 Markdown 文件记录，跳过 OCR")

            # 4. 上传 Markdown 文件
            logger.info("[Step 4] 准备上传 Markdown 文件至存储")
            if not task.md_file_key:
                logger.info("☁️ 正在上传 Markdown 文件...")
                with open(md_path, "rb") as f:
                    file_to_upload = UploadFile(file=f, filename=Path(md_path).name)
                    md_upload_info = await file_service.upload_file(file_to_upload, task.created_by)
                    task.md_file_key = md_upload_info.file_key
                    await db.commit()
                logger.info(f"✅ Markdown 文件上传完成, file_key: {task.md_file_key}")
            else:
                logger.info("⚡ Markdown 文件已上传过，跳过")

            # 5. 执行切片
            logger.info("[Step 5] 开始执行文档分块/切片")
            slice_result = await db.execute(select(FileSliceRecord).where(FileSliceRecord.task_id == task.id))
            file_slice_contents = slice_result.scalars().all()

            if not file_slice_contents:
                task.analysis_status = AnalysisStatus.FILE_CHUNK
                await db.commit()

                # logger.info("✂️ 正在调用大模型进行智能切片...")
                # model_invoke_info = await model_service.get_model_invoke_info()
                # slicer = LLMSmartSlicer(
                #     api_key=model_invoke_info.api_key,
                #     base_url=model_invoke_info.base_url,
                #     model_name=model_invoke_info.model_id,
                # )
                # # 切片逻辑如果是纯计算/阻塞请求，建议在线程池运行
                # chunks = await run_in_threadpool(slicer.process_file, md_path)

                chunks = slice_markdown_contract(md_path)

                logger.info(f"✅ 智能切片完成，共切分出 {len(chunks)} 个片段，准备写入数据库...")

                file_slice_contents = [
                    FileSliceRecord(
                        task_id=task.id,
                        source_file_key=task.file_key,
                        slice_index=chunk["slice_index"],
                        content=chunk["content"],
                        content_clean=chunk["content"],
                        content_len=chunk["content_len"]
                    ) for chunk in chunks
                ]
                db.add_all(file_slice_contents)
                await db.commit()
                logger.info(f"✅ 切片记录已成功保存至数据库")
            else:
                logger.info(f"⚡ 数据库中已存在 {len(file_slice_contents)} 个切片记录，跳过切片过程")

            # 6. 执行嵌入任务 (Embedding)
            logger.info("[Step 6] 准备执行 Embedding 向量化和入库")
            pending_slices_result = await db.execute(
                select(FileSliceRecord).where(
                    FileSliceRecord.task_id == task.id,
                    FileSliceRecord.is_embedded == False
                )
            )
            pending_slices = pending_slices_result.scalars().all()

            if pending_slices:
                logger.info(f"🧠 发现 {len(pending_slices)} 个未向量化的切片，准备调用 Embedding 模型...")
                emb_info = await model_service.get_model_invoke_info(model_type=ModelType.EMBEDDING)
                # 使用异步客户端提高 Embedding 效率
                async_client = AsyncOpenAI(api_key=emb_info.api_key, base_url=emb_info.base_url)

                batch_size = 10
                for i in range(0, len(pending_slices), batch_size):
                    batch = pending_slices[i:i + batch_size]
                    vdb_insert_data = []

                    logger.info(f"🔄 正在处理 Embedding 批次: {i + 1} 到 {i + len(batch)} ...")

                    # 也可以进一步使用 asyncio.gather 并发这 10 个 Embedding 请求
                    for slice_item in batch:
                        response = await async_client.embeddings.create(
                            input=slice_item.content_clean,
                            model=emb_info.model_id,
                            encoding_format="float"
                        )
                        vector = response.data[0].embedding

                        vdb_insert_data.append({
                            # 获取 uuid 的 int 值，并与 (2^63 - 1) 进行按位与运算
                            "id": uuid.uuid4().int & ((1 << 63) - 1),
                            "vector": vector,
                            "text": slice_item.content_clean,
                            "meta_data": {
                                "file_key": slice_item.source_file_key,
                                "task_id": slice_item.task_id,
                                "slice_index": slice_item.slice_index,
                                "account_id": task.created_by
                            }
                        })

                    # 批量写入向量库 (若 vdb.upsert 是同步的，需 wrap)
                    logger.info(
                        f"💾 将 {len(vdb_insert_data)} 条向量数据写入 Milvus (集合: {kb_info.collection_name})...")
                    await run_in_threadpool(
                        vdb.upsert,
                        collection_name=kb_info.collection_name,
                        data=vdb_insert_data
                    )

                    # 更新状态
                    slice_ids = [s.id for s in batch]
                    await db.execute(
                        update(FileSliceRecord)
                        .where(FileSliceRecord.id.in_(slice_ids))
                        .values(is_embedded=True)
                    )
                    await db.commit()
                    logger.info(f"✅ 批次 {i + 1}-{i + len(batch)} 向量化及入库完成")
            else:
                logger.info("⚡ 所有切片均已完成 Embedding，跳过向量化步骤")

            # 任务成功结束
            task.analysis_status = AnalysisStatus.FINISH
            file_info.is_resolved = True
            file_info.kb_id = kb_info.id
            await db.commit()
            logger.info(f"🎉 文件解析任务全部顺利完成！[task_id: {task_id}]")

        except Exception as e:
            logger.error(f"❌ 处理任务 {task_id} 发生内部异常: {str(e)}\n{traceback.format_exc()}")
            await db.rollback()
            # 重新获取 task 对象以防 session 失效
            await db.execute(
                update(FileResolveTask)
                .where(FileResolveTask.id == task_id)
                .values(analysis_status=AnalysisStatus.FAILED)
            )
            await db.commit()
            logger.info(f"⚠️ 任务 {task_id} 状态已更新为 FAILED")
