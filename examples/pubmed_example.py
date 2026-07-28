"""
PubMed 检索功能使用示例
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval.pubmed_retriever import PubMedRetriever, search_pubmed
from src.retrieval.hybrid import HybridRetriever


def example_basic_search():
    """示例 1：基本 PubMed 搜索"""
    print("=" * 60)
    print("示例 1：基本 PubMed 搜索")
    print("=" * 60)

    query = "diabetes treatment"
    print(f"查询: {query}")

    # 使用便捷函数
    results = search_pubmed(query, max_results=5)

    print(f"\n找到 {len(results)} 篇相关论文:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   PMID: {result['metadata']['pmid']}")
        print(f"   期刊: {result['metadata']['journal']}")
        print(f"   发表日期: {result['metadata']['pub_date']}")
        print(f"   链接: {result['metadata']['url']}")

    print()


def example_advanced_search():
    """示例 2：高级 PubMed 搜索"""
    print("=" * 60)
    print("示例 2：高级 PubMed 搜索")
    print("=" * 60)

    # 创建检索器实例
    retriever = PubMedRetriever()

    # 高级查询语法
    queries = [
        "diabetes[Title/Abstract] AND treatment[Title/Abstract]",
        "hypertension[MeSH Terms] AND complications[MeSH Terms]",
        "cancer[Title] AND immunotherapy[Title] AND 2024[pdat]",
    ]

    for query in queries:
        print(f"\n查询: {query}")
        results = retriever.search(query, max_results=3)
        print(f"找到 {len(results)} 篇论文")

        if results:
            print(f"  第一篇: {results[0]['title'][:60]}...")

    print()


def example_hybrid_search():
    """示例 3：混合检索（BM25 + PubMed + 向量）"""
    print("=" * 60)
    print("示例 3：混合检索")
    print("=" * 60)

    # 创建混合检索器
    retriever = HybridRetriever()

    query = "糖尿病视网膜病变如何治疗？"
    print(f"查询: {query}")

    # 执行混合检索
    results = retriever.retrieve(query, k=10)

    print(f"\n混合检索返回 {len(results)} 条结果:")

    # 按来源分组统计
    source_counts = {}
    for result in results:
        source = result.get('source', 'Unknown')
        source_counts[source] = source_counts.get(source, 0) + 1

    print("\n来源统计:")
    for source, count in source_counts.items():
        print(f"  {source}: {count} 篇")

    print("\n前 5 条结果:")
    for i, result in enumerate(results[:5], 1):
        source = result.get('source', 'Unknown')
        title = result.get('title', 'No title')[:60]
        print(f"  {i}. [{source}] {title}...")

    print()


def example_integrate_with_agent():
    """示例 4：集成到 Agent"""
    print("=" * 60)
    print("示例 4：集成到 Agent")
    print("=" * 60)

    # 模拟 Agent 使用 PubMed 检索
    from src.agent.core import MedAgent

    agent = MedAgent()

    question = "高血压的并发症有哪些？"
    print(f"问题: {question}")

    # Agent 会自动使用混合检索（包含 PubMed）
    result = agent.answer(question)

    print(f"\n回答:")
    print(result['answer'][:200] + "..." if len(result['answer']) > 200 else result['answer'])

    print(f"\n检索来源:")
    source_counts = {}
    for snippet in result.get('snippets', []):
        source = snippet.get('source', 'Unknown')
        source_counts[source] = source_counts.get(source, 0) + 1

    for source, count in source_counts.items():
        print(f"  {source}: {count} 篇")

    print()


if __name__ == "__main__":
    # 运行所有示例
    example_basic_search()
    example_advanced_search()
    example_hybrid_search()
    # example_integrate_with_agent()  # 需要 OpenAI API Key

    print("=" * 60)
    print("所有示例运行完成")
    print("=" * 60)
