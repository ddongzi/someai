import logging
import os
from langchain.tools import tool
from pymilvus import MilvusClient, DataType,AnnSearchRequest, RRFRanker
from FlagEmbedding import BGEM3FlagModel
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter
from typing import List
from tools import web_search
from pprint import pprint
from globals.logger import run_logger

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

    def clear_data(self):
        if self.client.has_collection(collection_name=self.collection_name):
            run_logger.info(f'drop: {self.collection_name} ...')
            self.client.drop_collection(collection_name=self.collection_name)


    def search_dense(self, queries: List[str], k: int = 5) -> list:
        """
        专职：单独进行稠密向量检索（纯语义匹配）
        
        Args:
            query: 用户的查询文本字符串
            k: 需要返回的最相关结果数量
        """
        if not self.client or not self.embedding:
            run_logger.warning(f"Milvus 不可用，无法进行稠密搜索: {query}")
            return []
            
        try:
            # 1. 生成查询词的稠密向量 (只提取 dense_vecs)
            vec = self.embedding.encode(queries, return_dense=True, return_sparse=False)
            dense_vec = vec['dense_vecs'] # 取出第一条查询的向量
            
            # 2. 执行标准的向量相似度搜索
            search_results = self.client.search(
                collection_name=self.collection_name,
                data=dense_vec,
                anns_field="dense_vec",       # 确保与你集合中的稠密向量字段名一致
                limit=k,
                output_fields=["text"] # 显式带回你需要的业务字段
            )
            # pprint(f'dense results: {search_results}')
            
            return search_results[0] if search_results else []
            
        except Exception as e:
            run_logger.error(f"单独稠密搜索发生异常: {str(e)}")
            return []


    def search_hybrid(self, queries: List[str], k: int = 5):
        """只进行混合搜索"""
        if not self.client or not self.embedding:
            run_logger.warning(f"Milvus 不可用，无法搜索: {queries}")
            return []
            
        try:
            # 1. 同时生成查询词的 稠密 和 稀疏 向量
            vec = self.embedding.encode(queries, return_dense=True, return_sparse=True)
            dense_vec,sparse_vec = vec['dense_vecs'], vec["lexical_weights"]
            
            # 2. 构建稠密向量（语义）检索请求
            req_dense = AnnSearchRequest(
                data=dense_vec, 
                anns_field="dense_vec", 
                param={"metric_type": "COSINE"}, 
                limit=k * 2  # 放大召回范围供后续融合
            )
            
            # 3. 构建稀疏向量（关键词/Header）检索请求
            req_sparse = AnnSearchRequest(
                data=sparse_vec, 
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
                    distance = hit.get('distance', 0)
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
                        'distance':distance
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
            run_logger.info(f'add text. {source}, {type}')
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
    def retrieve(self,queries: List[str], local_k: int = 5) -> list[Document]:
        """检索文档"""
            
        docs = self.search_hybrid(queries=queries, k=local_k)
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
def knowledge_search(queries: List[str]) -> str:
    """
    在内部技术知识库中检索开发文档、API 接口说明及架构设计方案。
    
    Args:
        queries (List[str]):  一些检索词句

    Returns:
        str: 包含相关文档片段、MDN/内部链接及代码示例的 Markdown 或 JSON 字符串。

    Note：
        1. 不要过度依赖：知识库仅提供了一些部分关键要求。有一些细节内容知识库可能没有收录，应该由外部合理推导。
        2. 禁止重复检索：不要使用相似的query多次检索，而应该使用过往的查询记录。
        3. 优质的查询：检索知识库是耗时操作，应该尽可能组织优质的queries一次查询出来,避免多次查询.
    """

    run_logger.info('knowledge_search tool called..')
    knowledge = get_knowledge()  # 确保知识库已初始化

    try:
        # 不会引入太多的知识
        docs = knowledge.retrieve(queries=queries, local_k=2)
        if not docs:
            return "未找到相关知识。"
        return "\n\n".join(doc.get("text", doc) if isinstance(doc, dict) else doc.page_content for doc in docs[:5])
    except Exception as e:
        run_logger.error(f"搜索失败: {e}")
        return "搜索失败，请稍后重试。"




# with open('./prod.md', mode='r') as f:
#     content = f.read()
#     knowledge = get_knowledge()
#     knowledge.add_text(content, 'prod.md', 'local')
#     # result = knowledge.search_dense(queries=['seedManager'])
#     # print(result)
#     result = knowledge.retrieve(
#         queries=[
#                 'seedManager',
#         ],
#         local_k=2
#     )
#     print(result)



import os
import argparse
from pathlib import Path

if __name__ == "__main__":
    # 1. 创建参数解析器（允许用户通过 -d 自定义目录，默认就是 'knowledges'）
    parser = argparse.ArgumentParser(description="CodeTeam 知识库批量文件导入工具")
    parser.add_argument(
        '--dir', 
        type=str, 
        default='knowledges',
        help='存放知识库文件的目标目录路径 (默认: knowledges)'
    )
    args = parser.parse_args()

    # 2. 校验目标知识库文件夹是否存在
    target_dir = Path(args.dir)
    if not target_dir.exists() or not target_dir.is_dir():
        run_logger.error(f"❌ 目标目录不存在或不是有效的文件夹: {target_dir.absolute()}")
        exit(1)

    # 3. 扫描该目录下所有的文本文件 (支持 .md 和 .txt)
    # rglob 表示递归扫描子文件夹，如果只想扫描当前层级可以换成 glob
    valid_extensions = {'.md', '.txt', '.markdown'}
    all_files = [f for f in target_dir.rglob('*') if f.is_file() and f.suffix.lower() in valid_extensions]

    if not all_files:
        run_logger.warning(f"⚠️ 文件夹 [{target_dir}] 内未找到任何有效的文本文件 (.md, .txt)。")
        exit(0)

    run_logger.info(f"📂 发现待导入的知识文件共 {len(all_files)} 个，开始批量加载...")

    try:
        # 4. 初始化知识库
        knowledge = get_knowledge()
        success_count = 0

        # 5. 循环处理每一个文件
        for file_path in all_files:
            file_name = file_path.name
            
            try:
                # 使用 Path 自动处理编码和读取，更安全健壮
                content = file_path.read_text(encoding='utf-8')
                
                # 动态传入文件内容和文件名
                knowledge.add_text(content, file_name, 'local')
                run_logger.info(f"✅ 成功加载文件: {file_name}")
                success_count += 1
                
            except Exception as file_err:
                run_logger.error(f"❌ 读取文件 [{file_name}] 失败，跳过该文件。原因: {str(file_err)}")

        run_logger.info(f"📊 批量加载完成！成功: {success_count}/{len(all_files)}")

        # 6. 测试检索效果
        if success_count > 0:
            print("\n" + "="*30 + " 🔍 检索效果测试 " + "="*30)
            test_query = '实现网格随机算法'
            docs = knowledge.retrieve(queries=[test_query])
            run_logger.info(f"针对关键词 [{test_query}] 的检索测试结果: {docs}")
            print("="*75 + "\n")
            
    except Exception as e:
        run_logger.error(f"💥 知识库处理过程中发生全局异常: {str(e)}")
