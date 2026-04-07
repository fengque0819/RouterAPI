from typing import Callable
from .Exception import HttpException


# 路由节点
class TrieTreeNode:
    """
    同一个节点下仅允许存在一个参数或者一个通配符节点
    不可同时出现 /id/{id}  /id/{name}
    注册/匹配路由路径
    优先级:静态>参数>通配符
    """
    __slots__ = ('static_route', 'param_route', 'wildcard_route', 'route_handler', 'param_names', 'is_route_end')

    def __init__(self):
        self.static_route = {}  # 存储静态路由
        self.param_route = None  # 参数路由 {id}格式
        self.wildcard_route = None  # 通配符路由 *id格式 默认通配符*参数名_path_
        self.route_handler = {}  # 存储路由处理方法
        self.param_names = []  # 从根到此节点的参数名列表
        self.is_route_end = False  # 路由是否结束


# 路由Trie树
class TrieTree:
    def __init__(self):
        self.root = TrieTreeNode()

    def insert(self, path: str, handler_func: Callable, methods: list | None = None):
        node = self.root  # 根节点
        route_param_names = []  # 路由参数
        # has_wildcard = False  # 注册路由是否存在通配符
        # 网络方法大写
        if methods is None:
            methods = ["GET"]
        methods = [m.upper() for m in methods]
        # 通配符处理
        wildcard_count = sum(1 for s in path.split('/') if '*' in s)
        if wildcard_count > 1:
            raise HttpException(404, "通配符数目出现错误")  # 错误码一律404
        # 根路由
        if path == '/':
            for method in methods:
                if method in node.route_handler:
                    raise HttpException(404, "路由方法重复注册")
                node.route_handler[method] = handler_func
                node.is_route_end = True
        else:
            segments = [s for s in path.split('/') if s]   # 路由中非空部分
            for seg in segments:
                # 静态路由
                if '{' not in seg and '}' not in seg and '*' not in seg:
                    if seg not in node.static_route:
                        node.static_route[seg] = TrieTreeNode()
                    node = node.static_route[seg]
                # 参数路由
                elif seg.startswith('{') and seg.endswith('}'):
                    if node.param_route is not None:
                        raise HttpException(404, "参数路由注册失败")
                    route_param_names.append(seg[1:-1])   # 添加参数名
                    node.param_route = TrieTreeNode()
                    node = node.param_route
                # 通配符路由
                elif seg.startswith('*'):
                    if segments.index(seg) != len(segments) - 1:
                        raise HttpException(404, "通配符路由只能处于结尾")
                    if node.wildcard_route is not None:
                        raise HttpException(404, "通配符路由注册失败")
                    if seg == '*':
                        node.wildcard_route = TrieTreeNode()
                        route_param_names.append('_path_')  # *通配符默认参数名
                        node = node.wildcard_route
                    else:
                        node.wildcard_route = TrieTreeNode()
                        route_param_names.append(seg[1:])
                        node = node.wildcard_route
                else:
                    raise HttpException(404, "路由结构有误")
                # 处理末尾节点
                for method in methods:
                    if method in node.route_handler:
                        raise HttpException(404, "路由方法重复注册")
                    node.route_handler[method] = handler_func
                    node.param_names = route_param_names
                    node.is_route_end = True

    # 进行路由匹配
    @staticmethod
    def search(self, segments: list, node: TrieTreeNode, height: int, param_values: list):
        """深度遍历优先级 静态>参数>通配符"""
        if height == len(segments):
            if node.is_route_end:
                return node
            return None
        # 静态匹配
        if segments[height] in node.static_route:
            static_node = node.static_route[segments[height]]
            match_node = static_node.search(self, segments, height + 1, param_values)
            if match_node is not None:
                return match_node
        # 参数匹配
        if node.param_route is not None:
            param_node = node.param_route
            param_values.append(segments[height])  # 添加路由参数值
            match_node = param_node.search(self, segments, height + 1, param_values)
            if match_node is not None:
                return match_node
            else:
                # 若是后续遍历失败，去除当前添加的参数值
                param_values = param_values[: -1]
        # 通配符匹配
        if node.wildcard_route is not None:
            wildcard_node = node.wildcard_route
            param_values.append('/'.join(segments[height:]))
            return wildcard_node
        # 未匹配
        return None

    # 获取路由对应视图函数、路由参数
    def search_route(self, path: str, method="GET"):
        segments = [s for s in path.split('/') if s]
        node = self.root
        param_values = []
        search_node = self.search(self, segments, node, 0, param_values)
        if search_node is not None:
            if search_node.is_route_end and method in search_node.route_handler:
                param = dict(zip(search_node.param_names, param_values))
                result = dict(zip(
                    ['param', 'handler_func'],
                    [param, search_node.route_handler[method]]
                ))
                return result
        return None











