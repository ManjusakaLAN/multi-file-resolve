from sqlalchemy import select, func


async def paginate(session, stmt, page, page_size):
    # 1. 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # 2. 执行分页查询
    list_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = (await session.execute(list_stmt)).scalars().all()

    return items, total