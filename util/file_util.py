import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader


def get_pdf_page_count(file_path: str) -> int:
    """
    传入 PDF 文件路径，返回文件的页数。

    :param file_path: PDF 文件的完整路径
    :return: 文件的页数 (int)。如果文件不存在或解析失败，返回 0 (或按需返回 None)
    """
    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 -> {file_path}")
        return 0

    # 2. 检查文件后缀是否为 pdf
    if not file_path.lower().endswith('.pdf'):
        print(f"警告: 该文件不是以 .pdf 结尾 -> {file_path}")
        # 视业务需求决定是否 return 0 拦截，这里直接尝试读取

    try:
        # 3. 读取 PDF 并获取页数
        # PdfReader 内部处理了文件流的打开和关闭，直接传路径即可
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
        return page_count

    except Exception as e:
        print(f"解析 PDF 文件失败: {file_path}")
        print(f"错误信息: {e}")
        return 0

def convert_with_libreoffice(input_file, output_dir):
    """
    使用开源技术libreoffice 将多种文件转换为pdf 便于后续的识别工作
    :param input_file:
    :param output_dir:
    :return:
    """
    # 1. 修正后缀列表：去掉 '*'，只保留纯后缀字符串
    # 建议统一使用小写，方便后续比对
    valid_extensions = ('.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')

    # 2. 获取输入文件的小写后缀进行比对
    # os.path.splitext 会返回 (文件名, 后缀名)
    _, file_ext = os.path.splitext(input_file)

    if file_ext.lower() not in valid_extensions:
        raise ValueError(f"不支持的文件格式: {file_ext}。目前仅支持: {', '.join(valid_extensions)}")

    command = [
        'libreoffice',
        '--headless',
        '--convert-to',
        'pdf',
        '--outdir',
        output_dir,
        input_file
    ]

    try:
        # 提取文件名用于美化打印日志
        filename = os.path.basename(input_file)
        print(f"正在转换: {filename} ...")

        # 运行转换命令
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"  └── 成功！")
    except subprocess.CalledProcessError as e:
        print(f"  └── 转换失败: {input_file}")
        print(f"      错误信息: {e.stderr.decode('utf-8', errors='ignore')}")


async def get_file_md5(file: UploadFile) -> str:
    """
    获取文件md5 (分块读取，防止大文件撑爆内存)
    :param file: FastAPI 的 UploadFile 对象
    :return: 文件的 MD5 字符串 (32位小写)
    """
    md5_hash = hashlib.md5()
    # 定义分块大小，通常 8KB (8192 bytes) 或 64KB 是比较好的平衡点
    chunk_size = 8192

    # 1. 确保指针在文件开头 (防止在此之前文件被读取过)
    await file.seek(0)

    # 2. 分块读取并更新 MD5
    while chunk := await file.read(chunk_size):
        md5_hash.update(chunk)

    # 3. ！！！极其重要！！！
    # 算完 MD5 后，文件指针已经到了末尾。
    # 必须把指针重新移回开头，否则后续保存文件时会保存一个空文件。
    await file.seek(0)

    # 返回 32 位小写的十六进制字符串
    return md5_hash.hexdigest()

def storage_file(file: UploadFile, path: Path) -> str:
    """
    存储文件到本地目录 返回存储后的路径
    :param file: FastAPI 上传的文件对象
    :param path: 目标存储目录（文件夹路径）
    :return: 存储后的完整绝对路径字符串
    """
    # 1. 确保目标目录存在（如果不存在则递归创建）
    path.mkdir(parents=True, exist_ok=True)

    # 2. 构造完整的保存路径（目录 + 原始文件名）
    # 注意：如果文件名可能重复，建议在此处加上 UUID 或时间戳
    save_path = path / file.filename

    # 3. 极其重要：复位文件指针
    # 防止在调用此方法前读取过 MD5 或文件内容，导致磁头停留在末尾
    file.file.seek(0)

    # 4. 执行流式拷贝
    # 使用 'wb' 模式打开目标文件，将上传的临时文件流拷贝进去
    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. 返回绝对路径的字符串形式
    return str(save_path.absolute())