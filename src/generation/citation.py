"""
引用溯源生成模块
"""

import re
from typing import List, Dict
from .llm_client import LLMClient


class CitationGenerator:
    """引用溯源生成器"""

    def __init__(self, llm: LLMClient | None = None):
        """初始化引用生成器"""
        self.llm = llm or LLMClient()

    async def generate(self, answer: Dict, snippets: List[Dict]) -> List[Dict]:
        """
        生成引用

        Args:
            answer: 生成的答案
            snippets: 检索到的文档片段

        Returns:
            引用列表
        """
        answer_content = answer.get("content", "") if isinstance(answer, dict) else str(answer)

        # 提取答案中的引用标记 [1], [2] 等
        citation_pattern = r"\[(\d+)\]"
        citation_matches = re.findall(citation_pattern, answer_content)

        # 构建引用列表（去重）
        citations = []
        seen_indices = set()
        for match in citation_matches:
            idx = int(match) - 1
            if 0 <= idx < len(snippets) and idx not in seen_indices:
                seen_indices.add(idx)
                snippet = snippets[idx]
                content = snippet.get("content", "")

                # 提取有意义的标题
                title = self._extract_title(content, snippet)

                # 提取关键内容片段
                key_content = self._extract_key_content(content)

                citations.append({
                    "marker": f"[{match}]",
                    "title": title,
                    "content": key_content,
                    "source": snippet.get(
                        "source",
                        snippet.get("metadata", {}).get("source", "Textbooks"),
                    ),
                })

        # 如果没有找到引用标记，使用 LLM 分析
        if not citations and snippets:
            citations = await self._analyze_citations(answer_content, snippets)

        return citations

    async def _analyze_citations(self, answer: str, snippets: List[Dict]) -> List[Dict]:
        """使用 LLM 分析引用"""
        prompt = f"""分析以下答案，找出它引用了哪些参考资料。

答案：
{answer}

参考资料：
{self._format_snippets(snippets)}

请列出答案中引用的资料编号，格式如：[1], [2]"""

        response = await self.llm.generate(prompt)

        # 解析引用
        citation_matches = re.findall(r"\[(\d+)\]", response)

        citations = []
        seen_indices = set()
        for match in citation_matches:
            idx = int(match) - 1
            if 0 <= idx < len(snippets) and idx not in seen_indices:
                seen_indices.add(idx)
                snippet = snippets[idx]
                content = snippet.get("content", "")
                title = self._extract_title(content, snippet)
                key_content = self._extract_key_content(content)
                citations.append({
                    "marker": f"[{match}]",
                    "title": title,
                    "content": key_content,
                    "source": snippet.get("source", snippet.get("metadata", {}).get("source", "Textbooks")),
                })

        return citations

    def _format_snippets(self, snippets: List[Dict]) -> str:
        """格式化检索结果"""
        return "\n\n".join([
            f"[{i+1}] {s.get('title', '无标题')}\n{s.get('content', '')[:300]}"
            for i, s in enumerate(snippets[:10])
        ])

    def _extract_title(self, content: str, snippet: Dict) -> str:
        """从内容中提取有意义的标题"""
        # 首先尝试从 source 生成书名
        source = snippet.get("source", "")
        if not source:
            source = snippet.get("metadata", {}).get("source", "")

        if source:
            # 移除文件扩展名
            source_clean = source.replace(".jsonl", "")

            # 格式化英文书名（将下划线替换为空格，首字母大写）
            formatted_name = source_clean.replace("_", " ").title()

            # 映射为完整的英文书名
            book_names = {
                "Internalmed Harrison": "Harrison's Principles of Internal Medicine",
                "Surgery Schwartz": "Schwartz's Principles of Surgery",
                "Pathology Robbins": "Robbins Pathologic Basis of Disease",
                "Pharmacology Katzung": "Katzung's Basic & Clinical Pharmacology",
                "Physiology Levy": "Levy's Physiology",
                "Biochemistry Lippincott": "Lippincott's Illustrated Reviews: Biochemistry",
                "Anatomy Gray": "Gray's Anatomy",
                "Neurology Adams": "Adams and Victor's Principles of Neurology",
                "Pediatrics Nelson": "Nelson Textbook of Pediatrics",
                "Gynecology Novak": "Novak's Gynecology",
                "Immunology Janeway": "Janeway's Immunobiology",
                "Cell Biology Alberts": "Molecular Biology of the Cell (Alberts)",
                "First Aid Step1": "First Aid for the USMLE Step 1",
                "First Aid Step2": "First Aid for the USMLE Step 2 CK",
                "Pathoma Husain": "Pathoma: Fundamentals of Pathology",
                "Psichiatry Dsm-5": "DSM-5: Diagnostic and Statistical Manual of Mental Disorders",
            }

            # 尝试匹配书名
            for key, full_name in book_names.items():
                if key.lower() in source_clean.lower():
                    return full_name

            # 如果没有匹配，返回格式化的名称
            return formatted_name

        # 如果没有 source，尝试从 content 提取标题
        if content:
            lines = content.split("\n")
            for line in lines[:5]:
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                if line[0].isdigit() and len(line) < 30:
                    continue
                # 返回第一行有意义的内容
                return line[:80]

        # 使用 snippet 中的 title
        title = snippet.get("title", "")
        if title and len(title) > 5:
            title = title.strip().replace("_", " ").title()
            if len(title) > 80:
                title = title[:80] + "..."
            return title

        return "Medical Literature"

    def _extract_key_content(self, content: str) -> str:
        """提取关键内容片段"""
        if not content:
            return "无内容"

        # 移除多余空白
        content = " ".join(content.split())

        # 提取前200个字符
        if len(content) > 200:
            # 尝试在句号处截断
            truncated = content[:200]
            last_period = truncated.rfind("。")
            if last_period > 100:
                return truncated[:last_period + 1] + "..."
            return truncated + "..."

        return content
