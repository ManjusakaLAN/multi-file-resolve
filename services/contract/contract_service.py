import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from core.config import settings
from core.enum.contract import ReviewStatus
from core.exception.contract import ContractException
from core.infrastructure.storage import MinioClient
from schemas.general import PageResponse
from services.contract.contract_agent_service import ContractAgentService
from services.file.file_service import FileService
from services.llm.model_service import LLMModelService
from util import file_util, ocr_util, slice_util
from models.contract import ContractReviewTask, ContractSliceContent
from util.db_util import paginate

logger = logging.getLogger(__name__)


class ContractService:
    def __init__(self, db: AsyncSession, file_service: FileService,
                 contract_agent_service: ContractAgentService,
                 model_service: LLMModelService,
                 minio_client: MinioClient):
        self.db = db
        self.file_service = file_service
        self.contract_agent_service = contract_agent_service
        self.model_service = model_service
        self.minio_client = minio_client

    async def generate_contract_review_task(self, file: UploadFile, user_id: str) -> ContractReviewTask:
        """
        生成合同审查任务
        :param file:
        :param user_id:
        :return:
        """
        # 上传文件
        file_record = await self.file_service.upload_file(file, user_id)

        # 记录任务
        contract_review_task = ContractReviewTask(
            file_name=file_record.name,
            review_status=ReviewStatus.WAITING_PRE_REVIEW,
            source_file_key=file_record.file_key,
            created_by=user_id
        )
        self.db.add(contract_review_task)
        await self.db.commit()
        await self.db.refresh(contract_review_task)
        base_dir = Path.cwd()
        task_dir = base_dir / "temp" / f"ocr_{contract_review_task.id}"
        task_dir_input = task_dir / "input"
        task_dir_output = task_dir / "output"
        # 递归创建目录
        task_dir_input.mkdir(parents=True, exist_ok=True)
        task_dir_output.mkdir(parents=True, exist_ok=True)

        return contract_review_task

    async def contract_preview(self):
        # 找到第一个这个条件的 md_file_path 为null
        contract_review_task = None
        try:
            stmt = select(ContractReviewTask).where(
                ContractReviewTask.review_status == ReviewStatus.WAITING_PRE_REVIEW
            )
            contract_review_task = (await self.db.execute(stmt)).scalars().first()
            # 没有符合条件的直接结束任务即可
            if contract_review_task is None:
                return

            logger.info(f"开始执行文件{contract_review_task.file_name}的预审查任务")
            contract_review_task.review_status = ReviewStatus.PRE_REVIEW
            await self.db.commit()

            base_dir = Path.cwd()
            task_dir = base_dir / "temp" / f"ocr_{contract_review_task.id}"
            task_dir_input = task_dir / "input"
            task_dir_output = task_dir / "output"

            source_file_path = task_dir_input / contract_review_task.file_name
            # 准确定位生成的 PDF 路径
            pdf_path = task_dir_output / f"{source_file_path.stem}.pdf"
            # 如果是pdf则直接下载到output 用户后续ocr识别即可
            if contract_review_task.file_name.endswith(".pdf"):
                if not pdf_path.exists():
                    await run_in_threadpool(
                        self.minio_client.download,  # 确保你的 minio_client 有此方法
                        object_name=contract_review_task.source_file_key,
                        target_filepath=str(pdf_path)
                    )
            else:
                # 如果源文件没下载，则进行下载
                if not source_file_path.exists():
                    await run_in_threadpool(
                        self.minio_client.download,  # 确保你的 minio_client 有此方法
                        object_name=contract_review_task.source_file_key,
                        target_filepath=str(source_file_path)
                    )
            # 执行文件转换 (LibreOffice -> PDF) 如果没有则进行转换
            if not pdf_path.exists():
                file_util.convert_with_libreoffice(str(source_file_path), str(task_dir_output))

            # 拿到md文件路径
            md_path = contract_review_task.md_file_path
            if md_path is None:
                logger.info(f"开始执行文件{contract_review_task.file_name}的OCR识别任务")
                md_path = await ocr_util.invoke_mineru_to_markdown(
                    file_path=str(pdf_path),
                    save_directory=str(task_dir_output),
                    api_url=settings.MINERU_API_URL
                )
                logger.info(f"文件{contract_review_task.file_name}的OCR识别任务执行完成")
                contract_review_task.md_file_path = md_path
                await self.db.commit()

            # 拿到md文件minio存储路径
            md_key = contract_review_task.md_file_key
            if md_key is None:
                logger.info(f"开始执行文件{contract_review_task.file_name}的md文件上传任务")
                with open(md_path, "rb") as f:
                    # 构造 UploadFile 对象
                    # 注意：FastAPI 的 UploadFile 内部需要一个 file-like 对象
                    file_to_upload = UploadFile(
                        file=f,
                        filename=md_path
                    )
                    md_upload_info = await self.file_service.upload_file(file_to_upload,
                                                                         contract_review_task.created_by)
                logger.info(f"文件{contract_review_task.file_name}的md文件上传任务执行完成")
                contract_review_task.md_file_key = md_upload_info.file_key
                await self.db.commit()

            # 执行文件切片工作 先查询 是否已经切片
            stmt_slice = select(ContractSliceContent).where(
                ContractSliceContent.contract_review_task_id == contract_review_task.id
            )
            contract_slice_contents = (await self.db.execute(stmt_slice)).scalars().all()
            if contract_slice_contents is None or len(contract_slice_contents) == 0:
                logger.info(f"开始执行文件{contract_review_task.file_name}的切片任务")
                chunks = slice_util.slice_markdown_contract(md_path=md_path)
                contract_slice_contents = []
                for i, chunk in enumerate(chunks):
                    contract_slice_content = ContractSliceContent(
                        contract_review_task_id=contract_review_task.id,
                        slice_id=str(i),
                        slice_content=chunk,
                        len=len(chunk),
                        created_by=contract_review_task.created_by
                    )
                    contract_slice_contents.append(contract_slice_content)
                self.db.add_all(contract_slice_contents)
                await self.db.commit()
                logger.info(f"文件{contract_review_task.file_name}的切片任务执行完成")

            # 开始进行预审察任务
            logger.info(f"开始执行文件{contract_review_task.file_name}的预审任务")
            model_invoke_info = await self.model_service.get_model_invoke_info()
            await self.contract_agent_service.contract_judge_agent(model_invoke_info, contract_review_task.id)
            logger.info(f"文件{contract_review_task.file_name}的预审任务执行完成")

        except Exception as e:
            logger.error(f"文件{contract_review_task.file_name}的预审查任务执行失败: {e}")
            if contract_review_task is not None:
                contract_review_task.review_status = ReviewStatus.PRE_REVIEW_FAILED
                contract_review_task.error_message = str(e)
                await self.db.commit()
            return

    async def get_review_task_page_list(self, file_name: str, contract_name: str, review_status: str, page: int,
                                        page_size: int) -> PageResponse:
        """
        分页获取合同审查任务
        :param file_name: 文件名称
        :param contract_name: 合同名称
        :param review_status: 审查状态
        :param page:
        :param page_size:
        :return:
        """
        stmt = select(ContractReviewTask)

        if file_name:
            stmt = stmt.where(ContractReviewTask.file_name.contains(file_name))
        if contract_name:
            stmt = stmt.where(ContractReviewTask.contract_name.contains(contract_name))
        if review_status:
            stmt = stmt.where(ContractReviewTask.review_status == review_status)

        stmt.order_by(ContractReviewTask.created_at.desc())

        return await paginate(self.db, stmt, page, page_size)

    async def retry(self, contract_id) -> ContractReviewTask:
        """
        重试任务
        如果预审查失败 则重新预审查
        如果审查任务失败 则重新审查
        :param contract_id:
        :return:
        """
        stmt = select(ContractReviewTask).where(ContractReviewTask.id == contract_id)
        contract_review_task = (await self.db.execute(stmt)).scalars().first()
        if not contract_review_task:
            raise ContractException("合同不存在")

        review_status = contract_review_task.review_status
        if review_status == ReviewStatus.PRE_REVIEW_FAILED:
            contract_review_task.review_status = ReviewStatus.WAITING_PRE_REVIEW
        elif review_status == ReviewStatus.FAILED:
            contract_review_task.review_status = ReviewStatus.WAITING_REVIEW
        else:
            raise ContractException("未失败的合同审查任务无需重试")
        await self.db.commit()
        await self.db.refresh(contract_review_task)
        return contract_review_task

    async def get_review_task_detail(self, contract_id: str) -> ContractReviewTask:
        """
        获取审查任务详情
        :param contract_id:
        :return:
        """
        stmt = select(ContractReviewTask).where(ContractReviewTask.id == contract_id)
        return (await self.db.execute(stmt)).scalars().first()
