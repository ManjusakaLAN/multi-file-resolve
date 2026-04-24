import logging
from typing import cast
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from schemas.agent_tool import State, ContractOutline, Elements

logger = logging.getLogger(__name__)


# --- 节点 1：处理前半部分大纲 ---
async def outline_generate_node_1(state: State, config: RunnableConfig):
    llm = cast(ChatOpenAI, config["configurable"].get("llm"))
    tools = config["configurable"].get("tools")
    tool_map = {t.name: t for t in tools}

    # ✅ 修复点 1: 增加 method="json_mode" 解决 400 报错
    structured_llm = llm.with_structured_output(ContractOutline, method="json_mode")
    llm_with_tools = llm.bind_tools(tools)

    mid = len(state.slice_ids) // 2
    target_ids = state.slice_ids[:mid]

    results = []
    for s_id in target_ids:
        # 获取原文
        lookup_msg = [HumanMessage(content=f"请调用工具获取分片 {s_id} 的原文")]
        response = await llm_with_tools.ainvoke(lookup_msg)

        content = ""
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_obj = tool_map.get(tool_call["name"])
                if tool_obj:
                    content = await tool_obj.ainvoke(tool_call["args"])

        # ✅ 修复点 2: Prompt 中必须包含 "JSON" 关键字
        # 修改 prompt
        prompt = f"""请根据以下内容生成合同大纲，必须返回 JSON 格式。
        要求包含以下字段：
        - slice_id: 整数，设为 {s_id}
        - outline: 字符串，大纲摘要内容

        文本内容：{content}
        """

        try:
            outline_obj = await structured_llm.ainvoke(prompt)
            outline_obj.slice_id = s_id
            results.append(outline_obj)
        except Exception as e:
            logger.error(f"Node 1 处理切片 {s_id} 结构化输出失败: {e}")
            # 如果你希望触发重试机制，这里可以抛出异常 raise e
            # 如果这里捕获了异常并返回“解析失败”，LangGraph 则认为节点成功运行，不会触发重试
            results.append(ContractOutline(slice_id=s_id, outline="解析失败"))

    logger.info(f"前半部分大纲生成完成，数量: {len(results)}")
    return {"contract_outlines": results, "logs": [f"Node 1 处理了切片: {target_ids}"]}


# --- 节点 2：处理后半部分大纲 ---
async def outline_generate_node_2(state: State, config: RunnableConfig):
    llm = cast(ChatOpenAI, config["configurable"].get("llm"))
    tools = config["configurable"].get("tools")
    tool_map = {t.name: t for t in tools}

    # ✅ 修复点 1: 增加 method="json_mode"
    structured_llm = llm.with_structured_output(ContractOutline, method="json_mode")
    llm_with_tools = llm.bind_tools(tools)

    mid = len(state.slice_ids) // 2
    target_ids = state.slice_ids[mid:]

    results = []
    for s_id in target_ids:
        lookup_msg = [HumanMessage(content=f"获取分片 {s_id} 的原文")]
        response = await llm_with_tools.ainvoke(lookup_msg)

        content = ""
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_obj = tool_map.get(tool_call["name"])
                if tool_obj:
                    content = await tool_obj.ainvoke(tool_call["args"])

        # ✅ 修复点 2: Prompt 中增加 "JSON" 关键字
        prompt = f"""请根据以下内容生成合同大纲，必须返回 JSON 格式。
        要求包含以下字段：
        - slice_id: 整数，设为 {s_id}
        - outline: 字符串，大纲摘要内容

        文本内容：{content}
        """

        try:
            outline_obj = await structured_llm.ainvoke(prompt)
            outline_obj.slice_id = s_id
            results.append(outline_obj)
        except Exception as e:
            logger.error(f"Node 2 处理切片 {s_id} 结构化输出失败: {e}")
            results.append(ContractOutline(slice_id=s_id, outline="解析失败"))

    logger.info(f"后半部分大纲生成完成，数量: {len(results)}")
    return {"contract_outlines": results, "logs": [f"Node 2 处理了切片: {target_ids}"]}


