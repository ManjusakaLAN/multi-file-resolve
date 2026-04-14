import logging
from typing import Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.dict import Dict as DictModel
from schemas.general import PageResponse
from util.db_util import paginate  # 假设你的分页工具在此路径

logger = logging.getLogger(__name__)


class DictService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def page_list_dict(
            self,
            dict_code: Optional[str],
            label: Optional[str],
            value: Optional[str],
            is_system: Optional[int],
            page: int = 1,
            page_size: int = 10
    ) -> PageResponse:
        """
        分页条件查询 dict
        """
        stmt = select(DictModel)

        # 动态构建过滤条件
        filters = []
        if dict_code:
            filters.append(DictModel.dict_code == dict_code)
        if label:
            filters.append(DictModel.label.contains(label))
        if value:
            filters.append(DictModel.value.contains(value))
        if is_system:
            filters.append(DictModel.is_system == is_system)

        if filters:
            stmt = stmt.where(and_(*filters))

        # 排序：先按 code 组聚合，再按 sort 排序
        stmt = stmt.order_by(DictModel.dict_code.asc(), DictModel.sort.asc())
        return await paginate(self.db, stmt, page, page_size)

    async def get_dict_by_id(self, dict_id: int) -> DictModel:
        """
        内部辅助方法：根据ID获取字典模型
        """
        stmt = select(DictModel).where(DictModel.id == dict_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="字典项不存在")
        return item

    async def create_dict(
            self,
            dict_code: str,
            label: str,
            value: str,
            sort: int = 0,
            is_system: int = 0
    ) -> DictModel:
        """
        创建 dict
        """
        # 校验同一个 dict_code 下 value 是否重复
        stmt = select(DictModel).where(
            and_(DictModel.dict_code == dict_code, DictModel.value == value)
        )
        existing = await self.db.execute(stmt)
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"该编码下已存在值为 '{value}' 的选项")

        new_dict = DictModel(
            dict_code=dict_code,
            label=label,
            value=value,
            sort=sort,
            is_system=is_system
        )

        self.db.add(new_dict)
        try:
            await self.db.commit()
            await self.db.refresh(new_dict)
            return new_dict
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建字典失败: {e}")
            raise HTTPException(status_code=500, detail="数据库写入失败")

    async def update_dict(
            self,
            dict_id: int,  # 建议变量名改为 dict_id 以免与内置 id 冲突
            dict_code: str,
            label: str,
            value: str,
            sort: int = 0,
            is_system: int = 0
    ) -> DictModel:
        """
        更新 dict，包含系统项保护和唯一性检查
        """
        # 1. 获取目标记录
        dict_item = await self.get_dict_by_id(dict_id)

        # 2. 系统内置项保护逻辑
        if dict_item.is_system == 1:
            if dict_item.dict_code != dict_code or dict_item.value != value:
                raise HTTPException(status_code=403, detail="系统内置项禁止修改编码或键值")

        # 3. 唯一性校验：检查是否存在 ID 不同但 code + value 相同的其他记录
        # 只有当 dict_code 或 value 发生变化时才有必要查重，但为了代码简洁，通常统一检查
        exist_stmt = select(DictModel).where(
            and_(
                DictModel.dict_code == dict_code,
                DictModel.value == value,
                DictModel.id != dict_id  # 关键点：排除掉自己
            )
        )
        existing_res = await self.db.execute(exist_stmt)
        if existing_res.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"更新失败：字典编码 '{dict_code}' 下已存在值为 '{value}' 的项"
            )

        # 4. 执行更新赋值
        dict_item.dict_code = dict_code
        dict_item.label = label
        dict_item.value = value
        dict_item.sort = sort
        dict_item.is_system = is_system

        # 5. 提交事务
        try:
            await self.db.commit()
            await self.db.refresh(dict_item)
            return dict_item
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新字典失败: {e}")
            # 处理可能的并发或数据库级唯一索引冲突
            if "Duplicate entry" in str(e):
                raise HTTPException(status_code=400, detail="数据冲突：该字典编码与键值已存在")
            raise HTTPException(status_code=500, detail="数据库更新失败")

    async def delete_dict(self, dict_id: str) -> bool:
        """
        删除 dict 如果是系统内置 则不允许删除此dict
        """
        dict_item = await self.get_dict_by_id(dict_id)

        # 拦截系统项
        if dict_item.is_system == 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="系统内置字典项，禁止删除"
            )

        try:
            await self.db.delete(dict_item)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除字典失败: {e}")
            raise HTTPException(status_code=500, detail="数据库删除失败")

    async def list_dict(self, dict_code: str, label: str, value: str, is_system: str):
        """
        查询所有字典信息
        :param dict_code:
        :param label:
        :param value:
        :param is_system:
        :return:
        """
        stmt = select(DictModel)

        # 动态构建过滤条件
        filters = []
        if dict_code:
            filters.append(DictModel.dict_code == dict_code)
        if label:
            filters.append(DictModel.label.contains(label))
        if value:
            filters.append(DictModel.value.contains(value))
        if is_system:
            filters.append(DictModel.is_system == is_system)

        if filters:
            stmt = stmt.where(and_(*filters))

        # 排序：先按 code 组聚合，再按 sort 排序
        stmt = stmt.order_by(DictModel.dict_code.asc(), DictModel.sort.asc())
        results = await self.db.execute(stmt)
        return results.scalars()