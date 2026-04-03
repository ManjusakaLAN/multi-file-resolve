from datetime import datetime
from typing import Annotated
from pydantic import PlainSerializer

from core.config import settings

# 定义一个格式化后的日期类型
# 定义带时区转换的格式化类型
CustomDatetime = Annotated[
    datetime,
    PlainSerializer(
        lambda x: x.astimezone(settings.tz_info).strftime('%Y-%m-%d %H:%M:%S'),
        return_type=str
    )
]