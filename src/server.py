import signal
import socket
import asyncio
from logger import logger
from request import Request
from Exception import HttpException
from TrieTree import TrieTree


class AsyncHttpServer:
    def __init__(self, host='127.0.0.1', port=8000, router=None):
        self.host = host
        self.port = port
        self.router = router  # 此处对接你的 Trie 树路由
        self.server_socket = None   # 服务端socket
        self._is_running = False
        self._active_tasks = set()  # 记录正在处理的客户端任务

    async def shutdown(self):
        """统一的关闭函数：负责清理所有资源"""
        if not self._is_running:
            return
        self._is_running = False
        # 1. 停止接收新连接
        if self.server_socket:
            self.server_socket.close()
            logger.info("监听套接字已关闭")
        # 2. 取消所有正在进行的客户端任务
        if self._active_tasks:
            logger.info(f"正在取消任务")
            for task in self._active_tasks:
                task.cancel()
            # 等待任务完成取消动作
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        logger.info("服务器已关闭")

    async def handle_client(self, client_sock):
        """处理具体的客户端连接"""
        addr = client_sock.getpeername()
        # 服务端默认的keep-alive设置
        default_timeout = 10
        default_max = 100
        # 第一次响应请求以服务器设置为准
        current_timeout = default_timeout
        current_max = default_max
        request_count = 0
        keep_alive = True
        try:
            while keep_alive and self._is_running:
                # 设置接收超时，防止死连接
                try:
                    raw_data = await asyncio.wait_for(
                        asyncio.get_running_loop().sock_recv(client_sock, 8192),
                        timeout=current_timeout
                    )
                except asyncio.TimeoutError:  # 链接超时
                    logger.info(f"请求{addr}超时")
                    break
                # 客户端断开
                if not raw_data:
                    break
                # 当前循环计数
                request_count += 1
                # 解析请求
                request = Request(raw_data)
                if not request.is_valid:   # 请求解析错误
                    break
                logger.info(f"请求来自{addr}")
                # 根据请求更新当前的keep-alive设置，只需更新一次
                if not request.keep_alive_params and request_count == 1:
                    current_timeout = min(request.keep_alive_params["timeout"], current_timeout)
                    current_max = min(request.keep_alive_params["max"], current_max)

                # 获取路由匹配结果
                result = self.router.search_route(request.path, request.method)
                if result is None:
                    response_body = b"<h1>Something is Wrong From Server</h1>"
                else:
                    handler_func = result["handler_func"]
                    params = result["param"]
                    response_body = await handler_func(request, **params)

                if request.is_keep_alive:
                    headers = [
                        f"{request.version} 200 OK",
                        f"Connection: keep-alive",
                        f"Keep-Alive: timeout={current_timeout}, max={current_max - request_count}",
                        f"Content-Length: {len(response_body)}"
                    ]
                else:
                    headers = [
                        f"{request.version} 200 OK",
                        f"Connection: close",
                        f"Content-Length: {len(response_body)}"
                    ]
                    keep_alive = False

                await asyncio.get_running_loop().sock_sendall(client_sock, headers + response_body)
                # 退出循环
                if request_count >= current_max:
                    keep_alive = False
        except Exception as e:
            logger.error(f"连接{addr}出错: {e}")
        finally:
            client_sock.close()

    async def start(self):
        """服务器启动入口"""
        loop = asyncio.get_running_loop()

        # 1. 初始化 Socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(128)
        self.server_socket.setblocking(False)

        self._is_running = True
        logger.info("服务已启动")

        # 主循环
        try:
            while self._is_running:
                client_sock, addr = await loop.sock_accept(self.server_socket)
                # 设置客户端socket非阻塞
                client_sock.setblocking(False)
                # 创建任务并加入任务集
                task = asyncio.create_task(self.handle_client(client_sock))
                self._active_tasks.add(task)
                # 任务完成时自动移除，防止内存泄漏
                task.add_done_callback(self._active_tasks.discard)
        except (asyncio.CancelledError, OSError):
            # 正常关闭或 Socket 关闭时抛出的异常，无需报错
            pass
        finally:
            await self.shutdown()