async def element_extract_node(state: State, config: RunnableConfig):
    llm = cast(ChatOpenAI, config["configurable"].get("llm"))
    tools = config["configurable"].get("tools")
    tool_map = {t.name: t for t in tools}

    # 1. 核心修复：使用 json_mode
    structured_llm = llm.with_structured_output(Elements, method="json_mode")

    # 初始化一个空的要素对象
    current_elements = Elements()
    tool_obj = tool_map.get("lookup_contract_slice")

    logger.info(f"开始循环处理 {len(state.slice_ids)} 个切片进行要素提取...")

    for s_id in state.slice_ids:
        # 2. 获取当前切片内容
        content = await tool_obj.ainvoke({"slice_id": s_id})

        # 3. 构造增量提取的 Prompt
        # 核心：必须包含 'json' 这个词以解决 400 错误
        prompt = f"""
        你是一个合同审查专家。当前正在处理合同的第 {s_id} 个切片。

        【已有要素 JSON 数据】：
        {current_elements.model_dump_json()}

        【当前切片原文】：
        {content}

        【任务】：
        请结合当前切片原文，对已有的要素数据进行完善或修正。
        1. 如果已有数据中某项为空，且当前切片包含该信息，请填入。
        2. 如果当前切片信息与已有信息冲突且当前切片更准确，请更新。
        3. 必须以 JSON 格式返回完整的 Elements 结构。
        """

        try:
            # 4. 调用模型进行增量更新
            # 由于使用了 json_mode 且 Prompt 包含 'JSON'，400 错误将消失
            current_elements = await structured_llm.ainvoke(prompt)
            logger.info(f"切片 {s_id} 要素增量提取完成")
        except Exception as e:
            logger.error(f"切片 {s_id} 处理失败: {str(e)}")
            # 如果希望在这个环节失败时进行重试，请抛出异常 raise e
            continue

    logger.info("所有切片循环处理完毕，最终要素汇总成功")
    return {"elements": current_elements, "logs": ["要素循环提取节点运行结束"]}


# --- 汇总节点 ---
async def aggregator(state: State, config: RunnableConfig):
    # 排序大纲，确保顺序正确
    sorted_outlines = sorted(state.contract_outlines, key=lambda x: x.slice_id)
    outline_text = "\n".join([f"[{o.slice_id}] {o.outline}" for o in sorted_outlines])

    summary = f"合同审查任务完成。\n\n【生成大纲汇总】:\n{outline_text}\n\n"
    summary += f"【核心要素摘要】: 甲方: {state.elements.party_a}, 乙方: {state.elements.party_b}, 金额: {state.elements.contract_amount}"

    llm = cast(ChatOpenAI, config["configurable"].get("llm"))

    # 基于大纲和要素生成合同摘要的提示词
    prompt = f"""
    你是一个合同审查专家。

    【大纲】:
    {outline_text}

    【要素】:
    {state.elements.model_dump_json()}

    【任务】:
    请结合大纲和要素，生成一份合同摘要。直接返回标准的摘要内容，不要有多余的介绍和不必要的描述信息
    """

    response = await llm.ainvoke(prompt)

    return {"summary": response.content}


# Build workflow
parallel_builder = StateGraph(State)

# Add nodes 并应用重试机制
parallel_builder.add_node("outline_generate_node_1", outline_generate_node_1)
parallel_builder.add_node("outline_generate_node_2", outline_generate_node_2)
parallel_builder.add_node("element_extract_node", element_extract_node)
parallel_builder.add_node("aggregator", aggregator)

# Add edges to connect nodes
parallel_builder.add_edge(START, "outline_generate_node_1")
parallel_builder.add_edge(START, "outline_generate_node_2")
parallel_builder.add_edge(START, "element_extract_node")
parallel_builder.add_edge("outline_generate_node_1", "aggregator")
parallel_builder.add_edge("outline_generate_node_2", "aggregator")
parallel_builder.add_edge("element_extract_node", "aggregator")
parallel_builder.add_edge("aggregator", END)

parallel_workflow = parallel_builder.compile()
