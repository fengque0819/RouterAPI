import asyncio
from src.logger import logger
from src.server import AsyncHttpServer
from src.TrieTree import TrieTree
from app.handler import *


async def main():
    # 注册路由
    router = TrieTree()

    # 启动异步服务器
    server = AsyncHttpServer(host="127.0.0.1", port=9000, router=router)
    try:
        await server.start()
    except KeyboardInterrupt:
        # Ctrl+C
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
