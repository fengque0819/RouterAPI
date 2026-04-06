# 错误处理
class HttpException(Exception):
    __slots__ = ('status_code', 'message')

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return str(self.status_code) + self.message