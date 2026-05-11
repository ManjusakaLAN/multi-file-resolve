import os
import io
import zipfile
import asyncio
import httpx
import aiofiles
from pathlib import Path


async def invoke_mineru_to_markdown(file_path: str, save_directory: str, api_url: str) -> str:
    save_path = Path(save_directory)
    # 创建目录是轻量操作，可以直接运行
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
        # 1. 异步读取待上传的文件
        async with aiofiles.open(file_path, 'rb') as f:
            file_content = await f.read()

        # 2. 使用 httpx 发送异步请求
        # 注意：files 的格式与 requests 略有不同
        files = {'files': (os.path.basename(file_path), file_content, 'application/pdf')}

        async with httpx.AsyncClient(timeout=3000.0) as client:
            response = await client.post(api_url, data=payload, files=files)
            response.raise_for_status()
            zip_data = response.content

        # 3. 处理解压逻辑
        # zipfile 模块是同步且耗 CPU 的，我们将其放入线程池中执行，防止阻塞主循环
        def extract_zip(data, target_dir):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for member in z.infolist():
                    if member.is_dir():
                        continue
                    filename = os.path.basename(member.filename)
                    if not filename:
                        continue

                    target_file_path = Path(target_dir) / filename
                    with z.open(member) as source, open(target_file_path, "wb") as target:
                        target.write(source.read())
            return True

        # 利用 asyncio.to_thread 将同步解压任务异步化 (Python 3.9+)
        await asyncio.to_thread(extract_zip, zip_data, save_path)

        # 4. 查找生成的 .md 文件
        md_files = list(save_path.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"未能在目录中找到生成的 .md 文件")

        return str(md_files[0].absolute())

    except httpx.HTTPStatusError as e:
        raise Exception(f"请求失败，状态码: {e.response.status_code}, 详情: {e.response.text}")
    except Exception as e:
        raise Exception(f"OCR 异步处理失败: {str(e)}")