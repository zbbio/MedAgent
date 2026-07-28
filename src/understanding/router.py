"""
自适应路由决策模块
"""

from typing import Dict
from ..generation.llm_client import LLMClient


class AdaptiveRouter:
    """自适应路由决策"""

    def __init__(self, llm: LLMClient | None = None):
        """初始化路由决策器"""
        self.llm = llm or LLMClient()

    def route(self, understanding: Dict) -> str:
        """
        根据查询理解结果决定路由

        Args:
            understanding: 查询理解结果

        Returns:
            路由类型：direct_generation, single_retrieval, multi_hop_retrieval
        """
        # 规则1：如果不需要检索，直接生成
        if not understanding.get("needs_retrieval", True):
            return "direct_generation"

        # 规则2：根据复杂度决定
        complexity = understanding.get("complexity", "中等")

        if complexity == "简单":
            return "single_retrieval"
        elif complexity == "复杂":
            # 复杂问题需要多轮检索
            return "multi_hop_retrieval"
        else:
            # 中等问题，先尝试单次检索
            return "single_retrieval"

    async def route_with_llm(self, understanding: Dict) -> str:
        """
        使用 LLM 进行更精细的路由（可选）

        Args:
            understanding: 查询理解结果

        Returns:
            路由类型
        """
        prompt = f"""根据以下查询分析，决定检索策略。

查询分析：
- 意图：{understanding.get('intent', '未知')}
- 复杂度：{understanding.get('complexity', '中等')}
- 关键实体：{understanding.get('key_entities', [])}
- 是否需要检索：{understanding.get('needs_retrieval', True)}

可能的策略：
1. direct_generation - 不需要检索，直接回答
2. single_retrieval - 单次检索即可
3. multi_hop_retrieval - 需要多轮检索

请选择最合适的策略，只返回策略名称："""

        response = (await self.llm.generate(prompt)).strip()

        if "direct" in response.lower():
            return "direct_generation"
        elif "multi" in response.lower():
            return "multi_hop_retrieval"
        else:
            return "single_retrieval"
