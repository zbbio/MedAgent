"""
索引构建模块
用于构建向量索引
"""

import os
import json
from typing import List, Dict
from ..config import config
from ..retrieval.vector_store import ChromaVectorStore


class IndexBuilder:
    """索引构建器"""

    def __init__(self):
        """初始化索引构建器"""
        self.vector_store = ChromaVectorStore()

    def build_from_directory(self, data_dir: str):
        """
        从目录构建索引

        Args:
            data_dir: 数据目录路径
        """
        print(f"开始从 {data_dir} 构建索引...")

        documents = []

        # 遍历目录中的所有 JSONL 文件
        for root, dirs, files in os.walk(data_dir):
            for fname in files:
                if not fname.endswith(".jsonl"):
                    continue

                fpath = os.path.join(root, fname)
                print(f"处理文件: {fname}")

                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                doc = json.loads(line)
                                documents.append({
                                    "id": doc.get("id", f"{fname}_{len(documents)}"),
                                    "content": doc.get("content", ""),
                                    "metadata": {
                                        "title": doc.get("title", ""),
                                        "source": fname,
                                    },
                                })
                except Exception as e:
                    print(f"处理文件 {fname} 失败: {e}")
                    continue

        if documents:
            print(f"共加载 {len(documents)} 个文档，开始向量化...")
            self.vector_store.add_documents(documents)
            print("索引构建完成！")
        else:
            print("未找到任何文档")

    def build_from_jsonl(self, jsonl_path: str):
        """
        从单个 JSONL 文件构建索引

        Args:
            jsonl_path: JSONL 文件路径
        """
        print(f"开始从 {jsonl_path} 构建索引...")

        documents = []

        try:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        documents.append({
                            "id": doc.get("id", f"doc_{len(documents)}"),
                            "content": doc.get("content", ""),
                            "metadata": {
                                "title": doc.get("title", ""),
                                "source": os.path.basename(jsonl_path),
                            },
                        })
        except Exception as e:
            print(f"处理文件失败: {e}")
            return

        if documents:
            print(f"共加载 {len(documents)} 个文档，开始向量化...")
            self.vector_store.add_documents(documents)
            print("索引构建完成！")
        else:
            print("未找到任何文档")

    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            "total_documents": self.vector_store.count(),
        }


if __name__ == "__main__":
    # 命令行运行
    import sys

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
        builder = IndexBuilder()
        builder.build_from_directory(data_dir)
        print("统计信息:", builder.get_stats())
    else:
        print("用法: python -m src.indexing.index_builder <数据目录>")
