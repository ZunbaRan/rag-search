from llama_index.legacy import Document, VectorStoreIndex
from llama_index.legacy.node_parser import SimpleNodeParser
from services.vdb.zilliz import get_storage_context
from services.llm.openai import get_service_context
from utils.hash import md5


def store_results(results):
    """
    将搜索结果存储到向量数据库中
    
    该方法接收搜索结果列表，将每个结果转换为Document对象，
    然后将这些文档分块并创建向量索引。最终返回创建的索引对象，
    该索引可用于后续的相似性搜索。
    """
    documents = []
    for result in results:
        document = build_document(result=result)
        documents.append(document)

        print(
            "build index for result: ",
            result["title"],
            result["link"],
            len(documents),
        )

    nodes = build_nodes(documents=documents)
    print("nodes count", len(nodes), len(documents))

    # index = VectorStoreIndex(nodes)
    # index.storage_context.persist(persist_dir="./storage")

    storage_context = get_storage_context()
    service_context = get_service_context()

    index = VectorStoreIndex(nodes=nodes,
                             storage_context=storage_context,
                             service_context=service_context)

    print("build index ok", storage_context)

    return index


def build_document(result):
    """
    将搜索结果转换为Document对象
    
    该方法接收一个搜索结果字典，提取其中的信息，
    创建并返回一个Document对象。Document对象包含
    文本内容和元数据，用于后续的向量化和检索。
    """
    if not result["link"] or not result["snippet"]:
        return

    uuid = ""
    if "uuid" in result:
        uuid = result["uuid"]
    else:
        uuid = md5(result["link"])

    text = result["snippet"]
    if "content" in result and len(result["content"]) > len(result["snippet"]):
        text = result["content"]

    document = Document(
        text=text,
        metadata={
            "uuid": uuid,
            "title": result["title"],
            "snippet": result["snippet"],
            "link": result["link"],
        },
        metadata_template="{key}: {value}",
        text_template="{metadata_str}\n\n{content}",
    )
    document.doc_id = uuid
    document.excluded_llm_metadata_keys = ["link", "score"]
    document.excluded_embed_metadata_keys = ["link", "score"]

    return document


def build_nodes(documents):
    """
    将Document对象列表转换为节点列表
    
    该方法使用SimpleNodeParser将Document对象分割成更小的节点，
    这些节点是向量索引的基本单位。分割成更小的节点有助于提高
    检索的精度和效率。
    """
    parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=20)

    nodes = parser.get_nodes_from_documents(documents=documents, show_progress=True)

    return nodes
