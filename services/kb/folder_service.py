import logging
from typing import List, Optional, Dict
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.middleware_exception import DBException
from models.file import FileRecord
from models.knowledge import Folder

logger = logging.getLogger(__name__)


class FolderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_kb_folder(self, kb_id: str, name: str, parent_id: Optional[str] = None,
                               user_id: Optional[str] = None):
        """
        创建知识库目录
        :param kb_id:
        :param name:
        :param parent_id:
        :param user_id:
        :return:
        """
        try:
            new_folder = Folder(
                name=name,
                kb_id=kb_id,
                parent_id=parent_id,
                created_by=user_id
            )
            self.db.add(new_folder)
            await self.db.commit()
            await self.db.refresh(new_folder)
        except Exception as e:
            logger.error(f"创建目录异常: {e}")
            raise DBException(message="文件创建失败")
        return new_folder

    async def tree_list_folder(self, kb_id: str):
        """
        树形展示所有目录信息（不含文件）
        """
        # 一次性查出该知识库下所有文件夹
        stmt = select(Folder).where(Folder.kb_id == kb_id)
        result = await self.db.execute(stmt)
        all_folders = result.scalars().all()

        return self._build_tree(all_folders, None)

    async def tree_list_folder_and_file(self, kb_id: str):
        """
        树形展示目录及其下的文件
        """
        # 预加载 files 关联
        stmt = (
            select(Folder)
            .where(Folder.kb_id == kb_id)
            .options(selectinload(Folder.files))
        )
        result = await self.db.execute(stmt)
        all_folders = result.scalars().all()

        # 还要获取根目录下的文件 (folder_id 为空的文件)
        stmt_root_files = select(FileRecord).where(
            and_(FileRecord.kb_id == kb_id, FileRecord.folder_id == None, FileRecord.is_resolved == True)
        )
        root_files_result = await self.db.execute(stmt_root_files)
        root_files = root_files_result.scalars().all()

        tree = self._build_tree(all_folders, None, include_files=True)

        # 将根目录文件放入返回结构的顶层
        return {
            "folders": tree,
            "root_files": [self._file_to_dict(f) for f in root_files]
        }

    async def delete_folder(self, folder_id: str, recursive: bool = False):
        """
        删除目录
        1. 允许递归删除 (recursive=True)
        2. 若 recursive=False 且目录下有文件或子目录，不允许删除
        """
        stmt = select(Folder).where(Folder.id == folder_id).options(
            selectinload(Folder.files),
            selectinload(Folder.children)
        )
        result = await self.db.execute(stmt)
        folder = result.scalar_one_or_none()

        if not folder:
            return False, "目录不存在"

        # 检查目录下是否有文件
        if folder.files:
            return False, "目录下存有文件，不允许删除"

        if not recursive:
            if folder.children:
                return False, "目录下存有子目录，请先清空或选择递归删除"
            await self.db.delete(folder)
        else:
            # SQLAlchemy 配置了 cascade="all, delete-orphan" 会自动递归删除子目录
            # 但由于我们要检查“所有”子目录下是否有文件，建议先手动校验或捕获异常
            await self.db.delete(folder)

        await self.db.commit()
        return True, "删除成功"

    async def move_file_to_folder(self, file_id: str, target_folder_id: Optional[str]):
        """
        移动文件到指定目录 (target_folder_id 为 None 则移到根目录)
        """
        stmt = update(FileRecord).where(FileRecord.id == file_id).values(folder_id=target_folder_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    # --- 内部辅助方法 ---

    def _build_tree(self, folders: List[Folder], parent_id: Optional[str], include_files: bool = False) -> List[Dict]:
        """
        递归构建树结构
        """
        tree = []
        for f in folders:
            if f.parent_id == parent_id:
                node = {
                    "id": f.id,
                    "name": f.name,
                    "children": self._build_tree(folders, f.id, include_files)
                }
                if include_files:
                    node["files"] = [
                        self._file_to_dict(file)
                        for file in f.files
                        if file.is_resolved
                    ]
                tree.append(node)
        return tree

    def _file_to_dict(self, file: FileRecord):
        return {
            "id": file.id,
            "name": file.name,
            "extension": file.extension,
            "file_key": file.file_key
        }

    async def update_kb_folder(self, folder_id: str, name: str):
        """
        修改目录名称
        :param folder_id:
        :param name:
        :return:
        """
        stmt = update(Folder).where(Folder.id == folder_id)
        await self.db.execute(stmt.values(name=name))
        await self.db.commit()
