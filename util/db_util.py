from sqlalchemy import select, func

from schemas.general import PageResponse


async def paginate(session, stmt, page, page_size) -> PageResponse:
    # 1. 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # 2. 执行分页查询
    list_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(list_stmt)

    # 3. 智能解析结果
    # 如果 select 的只有一列，用 scalars；如果是多列，保留整行
    if len(stmt.column_descriptions) > 1:
        raw_items = result.all()
        # 对于 (KnowledgeBase, is_favorite) 这种模式进行自动合并
        processed_items = []
        for row in raw_items:
            obj = row[0]
            # 将后续列的值动态赋给第一个对象
            for i, col in enumerate(stmt.column_descriptions[1:], start=1):
                setattr(obj, col['name'], row[i])
            processed_items.append(obj)
        data = processed_items
    else:
        data = result.scalars().all()

    return PageResponse(
        total=total,
        data=data,
        page=page,
        page_size=page_size
    )