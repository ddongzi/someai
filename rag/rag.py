import logging
import os
from langchain.tools import tool
from pymilvus import MilvusClient, DataType,AnnSearchRequest, RRFRanker
from FlagEmbedding import BGEM3FlagModel
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter

from tools import web_search

from logger import run_logger

URI = "./knowledge.db"

class KnowledgeManager:
    def __init__(self, uri: str = URI):
        self.collection_name = "demo_collection"
        self.client = None
        self.embedding = None
        self.dimension = (1024, 768)
        
        try:
            # 1. 明确使用 BGE-M3 (稠密向量维度 1024)
            self.embedding = BGEM3FlagModel(
                './models/bge-m3',  
                use_fp16=True
            ) # Setting use_fp16 to True speeds up computation with a slight performance degradation

            # 2. 初始化官方原生的 MilvusClient
            self.client = MilvusClient(uri=uri)
            
            # 3. 显式调用初始化，确保集合存在且结构正确
            self.init_milvus()
            
            run_logger.info("✅ Milvus 知识库已成功初始化")
        except Exception as e:
            run_logger.warning(f"⚠️  Milvus 初始化失败: {e}")
            run_logger.warning("   知识库搜索功能将不可用，但不影响其他功能")

        self.md_text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ])
        self.rec_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, 
        )
    def init_milvus(self):
        """完全使用原生 API 精准控制 Schema 和索引，保证不卡死"""
        if not self.client:
            run_logger.warning("Milvus 不可用，跳过初始化")
            return
        if self.client.has_collection(collection_name=self.collection_name):
            self.client.drop_collection(collection_name=self.collection_name)

        if not self.client.has_collection(collection_name=self.collection_name):
            run_logger.info(f"正在创建集合: {self.collection_name} ...")
            
            # 1. 创建 Schema
            schema = self.client.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
            # 稠密向量需要 dim
            schema.add_field(field_name="dense_vec", datatype=DataType.FLOAT_VECTOR, dim=self.dimension[0])
            # ⚠️ 修复：稀疏向量移除了 dim 参数，Milvus 规范要求此处不填维度
            schema.add_field(field_name="sparse_vec", datatype=DataType.SPARSE_FLOAT_VECTOR)
            schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
            schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=255)
            schema.add_field(field_name="type", datatype=DataType.VARCHAR, max_length=255)
            
            # 2. 配置索引参数
            index_params = self.client.prepare_index_params()
            
            # 稠密向量索引
            index_params.add_index(
                field_name="dense_vec",
                index_type="FLAT",  # Milvus Lite 环境下默认使用 FLAT 即可
                metric_type="COSINE"
            )
            # ⚠️ 修复：稀疏向量的 index_type 必须是 SPARSE_INVERTED_INDEX 或 SPARSE_WAND
            index_params.add_index(
                field_name="sparse_vec",
                index_type="SPARSE_INVERTED_INDEX", 
                metric_type="COSINE"
            )
            
            # 3. 创建并加载集合
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params
            )
            run_logger.info("集合创建并加载完成。")
            
        self.client.load_collection(collection_name=self.collection_name)


    def search_hybrid(self, query: str, k: int = 5):
        """只进行混合搜索"""
        if not self.client or not self.embedding:
            run_logger.warning(f"Milvus 不可用，无法搜索: {query}")
            return []
            
        try:
            # 1. 同时生成查询词的 稠密 和 稀疏 向量
            vec = self.embedding.encode(query, return_dense=True, return_sparse=True)
            dense_vec = vec['dense_vecs'].tolist()
            sparse_vec = vec["lexical_weights"]
            
            # 2. 构建稠密向量（语义）检索请求
            req_dense = AnnSearchRequest(
                data=[dense_vec], 
                anns_field="dense_vec", 
                param={"metric_type": "COSINE"}, 
                limit=k * 2  # 放大召回范围供后续融合
            )
            
            # 3. 构建稀疏向量（关键词/Header）检索请求
            req_sparse = AnnSearchRequest(
                data=[sparse_vec], 
                anns_field="sparse_vec", 
                param={"metric_type": "IP"}, 
                limit=k * 2
            )
            
            # 4. 执行混合搜索
            search_results = self.client.hybrid_search(
                collection_name=self.collection_name,
                reqs=[req_dense, req_sparse],
                ranker=RRFRanker(),  # 使用 RRF 倒数排名融合算法进行硬匹配和语义的平衡
                limit=k,
            )
            results = []

            # 外层循环：遍历每个查询词的检索结果（如果是单句查询，search_results 长度通常为 1）
            for hits in search_results:
                # 内层循环：遍历当前查询词召回的 Top-K 条相似数据段
                for hit in hits:
                    # 1. 核心提取：直接获取 entity 字典
                    entity = hit.get("entity", {})

                    # 2. 提取你绝对需要的核心文本
                    text = entity.get("text", "")
                    
                    # 3. 动态提取 Markdown 专属的 Headers（自动处理 Header1, Header2 等不存在的情况）
                    # MarkdownHeaderTextSplitter 默认生成的键名为 Header1, Header2 ...
                    headers = []
                    for i in range(1, 4):  # 遍历支持到五级标题
                        h_val = entity.get(f"Header {i}")# 兼容大小写
                        if h_val:
                            headers.append(h_val)
                            
                    # 将标题用 " > " 拼接，形成类似：指南 > 3.2 向量检索 > 配置说明
                    full_header = " > ".join(headers) if headers else "未分类章节"
                    
                    # 4. 提取其他固定字段
                    source = entity.get("source", "未知来源")
                    doc_type = entity.get("type", "未知类型")
                    
                    # 5. 组装成你需要的干净格式
                    results.append({
                        "text": text,
                        "header": full_header,
                        "source": source,
                        "type": doc_type,
                    })

            return results
        except Exception as e:
            run_logger.error(f"搜索失败: {e}")
            return []


    def add_text(self, text:str, source:str, type:str):
        """
        source: 来源url, file path
        type: local, web, ..
        """ 
        if  not self.client or not self.embedding:
            run_logger.warning(f"Milvus 不可用，无法添加文本: {source}")
            return
            
        try:
            run_logger.info(f'add text !{source}, {type}')
            md_chunks = self.md_text_splitter.split_text(text=text)
            
            # 组装符合 MilvusClient 格式的字典列表
            data_to_insert = []
            for chunk in md_chunks:
                vec = self.embedding.encode(chunk.page_content, return_dense=True, return_sparse=True)
                dense_vec = vec['dense_vecs'].tolist()
                data_to_insert.append({
                    "dense_vec": dense_vec,
                    'sparse_vec':vec["lexical_weights"],
                    "text": chunk.page_content,
                    'source':source,
                    'type':type,
                    **chunk.metadata # 将 metadata 扁平化展开存入动态字段中
                })
            # 调用原生 insert 接口
            self.client.insert(
                collection_name=self.collection_name,
                data=data_to_insert
            )
            run_logger.info(f"成功导入 {len(data_to_insert)} 条切片。")
        except Exception as e:
            run_logger.error(f"添加文本失败: {e}")

    # =====================================================
    # Hybrid Search 逻辑优化
    # =====================================================
    def retrieve(self, query: str, local_k: int = 5) -> list[Document]:
        """检索文档"""
            
        docs = self.search_hybrid(query=query, k=local_k)
        run_logger.info(f"本地检索到 {len(docs)} 条相关文档")
        
        return docs
    

