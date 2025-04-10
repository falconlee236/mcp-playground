from core.container import Container

if __name__ == "__main__":
    Container.get_mcp().run(transport="sse")