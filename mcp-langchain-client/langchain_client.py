from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
model = ChatOpenAI(model="gpt-4o")

def extract_final_message_content(result):
    if result and 'messages' in result:
        messages = result['messages']
        return messages[-1].content if hasattr(messages[-1], 'content') else None
    return None

async def main():    
    async with MultiServerMCPClient(
        {
            "weather1": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["weather/main.py"],
                "transport": "stdio",
            },
            "weather2": {
                # make sure you start your weather server on port 8000
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            }
        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        weather_stdio_response = await agent.ainvoke({"messages": "What are the weather alerts in California"})
        weather_sse_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
        print(extract_final_message_content(weather_stdio_response))
        print("---")
        print(extract_final_message_content(weather_sse_response))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())