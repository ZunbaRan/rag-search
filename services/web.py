# 导入html2text库，用于将HTML转换为Markdown格式
import html2text
# 导入asyncio库，用于支持异步编程
import asyncio
# 导入aiohttp库，用于异步HTTP请求
import aiohttp
# 导入re库，用于正则表达式操作
import re


async def fetch_url(session, url):
    """异步获取指定URL的HTML内容"""
    # 使用session异步发送GET请求到指定URL
    async with session.get(url) as response:
        try:
            # 检查HTTP响应状态，如果不是200则抛出异常
            response.raise_for_status()
            # 设置响应编码为utf-8
            response.encoding = 'utf-8'
            # 异步获取响应文本内容
            html = await response.text()

            # 返回获取到的HTML内容
            return html
        except Exception as e:
            # 捕获并打印任何异常
            print(f"fetch url failed: {url}: {e}")
            # 发生异常时返回空字符串
            return ""


async def html_to_markdown(html):
    """将HTML内容转换为Markdown格式"""
    try:
        # 创建HTML2Text实例
        h = html2text.HTML2Text()
        # 设置忽略链接
        h.ignore_links = True
        # 设置忽略图片
        h.ignore_images = True

        # 将HTML转换为Markdown
        markdown = h.handle(html)

        # 返回转换后的Markdown文本
        return markdown
    except Exception as e:
        # 捕获并打印任何异常
        print(f"html to markdown failed: {e}")
        # 发生异常时返回空字符串
        return ""


async def fetch_markdown(session, url):
    """获取URL内容并转换为Markdown格式"""
    try:
        # 获取URL的HTML内容
        html = await fetch_url(session, url)
        # 将HTML转换为Markdown
        markdown = await html_to_markdown(html)
        # 使用正则表达式将连续的多个换行符替换为单个换行符
        # 注意：这里有语法错误，\n{2,n}中的n应该是一个数字，正确的应该是\n{2,}
        markdown = re.sub(r'\n{2,}', '\n', markdown)

        # 返回URL和对应的Markdown内容
        return url, markdown
    except Exception as e:
        # 捕获并打印任何异常
        print(f"fetch markdown failed: {url}: {e}")
        # 发生异常时返回URL和空字符串
        return url, ""


async def batch_fetch_urls(urls):
    """批量获取多个URL的Markdown内容"""
    # 打印要处理的URL列表
    print("urls", urls)
    try:
        # 创建异步HTTP客户端会话
        async with aiohttp.ClientSession() as session:
            # 为每个URL创建一个获取Markdown的任务
            tasks = [fetch_markdown(session, url) for url in urls]
            # 并行执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=False)

            # 返回所有URL的处理结果
            return results
    except aiohttp.ClientResponseError as e:
        # 捕获并打印HTTP客户端响应异常
        print(f"batch fetch urls failed: {e}")
        # 发生异常时返回空列表
        return []
