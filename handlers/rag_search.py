# 导入操作系统相关功能的模块
import os
# 导入类型提示相关的模块
from typing import Optional
# 导入Pydantic的BaseModel用于数据验证
from pydantic import BaseModel
# 导入FastAPI的路由器和请求头处理组件
from fastapi import APIRouter, Header
# 导入搜索服务，用于获取搜索结果
from services.search.serper import get_search_results
# 导入LlamaIndex重排序服务，并重命名为get_rerank_llamaindex
from services.rerank.llamaindex import get_rerank_results as get_rerank_llamaindex
# 导入FlashRank重排序服务，并重命名为get_rerank_flashrank
from services.rerank.flashrank import get_rerank_results as get_rerank_flashrank
# 导入通用重排序服务
from services.rerank.rerank import rerank
# 导入文档存储服务
from services.document.store import store_results
# 导入文档查询服务
from services.document.query import query_results
# 导入网页内容获取服务
from services.web import batch_fetch_urls
# 导入响应工具函数
from utils.resp import resp_err, resp_data


# 创建FastAPI路由器实例
rag_router = APIRouter()


# 定义RAG搜索请求的数据模型，继承自Pydantic的BaseModel
class RagSearchReq(BaseModel):
    query: str                                    # 搜索查询字符串，必填字段
    locale: Optional[str] = ''                    # 区域设置，可选字段，默认为空字符串
    search_n: Optional[int] = 10                  # 搜索结果数量，可选字段，默认为10
    search_provider: Optional[str] = 'google'     # 搜索提供商，可选字段，默认为'google'
    is_reranking: Optional[bool] = False          # 是否进行重排序，可选字段，默认为False
    is_detail: Optional[bool] = False             # 是否获取详细内容，可选字段，默认为False
    detail_top_k: Optional[int] = 6               # 获取详细内容的结果数量，可选字段，默认为6
    detail_min_score: Optional[float] = 0.70      # 获取详细内容的最低分数阈值，可选字段，默认为0.70
    is_filter: Optional[bool] = False             # 是否过滤内容，可选字段，默认为False
    filter_min_score: Optional[float] = 0.80      # 过滤内容的最低分数阈值，可选字段，默认为0.80
    filter_top_k: Optional[int] = 6               # 过滤后保留的结果数量，可选字段，默认为6


# 定义RAG搜索API端点，使用POST方法
@rag_router.post("/rag-search")
async def rag_search(req: RagSearchReq, authorization: str = Header(None)):
    """
    RAG搜索API端点
    
    该方法实现了一个完整的RAG(检索增强生成)搜索流程：
    1. 验证API密钥
    2. 执行搜索获取初始结果
    3. 可选地对结果进行重排序
    4. 可选地获取搜索结果的详细内容
    5. 可选地过滤内容
    6. 返回处理后的搜索结果
    """
    # 从环境变量获取认证API密钥
    authApiKey = os.getenv("AUTH_API_KEY")
    # 初始化API密钥变量
    apiKey = ""
    # 如果请求头中包含authorization字段
    if authorization:
        # 从authorization字段中提取API密钥，去除"Bearer "前缀
        apiKey = authorization.replace("Bearer ", "")
    # 验证API密钥是否匹配
    if apiKey != authApiKey:
        # 如果不匹配，返回访问拒绝错误
        return resp_err("Access Denied")

    # 验证查询参数是否为空
    if req.query == "":
        # 如果查询为空，返回参数无效错误
        return resp_err("invalid params")

    try:
        # 初始化搜索结果列表
        search_results = []
        # 1. 获取搜索结果
        try:
            # 调用search函数执行搜索
            search_results = search(req.query, req.search_n, req.locale)
        except Exception as e:
            # 如果搜索失败，返回错误信息
            return resp_err(f"get search results failed: {e}")

        # 2. 如果启用了重排序
        if req.is_reranking:
            try:
                # 对搜索结果进行重排序
                search_results = rerank(search_results, req.query)
            except Exception as e:
                # 如果重排序失败，记录错误但继续执行
                print(f"reranking search results failed: {e}")

        # 3. 如果启用了详细内容获取
        if req.is_detail:
            try:
                # 获取搜索结果的详细内容
                search_results = await fetch_details(search_results, req.detail_min_score, req.detail_top_k)
            except Exception as e:
                # 如果获取详细内容失败，记录错误但继续执行
                print(f"fetch search details failed: {e}")

        # 4. 如果启用了内容过滤
        if req.is_filter:
            try:
                # 过滤搜索结果内容
                search_results = filter_content(search_results, req.query, req.filter_min_score, req.filter_top_k)
            except Exception as e:
                # 如果内容过滤失败，记录错误但继续执行
                print(f"filter content failed: {e}")

        # 返回处理后的搜索结果
        return resp_data({
            "search_results": search_results,
        })
    except Exception as e:
        # 捕获并返回任何未处理的异常
        return resp_err(f"rag search failed: {e}")


