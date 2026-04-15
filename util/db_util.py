from sqlalchemy import select, func

from schemas.general import PageResponse


async def paginate(session, stmt, page, page_size) -> PageResponse:
    """
    分页查询 工具类
    :param session:
    :param stmt:
    :param page:
    :param page_size:
    :return:
    """
    # 1. 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # 2. 执行分页查询
    list_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    results = (await session.execute(list_stmt)).scalars().all()

    return PageResponse(
        total=total,
        data=results,
        page=page,
        page_size=page_size
    )

