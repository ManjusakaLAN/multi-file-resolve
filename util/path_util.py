from pathlib import Path


def get_workspace_path() -> Path:
    """
    获取项目的workspace路径
    处理临时文件 以及 存放结果文件
    :return:
    """
    return Path.cwd() / "workspace"

def file_exists(file_path: str) -> bool:
    """
    判断文件是否存在
    :param file_path:
    :return:
    """
    return Path(file_path).exists()