def search(query, num, locale=''):
    """
    执行搜索查询
    
    该方法使用搜索服务获取与查询相关的搜索结果。
    它接受查询字符串、结果数量和可选的区域设置参数，
    并返回搜索结果列表。
    """
    # 构建搜索参数字典
    params = {
        "q": query,        # 查询字符串
        "num": num         # 结果数量
    }

    # 如果提供了区域设置
    if locale:
        # 将区域设置添加到参数中
        params["hl"] = locale

    try:
        # 调用搜索服务获取搜索结果
        search_results = get_search_results(params=params)

        # 返回搜索结果
        return search_results
    except Exception as e:
        # 记录搜索失败的错误
        print(f"search failed: {e}")
        # 重新抛出异常
        raise e


async def fetch_details(search_results, min_score=0.00, top_k=6):
    """
    获取搜索结果的详细内容
    
    该方法从搜索结果中提取URL，然后异步获取这些URL的网页内容，
    并将内容添加到相应的搜索结果中。它根据分数阈值和结果数量限制
    来选择要获取详细内容的URL。
    """
    # 初始化URL列表
    urls = []
    # 遍历搜索结果
    for res in search_results:
        # 如果已收集的URL数量超过top_k，停止收集
        if len(urls) > top_k:
            break
        # 如果结果的分数大于等于最低分数阈值
        if res["score"] >= min_score:
            # 将结果的链接添加到URL列表
            urls.append(res["link"])

    try:
        # 异步批量获取URL的内容
        details = await batch_fetch_urls(urls)
    except Exception as e:
        # 记录获取详细内容失败的错误
        print(f"fetch details failed: {e}")
        # 重新抛出异常
        raise e

    # 创建URL到内容的映射字典
    content_maps = {}
    # 遍历获取到的URL和内容对
    for url, content in details:
        # 将URL和内容添加到映射字典
        content_maps[url] = content

    # 遍历搜索结果
    for result in search_results:
        # 如果结果的链接在内容映射中
        if result["link"] in content_maps:
            # 将内容添加到结果中
            result["content"] = content_maps[result["link"]]

    # 返回更新后的搜索结果
    return search_results


def filter_content(search_results, query, filter_min_score=0.8, filter_top_k=10):
    """
    过滤搜索结果内容
    
    该方法对搜索结果进行进一步过滤，只保留与查询最相关的内容。
    它首先筛选出有内容的结果，然后将这些结果存储到向量数据库中，
    最后查询数据库以获取与原始查询最相关的结果。
    """
    try:
        # 初始化有内容的结果列表
        results_with_content = []
        # 遍历搜索结果
        for result in search_results:
            # 如果结果包含内容且内容长度大于摘要长度
            if "content" in result and len(result["content"]) > len(result["snippet"]):
                # 将结果添加到有内容的结果列表
                results_with_content.append(result)

        # 将有内容的结果存储到向量数据库中，返回索引
        index = store_results(results=results_with_content)
        # 查询向量数据库，获取与查询最相关的结果
        match_results = query_results(index, query, filter_min_score, filter_top_k)

    except Exception as e:
        # 记录内容过滤失败的错误
        print(f"filter content failed: {e}")
        # 重新抛出异常
        raise e

    # 创建UUID到内容的映射字典
    content_maps = {}
    # 遍历匹配的结果
    for result in match_results:
        # 如果结果的UUID不在内容映射中
        if result["uuid"] not in content_maps:
            # 初始化该UUID的内容为空字符串
            content_maps[result["uuid"]] = ""
        else:
            # 否则，将内容追加到该UUID的现有内容
            content_maps[result["uuid"]] += result["content"]

    # 遍历原始搜索结果
    for result in search_results:
        # 如果结果的UUID在内容映射中
        if result["uuid"] in content_maps:
            # 更新结果的内容
            result["content"] = content_maps[result["uuid"]]

    # 返回更新后的搜索结果
    return search_results