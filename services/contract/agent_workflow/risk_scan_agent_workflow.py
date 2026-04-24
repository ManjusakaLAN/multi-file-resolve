import json
import logging
from typing import cast, List
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph

from langchain_openai import ChatOpenAI
from schemas.agent_tool import RiskScanState,RiskScanResult

logger = logging.getLogger(__name__)


async def risk_scan_node_1(state: RiskScanState, config: RunnableConfig):
    llm = cast(ChatOpenAI, config["configurable"].get("llm"))
    tools = config["configurable"].get("tools")
    tool_map = {t.name: t for t in tools}

    # 1. 准备两个版本的 LLM
    # 一个用于执行工具反查（带工具绑定）
    llm_with_tools = llm.bind_tools(tools)
    # 一个用于最终的结构化风险提取（JSON 模式）
    # 注意：使用我们之前定义的 ContractRisks 包装类，包含 List[RiskCreate]
    structured_llm = llm.with_structured_output(RiskScanResult, method="json_mode")

    mid = len(state.slice_ids)
    target_ids = state.slice_ids[:mid]

    # 将大纲转为字符串上下文
    outlines_info = state.outlines

    final_scan_results = []

    for s_id in target_ids:
        # --- 第一阶段：内容收集与潜在反查 ---
        # 初始上下文包含该切片内容和大纲
        lookup_msg = [
            HumanMessage(content=f"""你正在进行风险扫描。
            当前切片 ID: {s_id}
            全文大纲参考: {outlines_info} 每部分大纲有吧对应切片的id提供，后续反查请使用这个id

            请先调用工具获取切片 {s_id} 的原文。
            在阅读原文后，如果发现涉及其他条款或需要核实大纲中的信息，你可以继续调用工具进行反查。
            如果信息已足够，请直接回答“信息已就绪”。""")
        ]

        # 模拟 ReAct 循环，最多允许 3 次反查以防死循环
        collected_content = ""
        for _ in range(3):
            response = await llm_with_tools.ainvoke(lookup_msg)
            if not response.tool_calls:
                break

            lookup_msg.append(response)
            for tool_call in response.tool_calls:
                target_tool = tool_map.get(tool_call["name"])
                if target_tool:
                    tool_output = await target_tool.ainvoke(tool_call["args"])
                    lookup_msg.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))
                    collected_content += f"\n--- 工具反查结果 ---\n{tool_output}"
        # --- 第二阶段：结构化风险提取 ---
        prompt = f"""你是一个资深的法务专家。请根据以下收集到的合同内容进行风险扫描。

        【待扫描内容】：
        {collected_content}

        【任务】：
        识别潜在的法律和商业风险点。必须以 JSON 格式返回。

        【JSON 结构要求】：
        请返回一个对象，包含 "risks" 列表字段，列表中的每个项包含以下字段：
        - risk_level: 风险等级（high高、medium中、low低）
        - associated_clause: 关联条款名称/章节号
        - original_excerpt: 合同原文摘录
        - risk_description: 风险详细说明
        - potential_impact: 潜在法律或经济影响
        - modification_suggestion: 针对性的修改建议
        - slice_id: 固定填写为 "{s_id}"
        """

        try:
            # 使用包装类 ContractRisks 提取列表
            extracted_data = await structured_llm.ainvoke(prompt)
            if extracted_data and extracted_data.risks:
                # 强制修正 slice_id 并合并
                for r in extracted_data.risks:
                    r.slice_id = str(s_id)
                final_scan_results.extend(extracted_data.risks)
        except Exception as e:
            logger.error(f"Node 1 在处理切片 {s_id} 提取风险时报错: {e}")

    logger.info(f"风险扫描完成，识别到风险点: {len(final_scan_results)}")
    print(final_scan_results)
    # json 格式化输出
    # 返回 State 更新，注意字段名要对应你的 RiskScanState
    return {
        "scan_risks": final_scan_results,
        "logs": [f"扫描了切片: {target_ids}，发现 {len(final_scan_results)} 个风险"]
    }


# --- 汇总节点 ---
async def aggregator(state: RiskScanState, config: RunnableConfig):


    llm = cast(ChatOpenAI, config["configurable"].get("llm"))
    print("state: ", state)

    return {}


# Build workflow
parallel_builder = StateGraph(RiskScanState)

# Add nodes
parallel_builder.add_node("risk_scan_node_1", risk_scan_node_1)
parallel_builder.add_node("aggregator", aggregator)

# Add edges to connect nodes
parallel_builder.add_edge(START, "risk_scan_node_1")
parallel_builder.add_edge("risk_scan_node_1", "aggregator")
parallel_builder.add_edge("aggregator", END)

risk_scan_workflow = parallel_builder.compile()
