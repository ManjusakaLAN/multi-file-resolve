import re
import json
import requests
import time
import os
from typing import List, Dict


class LLMSmartSlicer:
    def __init__(
            self,
            api_key: str,
            base_url: str = "https://api.deepseek.com",
            model_name: str = "deepseek-chat",  # 建议使用通用的对话模型名
            max_chunk_size: int = 1000,
            overlap_size: int = 200,  # 前后语义重叠长度
            min_chunk_size: int = 400
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.max_size = max_chunk_size
        self.overlap = overlap_size
        self.min_size = min_chunk_size

    def _ask_llm(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system",
                 "content": "你是一个高精度的文本处理助手，擅长分析文档结构和语义断点。你必须严格返回 JSON。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        try:
            url = f"{self.base_url}/chat/completions"
            response = requests.post(url, json=data, headers=headers, timeout=45)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"API调用异常: {e}")
        return ""

    def _get_semantic_split_point(self, context: str) -> int:
        """
        利用 LLM 在指定的缓冲区内寻找最佳语义断点
        """
        # 截取 buffer 的中间到末尾区域寻找断点
        search_area = context[self.min_size: self.max_size + 100]

        prompt = f"""
        任务：在待分析文本中寻找一个最适合断句的位置。
        要求：
        1. 优先在段落末尾（\n\n）或句子结束处（。！？）。
        2. 绝对不要截断代码块、表格或数学公式。
        3. 返回该位置最后 8 个字符。

        待分析文本：
        \"\"\"{search_area}\"\"\"

        请以 JSON 格式回复：
        {{"cut_marker": "最后8个字符内容", "reason": "理由"}}
        """

        res_raw = self._ask_llm(prompt)
        try:
            res_data = json.loads(res_raw)
            marker = res_data.get("cut_marker", "")
            idx = search_area.rfind(marker)
            if idx != -1:
                return self.min_size + idx + len(marker)
        except:
            pass

        # 兜底：如果 LLM 失败，尝试正则找最后一个句号
        last_period = re.search(r'[。！？\n](?=[^。！？\n]*$)', search_area)
        if last_period:
            return self.min_size + last_period.end()

        return self.max_size

    def process_file(self, file_path: str) -> List[Dict]:
        if not os.path.exists(file_path):
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. 结构化初步切分：识别 Markdown 标题
        # 将文档切分为若干块，但保留标题信息
        parts = re.split(r'(^#+ .*)', content, flags=re.MULTILINE)

        raw_blocks = []
        for i in range(0, len(parts), 2):
            # 合并标题和紧随其后的内容
            block = parts[i]
            if i + 1 < len(parts):
                block += parts[i + 1]
            if block.strip():
                raw_blocks.append(block)

        final_chunks = []
        current_buffer = ""
        chunk_id = 1

        for block in raw_blocks:
            # 如果当前 block 加上 buffer 没超过最大限制，先存入 buffer
            if len(current_buffer) + len(block) <= self.max_size:
                current_buffer += block
            else:
                # 如果超了，需要对当前 buffer 进行语义切分
                while len(current_buffer) + len(block) > self.max_size:
                    # 如果 buffer 本身就很短（小于最小值），直接把新 block 塞进去再切
                    if len(current_buffer) < self.min_size:
                        current_buffer += block
                        block = ""  # 已消耗

                    split_pos = self._get_semantic_split_point(current_buffer)

                    chunk_text = current_buffer[:split_pos].strip()
                    if chunk_text:
                        final_chunks.append({
                            "slice_index": chunk_id,
                            "content": chunk_text,
                            "content_len": len(chunk_text)
                        })
                        chunk_id += 1

                    # --- 核心：重叠窗口处理 ---
                    # 移动 buffer 指针，保留 overlap 部分以维持语义连贯
                    new_start = max(0, split_pos - self.overlap)
                    current_buffer = current_buffer[new_start:].strip()

                    # 避免陷入死循环：如果 buffer 没变长，强制跳出
                    if len(current_buffer) >= self.max_size and split_pos <= self.overlap:
                        current_buffer = current_buffer[split_pos:]

                    # 如果 block 还没处理完，且当前 buffer 已经清空/缩短到合理范围
                    if len(current_buffer) < self.max_size:
                        break

                current_buffer += block

        # 处理剩余尾部
        if current_buffer.strip():
            final_chunks.append({
                "slice_index": chunk_id,
                "content": current_buffer.strip(),
                "content_len": len(current_buffer.strip())
            })

        return final_chunks


from typing import List, Dict, Any
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def slice_markdown_contract(
        md_path: str,
        chunk_min_size: int = 200,
        chunk_target_size: int = 400,
        chunk_max_size: int = 600
) -> List[Dict[str, Any]]:
    """
    精细化合同切片：
    按 [200, 600] 字符长度进行切分，返回带索引和长度的数据结构。
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 结构化初步切分 (捕捉 H1-H4)
    headers_to_split_on = [
        ("#", "H1"),
        ("##", "H2"),
        ("###", "H3"),
        ("####", "H4"),
    ]
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    initial_sections = header_splitter.split_text(content)

    # 2. 对超长语义段落进行二次降级切分
    refined_texts = []
    sub_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_max_size,
        chunk_overlap=50,
        separators=["\n\n", "\n", "；", "。", " "]
    )

    for sec in initial_sections:
        if len(sec.page_content) > chunk_max_size:
            refined_texts.extend(sub_splitter.split_text(sec.page_content))
        else:
            refined_texts.append(sec.page_content)

    # 3. 贪婪合并与结构化输出
    final_chunks = []
    current_buffer = ""
    chunk_id = 0

    def add_to_result(text: str):
        nonlocal chunk_id
        text_content = text.strip()
        if text_content:
            final_chunks.append({
                "slice_index": chunk_id,
                "content": text_content,
                "content_len": len(text_content)
            })
            chunk_id += 1

    for text in refined_texts:
        text = text.strip()
        if not text:
            continue

        # 逻辑：如果当前缓冲区 + 新文本超过上限，先存掉当前的
        if current_buffer and (len(current_buffer) + len(text) > chunk_max_size):
            add_to_result(current_buffer)
            current_buffer = text
        elif current_buffer:
            current_buffer += "\n\n" + text
        else:
            current_buffer = text

        # 如果缓冲区已经达到了目标理想大小，直接封包，保证切片精细度
        if len(current_buffer) >= chunk_target_size:
            add_to_result(current_buffer)
            current_buffer = ""

    # 4. 尾部处理
    if current_buffer:
        # 兜底逻辑：如果最后一段太短，且前面有块，尝试合并到前一块
        if final_chunks and len(current_buffer) < chunk_min_size:
            last_chunk = final_chunks[-1]
            if len(last_chunk["content"]) + len(current_buffer) <= chunk_max_size:
                last_chunk["content"] += "\n\n" + current_buffer
                last_chunk["content_len"] = len(last_chunk["content"])
            else:
                add_to_result(current_buffer)
        else:
            add_to_result(current_buffer)

    return final_chunks
