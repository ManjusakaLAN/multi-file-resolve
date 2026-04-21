from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from typing import List


def slice_markdown_contract(
        md_path: str,
        chunk_target_size: int = 3000,  # 增大目标大小
        chunk_max_size: int = 4000  # 增大上限
) -> List[str]:
    """
    粗放式合同切片：
    以“章”为核心单位，尽可能保持条款的连续性。
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 仅按一级和二级标题切分 (如：# 第一节, ## 1. 一般约定)
    # 这样 H3 (### 1.1.1) 就会被包含在 H2 中，不会被切断
    headers_to_split_on = [
        ("#", "H1"),
        ("##", "H2"),
    ]
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    sections = header_splitter.split_text(content)

    # 2. 贪婪合并：将过小的 Section 合并到一起
    combined_chunks = []
    current_chunk = ""

    for sec in sections:
        text = sec.page_content.strip()
        if not text:
            continue

        # 如果当前累加的内容 + 新内容 < 目标大小，就持续累加
        if len(current_chunk) + len(text) < chunk_target_size:
            current_chunk += "\n\n" + text if current_chunk else text
        else:
            # 达到阈值，存入当前块
            if current_chunk:
                combined_chunks.append(current_chunk)
            current_chunk = text

    if current_chunk:
        combined_chunks.append(current_chunk)

    # 3. 极长块兜底（例如附件里的超大表格）
    # 只有当合并后的块依然超过 max_size，才使用递归切分
    final_output = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_max_size,
        chunk_overlap=200,
        separators=["\n\n", "\n", "。"]
    )

    for chunk in combined_chunks:
        if len(chunk) > chunk_max_size:
            # 对于超长块（如附件表格），进行物理切分
            final_output.extend(text_splitter.split_text(chunk))
        else:
            final_output.append(chunk)

    return final_output
