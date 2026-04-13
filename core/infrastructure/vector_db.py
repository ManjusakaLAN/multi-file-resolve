import logging
from typing import List, Dict, Any
from packaging import version
from pymilvus import MilvusClient, DataType, AnnSearchRequest, RRFRanker, MilvusException

from core.config import settings

logger = logging.getLogger(__name__)


class MilvusVectorDB:
    """
    基于 MilvusClient 的混合搜索(Hybrid Search)基础设施层
    支持：Dense + BM25 检索、自动数据库路由、动态元数据存储
    """

    def __init__(self):
        self.uri = settings.MILVUS_URI
        self.user = settings.MILVUS_USER
        self.password = settings.MILVUS_PASSWORD
        self.db_name = settings.MILVUS_DATABASE

        # 初始化客户端
        self.client = self._init_client()

        # 预检混合搜索支持 (Milvus 2.5.0+)
        self.is_hybrid_supported = self._check_hybrid_support()

    def _init_client(self) -> MilvusClient | None:
        """初始化并确保目标数据库存在"""
        # 1. 连接管理空间
        admin_client = MilvusClient(uri=self.uri, user=self.user, password=self.password)

        try:
            if self.db_name not in admin_client.list_databases():
                admin_client.create_database(self.db_name)
                logger.info(f"成功创建 Milvus 数据库: {self.db_name}")
        except MilvusException as e:
            logger.error(f"管理 Milvus 数据库失败: {e}")
        finally:
            admin_client.close()

        # 2. 返回业务数据库客户端
        return MilvusClient(
            uri=self.uri,
            user=self.user,
            password=self.password,
            db_name=self.db_name
        )

    def _check_hybrid_support(self) -> bool:
        try:
            ver = self.client.get_server_version()
            return version.parse(ver).base_version >= version.parse("2.5.0").base_version
        except Exception as e:
            logger.error(f"检查 Milvus 版本失败: {e}")
            return False

    def _ensure_loaded(self, collection_name: str):
        """内部助手：确保集合已加载到内存"""
        state = self.client.get_load_state(collection_name)
        if state != "Loaded":
            logger.info(f"正在加载集合: {collection_name}")
            self.client.load_collection(collection_name)

    def create_hybrid_collection(self, collection_name: str, dim: int = 1024):
        """
        创建支持混合检索的集合
        """
        if self.client.has_collection(collection_name):
            self._ensure_loaded(collection_name)
            return

        # 1. 定义 Schema (开启动态字段以存储任意 metadata)
        schema = self.client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="meta_data", datatype=DataType.JSON)

        # 混合检索必备：稀疏向量字段
        if self.is_hybrid_supported:
            schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

        # 2. 准备索引参数
        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="vector", metric_type="COSINE", index_type="AUTOINDEX")

        if self.is_hybrid_supported:
            index_params.add_index(
                field_name="sparse_vector",
                metric_type="BM25",
                index_type="SPARSE_INVERTED_INDEX"
            )

        # 3. 启用全文检索函数 (将文本自动转为稀疏向量)
        if self.is_hybrid_supported:
            # 注意：某些 PyMilvus 版本通过 schema 配置 Function，此处直接在 create 流程中由索引触发 BM25 逻辑
            pass

        self.client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )
        self.client.load_collection(collection_name)
        logger.info(f"混合集合 {collection_name} 初始化完成")

    def upsert(self, collection_name: str, data: List[Dict[str, Any]]):
        """
        插入或更新数据

        data 示例:
        [
            {
                # 1. 显式定义的必填字段
                "vector": [0.1, 0.2, ...],        # 稠密向量 (Dense Vector)
                "text": "本合同自双方签字盖章之日起生效。", # 原始文本内容

                # 2. 显式定义的 JSON 字段 (meta_data)
                # 建议将结构化、固定的元数据存放在这里
                "meta_data": {
                    "file_id": 1024,
                    "page_no": 5,
                    "contract_type": "采购合同"
                },

                # 3. 动态字段 (因为开启了 enable_dynamic_field=True)
                # 如果你不想手动包一层 meta_data，也可以直接平铺
                # 它们会被 Milvus 自动收集并支持过滤查询
                "author": "用户x",
                "project_name": "合同审查系统V1"
            }
        ]
        """
        return self.client.upsert(collection_name=collection_name, data=data)

    def search(self,
               collection_name: str,
               query_text: str,
               dense_vector: List[float],
               limit: int = 5,
               filter_expr: str = "",
               output_fields: List[str] = None):
        """
        向量查询
        :param collection_name: 集合名称
        :param query_text: 查询文本内容
        :param dense_vector:
        :param limit:
        :param filter_expr:
        :param output_fields:
        :return:
        """
        self._ensure_loaded(collection_name)
        output_fields = output_fields or ["text"]

        if not self.is_hybrid_supported:
            return self.client.search(
                collection_name=collection_name,
                data=[dense_vector],
                filter=filter_expr,
                limit=limit,
                output_fields=output_fields,
                anns_field="vector"
            )

        # 稠密子查询
        res_dense = AnnSearchRequest(
            data=[dense_vector],
            anns_field="vector",
            param={"metric_type": "COSINE"},
            limit=limit,
            expr=filter_expr
        )

        # 稀疏子查询 (BM25)
        res_sparse = AnnSearchRequest(
            data=[query_text],
            anns_field="sparse_vector",
            param={"metric_type": "BM25"},
            limit=limit,
            expr=filter_expr
        )

        return self.client.hybrid_search(
            collection_name=collection_name,
            reqs=[res_dense, res_sparse],
            ranker=RRFRanker(k=60),
            limit=limit,
            output_fields=output_fields
        )

    def delete(self, collection_name: str, expr: str):
        """
        删除向量数据
        :param collection_name: 集合名称
        :param expr: 过滤表达式，例如 'meta_data["file_id"] == 1024'。 text == "一段文字内容"
        delete 的 expr 必须是确定性的。它不支持模糊匹配（如 like），只支持精确匹配（==, in）和范围匹配（>, <）。
        """
        if not expr:
            logger.warning(f"尝试对集合 {collection_name} 执行空条件删除，操作已拦截。")
            return None

        try:
            # 注意：MilvusClient 的 delete 接口参数名通常也是 filter
            res = self.client.delete(collection_name=collection_name, filter=expr)
            logger.info(f"成功从 {collection_name} 删除数据，条件: {expr}")
            return res
        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            raise e

    def drop_collection(self, collection_name: str):
        """
        物理删除集合及其所有数据和索引
        :param collection_name: 集合名称
        """
        try:
            if self.client.has_collection(collection_name):
                # 执行删除
                self.client.drop_collection(collection_name=collection_name)
                logger.info(f"成功删除集合: {collection_name}")
            else:
                logger.warning(f"集合 {collection_name} 不存在，无需删除。")
        except Exception as e:
            logger.error(f"删除集合 {collection_name} 失败: {e}")
            raise e

    def list_all_collections(self) -> List[str]:
        """
        列出当前数据库中所有的集合名称
        :return: 集合名称列表，例如 ['contract_v1', 'task_cache']
        """
        try:
            collections = self.client.list_collections()
            logger.info(f"当前数据库 [{self.db_name}] 中的集合数量: {len(collections)}")
            return collections
        except Exception as e:
            logger.error(f"获取集合列表失败: {e}")
            return []

    def close(self):
        """
        关闭连接
        :return:
        """
        self.client.close()


# 导出混合搜索单例
try:
    milvus_vdb = MilvusVectorDB()
    logger.info("MilvusVectorDB 初始化成功")
except Exception as e:
    logger.error(f"初始化 MilvusVectorDB 失败: {e}")

