import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from chromadb import PersistentClient
from openai import OpenAI


class VectorMemory:
    def __init__(
        self,
        collection_name: str = "shell_assistant",
        persist_dir: str = "~/.shell_assistant/vector_db",
    ):
        """初始化向量记忆系统"""
        # 使用持久化存储
        persist_path = os.path.expanduser(persist_dir)

        # 创建 ChromaDB 客户端
        self.client = PersistentClient(path=persist_path)

        try:
            self.client.delete_collection(name=collection_name)
            print("[INFO]已删除旧collection,重建新维度")
        except:
            pass

        # 获取或创建 collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
        )

        # 检查是否需要迁移数据（从旧格式迁移）
        self._migrate_if_needed()

    def _migrate_if_needed(self):
        """迁移旧格式数据"""
        # 检查是否已存在数据
        docs = self.collection.get()
        if not docs["documents"]:
            return

        # 检查第一条记录的格式
        first_doc = docs["documents"][0]
        if isinstance(first_doc, str) and first_doc.startswith("{"):
            # 旧格式（JSON字符串），需要迁移
            print("[Info] Migrating old memory format...")
            new_docs = []
            new_metadatas = []
            new_ids = []

            for i, doc in enumerate(docs["documents"]):
                content = json.loads(doc)
                meta = docs["metadatas"][i]
                new_docs.append(content)
                new_metadatas.append(meta)
                new_ids.append(docs["ids"][i])

            # 清空原有数据
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.create_collection(
                name=self.collection.name, metadata={"hnsw:space": "cosine"}
            )

            # 重新添加数据
            self.collection.add(
                documents=new_docs, metadatas=new_metadatas, ids=new_ids
            )
            print("[Info] Migration completed")

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的嵌入向量（使用 OpenRouter 的 embeddings API）"""
        import os

        from openai import OpenAI

        api_key = os.getenv("DASHSCOPE_API_KEY")  # 复用你的 OpenRouter key
        if not api_key:
            raise Exception("DASHSCOPE_API_KEY 未设置，请检查环境变量")

        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        try:
            response = client.embeddings.create(
                model="baai/bge-m3",  # 可改成想用的模型
                input=text,
                encoding_format="float",  # 默认返回 float 向量
            )
            # 返回第一个（也是唯一一个）embedding
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"OpenRouter embedding failed: {str(e)}")

    def store_memory(
        self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储单条记忆到向量数据库"""
        # 生成唯一ID
        memory_id = str(uuid.uuid4())

        # 准备元数据
        meta = {
            "role": role,
            "timestamp": datetime.now().isoformat(),
            "type": "text",  # 默认类型
            **(metadata or {}),
        }

        # 获取嵌入向量
        embedding = self._get_embedding(content)

        # 存储到 ChromaDB
        self.collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta],
            ids=[memory_id],
        )

        return memory_id

    def store_code_memory(
        self,
        role: str,
        content: str,
        file_path: str,
        language: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """存储代码相关的记忆（特殊处理）"""
        # 为代码添加特殊标记
        code_marker = f"\n\n# [{language.upper()}] CODE MEMORY: {file_path}\n"

        # 组合内容
        full_content = f"{content}{code_marker}"

        # 扩展元数据
        meta = {
            "role": role,
            "timestamp": datetime.now().isoformat(),
            "type": "code",
            "file_path": file_path,
            "language": language,
            **(metadata or {}),
        }

        # 获取嵌入向量
        embedding = self._get_embedding(full_content)

        # 存储到 ChromaDB
        memory_id = str(uuid.uuid4())
        self.collection.add(
            embeddings=[embedding],
            documents=[full_content],
            metadatas=[meta],
            ids=[memory_id],
        )

        return memory_id

    def search_relevant_memories(
        self,
        query: str,
        top_k: int = 3,
        filter_role: Optional[str] = None,
        filter_type: Optional[str] = None,
    ) -> List[Dict]:
        """搜索与查询最相关的记忆"""
        # 获取查询向量
        query_embedding = self._get_embedding(query)

        # 构建查询条件
        where_clause = {}
        if filter_role:
            where_clause["role"] = filter_role
        if filter_type:
            where_clause["type"] = filter_type

        # 执行查询
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        # 格式化结果
        memories = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append(
                    {
                        "content": doc,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "relevance_score": 1
                        - results["distances"][0][i],  # 余弦相似度越小越相关
                    }
                )

        return memories

    def get_recent_memories(
        self,
        limit: int = 10,
        filter_role: Optional[str] = None,
        filter_type: Optional[str] = None,
    ) -> List[Dict]:
        """获取最近的历史记录（按时间）"""
        # ChromaDB 本身不支持按时间排序，需要手动处理
        all_docs = self.collection.get(include=["documents", "metadatas"])

        # 过滤和排序
        filtered = []
        for i, doc in enumerate(all_docs["documents"]):
            meta = all_docs["metadatas"][i]

            # 过滤条件
            if filter_role and meta.get("role") != filter_role:
                continue
            if filter_type and meta.get("type") != filter_type:
                continue

            filtered.append(
                {
                    "content": doc,
                    "metadata": meta,
                    "timestamp": meta.get("timestamp", ""),
                }
            )

        # 按时间戳排序（最新的在前）
        sorted_memories = sorted(filtered, key=lambda x: x["timestamp"], reverse=True)

        return sorted_memories[:limit]

    def clear_memory(self):
        """清空所有记忆"""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name, metadata={"hnsw:space": "cosine"}
        )
        print("[Info] All memories cleared")

    def get_memory_stats(self) -> Dict:
        """获取记忆库统计信息"""
        docs = self.collection.get()
        stats = {
            "total_memories": len(docs["documents"]),
            "memories_by_role": {},
            "memories_by_type": {},
        }

        for meta in docs["metadatas"]:
            role = meta.get("role", "unknown")
            mem_type = meta.get("type", "unknown")

            stats["memories_by_role"][role] = stats["memories_by_role"].get(role, 0) + 1
            stats["memories_by_type"][mem_type] = (
                stats["memories_by_type"].get(mem_type, 0) + 1
            )

        return stats
