import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.enum.kb import KBType, AuditStatus, AnalysisStatus
from core.exception.llm_exception import KBException
from core.infrastructure.storage import MinioClient
from core.infrastructure.vector_db import MilvusVectorDB
from models.file import FileRecord
from models.knowledge import FileResolveTask, KnowledgeBase
from services.file.file_service import FileService
from services.kb.folder_service import FolderService
from services.llm.model_service import ModelService
from tasks.file_resolve_task import file_resolve_task
from util import db_util

logger = logging.getLogger(__name__)


async def execute_file_resolve_task(task_id: str):
    logger.info(f"开始执行文件处理任务{task_id}")
    file_resolve_task.delay(task_id)


class TaskService:
    def __init__(self, db: AsyncSession, minio_client: MinioClient, file_service: FileService, vdb: MilvusVectorDB,
                 model_service: ModelService, folder_service: FolderService):
        self.db = db
        self.vdb = vdb
        self.minio_client = minio_client
        self.file_service = file_service
        self.model_service = model_service
        self.folder_service = folder_service

    async def generate_task(self, file_keys: list[str], kb_id: str, user_id: str, task_type: str,
                            folder_id: str | None = None):
        tasks = []

        kb_info = (await self.db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id,
                                                                     KnowledgeBase.is_deleted == False))).scalars().first()
        if not kb_info:
            raise KBException(message="知识库不存在或已删除")

        audit_flag = True
        audit_status = AuditStatus.UNREVIEWED

        # 个人知识库不需要审核
        if kb_info.kb_type == KBType.PERSONAL:
            audit_flag = False
            audit_status = AuditStatus.NO_NEED_REVIEWED

        for file_key in file_keys:

            file_info = (
                await self.db.execute(select(FileRecord).where(FileRecord.file_key == file_key))).scalars().first()
            if not file_info:
                continue

            await self.folder_service.move_file_to_folder(file_id=file_info.id, target_folder_id=folder_id)

            tasks.append(FileResolveTask(
                file_key=file_key,
                kb_id=kb_id,
                created_by=user_id,
                audit_status=audit_status,
                file_name=file_info.name
            ))

        self.db.add_all(tasks)
        await self.db.commit()
        await self.db.flush()

        if audit_flag:
            logger.info(f"任务生成完成,数量{len(tasks)}，请进行审核工作")
            return "任务生成完成，请进行审核工作"

        # 提取 ID 列表
        task_ids = [task.id for task in tasks]

        logger.info(f"文件处理中，数量{len(tasks)}，请耐心等待")

        for task_id in task_ids:
            await execute_file_resolve_task(task_id)
        return "文件处理中，请耐心等待"

    async def retry_task(self, task_id: str):
        # 判断是否有这个任务
        task = (await self.db.execute(select(FileResolveTask).where(FileResolveTask.id == task_id))).scalars().first()
        if not task:
            raise KBException(message="任务不存在")
        if task.analysis_status != AnalysisStatus.FAILED:
            raise KBException(message="任务状态不是失败,暂时无需重试")

        await execute_file_resolve_task(task_id)
        return "任务已重试,请耐心等待"

    async def task_page_list(self, file_name: str, audit_status: AuditStatus | str,
                             analysis_status: AnalysisStatus | str, page: int = 1, page_size: int = 10):
        """
        审核任务分页查询
        :param analysis_status:
        :param file_name:
        :param audit_status:
        :param page:
        :param page_size:
        :return:
        """
        stmt = select(FileResolveTask)

        if file_name:
            stmt = stmt.where(FileResolveTask.file_name.like(f"%{file_name}%"))

        if audit_status:
            stmt = stmt.where(FileResolveTask.audit_status == audit_status)

        if analysis_status:
            stmt = stmt.where(FileResolveTask.analysis_status == analysis_status)

        # 按照时间降序
        stmt = stmt.order_by(FileResolveTask.created_at.desc())
        return await db_util.paginate(self.db, stmt, page, page_size)

    async def check_task(self, task_id: str, audit_status: AuditStatus | str, audit_opinion: str):
        """
        任务审核
        :param task_id:
        :param audit_status:
        :param audit_opinion:
        :return:
        """
        task = (await self.db.execute(select(FileResolveTask).where(FileResolveTask.id == task_id))).scalars().first()
        if not task:
            raise KBException(message="任务不存在")
        if task.audit_status != AuditStatus.UNREVIEWED:
            raise KBException(message="任务状态不是待审核")

        task.audit_status = audit_status
        task.audit_opinion = audit_opinion

        await self.db.commit()
        if audit_status == AuditStatus.PASS:
            # 审核通过的执行解析任务
            await execute_file_resolve_task(task_id)

        return "任务审核完成"
