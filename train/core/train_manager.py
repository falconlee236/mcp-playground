import importlib
import pkgutil

from mcp.server.fastmcp import FastMCP

class TrainManger:
    mcp = FastMCP("Train")
    _is_tools_registered = False
    
    @staticmethod
    def _register_tools():
        import tools
        package_path = tools.__path__
        
        for _, module_name, _ in pkgutil.iter_modules(package_path):
            importlib.import_module(f"tools.{module_name}")
            
    @classmethod
    def get_mcp(cls) -> FastMCP:
        if not cls._is_tools_registered:
            cls._register_tools()
            cls._is_tools_registered = True
        return cls.mcp