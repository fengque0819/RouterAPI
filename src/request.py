from logger import logger
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional, Any
import json
from Exception import HttpException
import re


# 封装请求类
class Request:
    """请求解析类"""

    def __init__(self, raw_data: bytes):
        self.method = ""
        self.path = ""
        self.headers = {}
        self.query_params = {}
        self.body = b""
        self.is_valid = False
        self.version = "HTTP/1.1"   # 请求HTTP协议  默认1.1
        self.is_keep_alive = True
        self.keep_alive_params = {}

        if raw_data:    # 拆解请求字节
            self._parse(raw_data)

    """
        POST /api/search?q=python&lang=zh HTTP/1.1\r\n
        Host: api.example.com\r\n
        Content-Type: application/json\r\n
        Content-Length: 32\r\n
        Connection: keep-alive\r\n
        Keep-Alive: timeout=5, max=100\r\n
        Accept-Encoding: gzip\r\n\r\n
        {"keyword":"asyncio","version":"3.12"}
    """

    def _parse(self, data: bytes):
        try:
            # 严格按照 \r\n\r\n 分割请求头与请求体
            parts = data.split(b"\r\n\r\n", 1)
            header_section = parts[0].decode('utf-8')    # 请求头转为字符串
            self.body = parts[1] if len(parts) > 1 else b""   # 请求体 若无则为空

            # 分割请求头
            lines = header_section.split("\r\n")
            if not lines:  # 请求头为空
                return

            # 请求行  "POST /api/search?q=python&lang=zh HTTP/1.1"
            request_line = lines[0].split()
            if len(request_line) < 3:
                return
            self.method = request_line[0].upper()   # 方法
            parsed_url = urlparse(request_line[1])  # 路由
            self.path = parsed_url.path
            self.query_params = parse_qs(parsed_url.query)  # 请求参数
            self.version = request_line[2].upper()   # HTTP协议

            # 分割请求头剩余部分
            for line in lines[1:]:
                if ": " in line:
                    k, v = line.split(": ", 1)
                    self.headers[k.strip().lower()] = v.strip()  # 统一小写方便查找

            # keep-alive属性
            conn_header = self.headers.get("connection", "").lower()
            # 1.1版本明确close；1.0版本未明确keep-alive
            if self.version == "HTTP/1.1":
                if conn_header == "close":
                    self.is_keep_alive = False
            elif self.version == "HTTP/1.0":
                if conn_header != "keep-alive":
                    self.is_keep_alive = False

            if self.is_keep_alive:
                keep_alive_str = self.headers.get("keep-alive", "")  # 获取keep-alive字段键值
                if keep_alive_str:
                    t_match = re.search(r"timeout=(\d+)", keep_alive_str)
                    m_match = re.search(r"max=(\d+)", keep_alive_str)
                    if t_match:
                        self.keep_alive_params["timeout"] = int(t_match.group(1))
                    if m_match:
                        self.keep_alive_params["max"] = int(m_match.group(1))

            self.is_valid = True
        except HttpException as e:
            self.is_valid = False
            logger.error(e.message)