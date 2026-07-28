"""
查询理解与重写模块
"""

from typing import List, Dict
from ..generation.llm_client import LLMClient


class QueryUnderstander:
    """查询理解与重写"""

    def __init__(self, llm: LLMClient | None = None):
        """初始化查询理解器"""
        self.llm = llm or LLMClient()

    async def understand(self, question: str, history: List[Dict]) -> Dict:
        """
        理解用户查询

        Args:
            question: 用户问题
            history: 历史对话

        Returns:
            理解结果字典
        """
        history_text = self._format_history(history)

        prompt = f"""分析以下医学问题，提取关键信息。

历史对话：
{history_text}

当前问题：{question}

请输出 JSON 格式：
{{
    "original_query": "原始问题",
    "rewritten_query": "英文检索查询（用于搜索英文医学文献，使用英文关键词）",
    "intent": "诊断/治疗/用药/检查/预后/病因/病理",
    "key_entities": ["关键实体1", "关键实体2"],
    "complexity": "简单/中等/复杂",
    "needs_retrieval": true/false,
    "reasoning": "判断理由"
}}

判断规则（必须严格遵守）：

【设置 needs_retrieval: true 的情况】（必须检索）
1. 具体患者病例问题：包含"患者"、"XX岁"、具体症状或检查结果
   例如："患者男性，70岁，血压180/110，如何用药？"
2. 诊断标准问题：包含"诊断标准"、"诊断依据"、"如何诊断"
   例如："糖尿病酮症酸中毒的诊断标准是什么？"
3. 治疗方案问题：包含"如何治疗"、"治疗方案"、"用药方案"
   例如："心肌梗死的治疗流程是什么？"
4. 药物使用问题：包含"剂量"、"用法"、"药物选择"、"用药"
   例如："华法林的剂量是多少？"
5. 鉴别诊断问题：包含"鉴别诊断"、"如何区分"、"区别"
   例如："心源性哮喘和支气管哮喘如何鉴别？"
6. 发病机制问题：包含"发病机制"、"病理生理"、"病因"
   例如："糖尿病的发病机制是什么？"

【设置 needs_retrieval: false 的情况】（不检索）
1. 非常简单的常识问题：答案是普遍认可的健康常识
   例如："多喝水对身体好吗？"、"感冒了应该多休息吗？"
2. 简单的定义问题：答案是简单的概念解释
   例如："什么是高血压？"
3. 一般性健康建议：不涉及具体医学细节
   例如："如何预防感冒？"

rewritten_query 必须是英文，用于搜索英文医学文献

示例：
- 问题："高血压并发症有哪些？"
  needs_retrieval: true
  rewritten_query: "hypertension complications"
- 问题："患者男性，70岁，血压180/110，合并肾功能不全，如何用药？"
  needs_retrieval: true
  rewritten_query: "hypertension renal impairment drug treatment elderly"
- 问题："糖尿病酮症酸中毒的诊断标准是什么？"
  needs_retrieval: true
  rewritten_query: "diabetic ketoacidosis diagnosis criteria DKA"
- 问题："多喝水对身体好吗？"
  needs_retrieval: false
  rewritten_query: "water intake health benefits"
"""

        result = await self.llm.generate_json(prompt)

        # 确保返回必要字段
        return {
            "original_query": question,
            "rewritten_query": result.get("rewritten_query", question),
            "intent": result.get("intent", "未知"),
            "key_entities": result.get("key_entities", []),
            "complexity": result.get("complexity", "中等"),
            "needs_retrieval": result.get("needs_retrieval", True),
            "reasoning": result.get("reasoning", ""),
        }

    def _format_history(self, history: List[Dict]) -> str:
        """格式化历史对话"""
        if not history:
            return "无"

        return "\n".join([
            f"{'用户' if h['role'] == 'user' else '助手'}: {h['content']}"
            for h in history[-5:]
        ])
