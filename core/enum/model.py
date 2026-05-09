from enum import StrEnum


class ModelConfigType(StrEnum):
    SYSTEM = "system"
    CUSTOM = "custom"

    @classmethod
    def get_desc(cls, model_config_type):
        mapping = {
            cls.SYSTEM: "系统内置",
            cls.CUSTOM: "用户自定义"
        }
        return mapping.get(model_config_type, "未知类型")


class ModelProvider(StrEnum):
    # 国际主流
    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    GOOGLE = "Google"
    META = "Meta"
    MISTRAL = "Mistral"

    # 国内主流
    DEEPSEEK = "DeepSeek"
    ALICLOUD = "AliCloud"  # 通义千问 Qwen
    BAIDU = "Baidu"  # 文心一言 Ernie
    TENCENT = "Tencent"  # 混元 HunYuan
    ZHIPU = "Zhipu"  # 智谱清言 ChatGLM
    MOONSHOT = "Moonshot"  # Kimi

    # 特殊类型
    LOCAL_CUSTOM = "LocalCustom"  # 自定义或本地部署 (如 Ollama, LocalAI, vLLM)

    @classmethod
    def get_desc(cls, provider):
        mapping = {
            cls.OPENAI: "OpenAI (GPT系列)",
            cls.ANTHROPIC: "Anthropic (Claude系列)",
            cls.GOOGLE: "Google (Gemini系列)",
            cls.META: "Meta (Llama系列)",
            cls.MISTRAL: "Mistral AI",
            cls.DEEPSEEK: "DeepSeek (深度求索)",
            cls.ALICLOUD: "阿里云 (通义千问)",
            cls.BAIDU: "百度 (文心一言)",
            cls.TENCENT: "腾讯 (混元)",
            cls.ZHIPU: "智谱清言 (GLM)",
            cls.MOONSHOT: "月之暗面 (Kimi)",
            cls.LOCAL_CUSTOM: "本地部署或自定义中转"
        }
        return mapping.get(provider, "未知供应商")

class ModelType(StrEnum):
    """AI 技术架构维度的模型类型枚举"""
    LLM = "llm"  # 语言模型 (大文本生成、推理)
    EMBEDDING = "embedding"  # 向量模型 (文本转向量)
    RERANK = "rerank"  # 重排序模型 (精排)
    VISION = "vision"  # 多模态/视觉模型

    @classmethod
    def get_desc(cls, model_type):
        mapping = {
            cls.LLM: "大语言模型",
            cls.EMBEDDING: "向量嵌入模型",
            cls.RERANK: "重排序模型",
            cls.VISION: "视觉多模态模型"
        }
        return mapping.get(model_type, "未知能力类型")
