import os
import subprocess
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