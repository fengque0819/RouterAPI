from src.Exception import HttpException
from src.TrieTree import TrieTree
from src.logger import logger
from app.handler import user_handler_request
from http.server import HTTPServer


if __name__ == '__main__':
    # 注册路由
    router = TrieTree()
    router.insert(path="/", handler_func=user_handler_request, methods=["GET"])
    router.insert("/*", user_handler_request, methods=["GET"])
    router.insert("/user/{id}", user_handler_request, methods=["GET", "POST"])
    router.insert("/user/{id}/*file", user_handler_request, methods=["GET"])

    # 启动httpserver
    server = HTTPServer(('localhost', 9000), )
    logger.info("Server running on http://localhost:9000")
    server.serve_forever()
