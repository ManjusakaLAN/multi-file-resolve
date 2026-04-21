import io
import os
import zipfile
from pathlib import Path

import requests


async def invoke_mineru_to_markdown(file_path: str, save_directory: str, api_url: str) -> str:
    save_path = Path(save_directory)
    save_path.mkdir(parents=True, exist_ok=True)

    payload = {
        'return_md': 'true',
        'response_format_zip': 'true',
        'return_middle_json': 'false',
        'return_model_output': 'false',
        'return_content_list': 'false',
        'return_images': 'false'
    }

    try:
        with open(file_path, 'rb') as f:
            files = [('files', (os.path.basename(file_path), f, 'application/pdf'))]
            response = requests.post(api_url, data=payload, files=files, timeout=3000)

        response.raise_for_status()

        # 4. 解压并去除多余目录
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            for member in z.infolist():
                # 跳过文件夹条目
                if member.is_dir():
                    continue

                # 获取纯文件名 (filename.md)，去掉前面的路径 (a/b/c/)
                filename = os.path.basename(member.filename)
                if not filename:
                    continue

                # 构建目标存放路径：直接放在 save_directory 下
                target_path = save_path / filename

                # 执行解压写入
                with z.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())

        # 5. 返回路径
        md_files = list(save_path.glob("*.md"))  # 注意这里改成了 glob，因为就在当前层
        if not md_files:
            raise FileNotFoundError(f"未能在目录中找到生成的 .md 文件")

        return str(md_files[0].absolute())

    except Exception as e:
        raise Exception(f"OCR 处理失败: {str(e)}")