_knowledge_instance = None
def get_knowledge():
    """只有在被显式调用时，才会进行真正的懒加载初始化"""
    global _knowledge_instance
    if _knowledge_instance is None:
        try:
            run_logger.info("首次调用，正在安全初始化 KnowledgeManager...")
            _knowledge_instance = KnowledgeManager()
        except Exception as e:
            run_logger.error(f"❌ 知识库初始化失败: {e}")
            raise e
    return _knowledge_instance
# # =====================================================
# # 全局知识库实例
# # =====================================================
# try:
#     knowledge = KnowledgeManager()
# except Exception as e:
#     run_logger.error(f"❌ 知识库初始化失败: {e}")
#     knowledge = None


@tool
def knowledge_search(query: str) -> str:
    """
    在 CodeTeam 内部技术知识库中检索开发文档、API 接口说明及架构设计方案。
    
    当用户询问团队内部的接口定义、部署流程、代码规范、组件使用方法
    或历史技术沉淀时，应调用此工具获取权威解答。

    Args:
        query (str): 针对开发文档的检索词。应包含具体的组件名、接口名或技术关键字。

    Returns:
        str: 包含相关文档片段、MDN/内部链接及代码示例的 Markdown 或 JSON 字符串。
    """
    run_logger.info('knowledge_search tool called..')
    knowledge = get_knowledge()  # 确保知识库已初始化

    try:
        docs = knowledge.retrieve(query=query)
        if not docs:
            return "未找到相关知识。"
        return "\n\n".join(doc.get("text", doc) if isinstance(doc, dict) else doc.page_content for doc in docs[:5])
    except Exception as e:
        run_logger.error(f"搜索失败: {e}")
        return "搜索失败，请稍后重试。"

# with open('./prod.md', mode='r') as f:
#     content = f.read()
#     knowledge.add_text(content, 'prod.md', 'local')
#     docs = knowledge.retrieve(query='实现网格随机算法')
#     run_logger.info(docs)

# 直接调用来加载知识。
import argparse

if __name__ == "__main__":
    # 1. 创建参数解析器
    parser = argparse.ArgumentParser(description="CodeTeam 知识库本地文件导入工具")
    
    # 2. 添加必填的文件路径参数
    parser.add_argument(
        'file_path', 
        type=str, 
        help='要导入的 Markdown 文件路径 (例如: ./prod.md)'
    )
    
    # 解析命令行参数
    args = parser.parse_args()

    # 3. 校验文件是否存在
    if not os.path.exists(args.file_path):
        run_logger.error(f"文件未找到: {args.file_path}")
        exit(1)

    # 4. 自动获取文件名（例如从 './docs/prod.md' 中提取出 'prod.md'）
    file_name = os.path.basename(args.file_path)

    try:
        # 5. 初始化知识库并读取文件
        knowledge = get_knowledge()
        
        with open(args.file_path, mode='r', encoding='utf-8') as f:
            content = f.read()
            
            # 动态传入文件内容和文件名
            knowledge.add_text(content, file_name, 'local')
            run_logger.info(f"成功将文件 [{file_name}] 加载到知识库！")
            
            # 测试检索效果
            docs = knowledge.retrieve(query='实现网格随机算法')
            run_logger.info(f"检索测试结果: {docs}")
            
    except Exception as e:
        run_logger.error(f"加载知识库失败: {str(e)}")