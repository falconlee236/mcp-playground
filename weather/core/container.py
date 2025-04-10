# core/container.py
import importlib
import pkgutil
from mcp.server.fastmcp import FastMCP

class Container:
    mcp = FastMCP("weather")
    _is_tools_registered = False

    @staticmethod
    def _register_tools():
        import tools  # tools는 반드시 패키지여야 함 (즉, __init__.py 필요)
        package_path = tools.__path__

        for _, module_name, _ in pkgutil.iter_modules(package_path):
            importlib.import_module(f"tools.{module_name}")

    @classmethod
    def get_mcp(cls) -> FastMCP:
        if not cls._is_tools_registered:
            cls._register_tools()  # MCP 툴 자동 등록
            cls._is_tools_registered = True
        return cls.mcp