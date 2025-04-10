import asyncio
import json
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI()

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport

        Args:
            server_url: the server url
        """
        
        sse_transport = await self.exit_stack.enter_async_context(sse_client(url=server_url, timeout=30.0))
        self.sse_reader, self.sse_writer = sse_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.sse_reader, self.sse_writer))

        # Initialize
        await self.session.initialize()

        # List available tools to verify connection
        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query,
            }
        ]
        
        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
        } for tool in response.tools]
        
        # Initial OpenAI API call
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            max_tokens=1000,
        )
        
        # Process response and handle tool calls
        final_text = []
        assistant_message_content = []
        message = response.choices[0].message
        
        # handling text response
        if message.content:
            final_text.append(message.content)
            assistant_message_content.append({
                "type": "text",
                "text": message.content
            })
        # handling tool calls
        elif message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                # openai는 string 형식으로 들어온다
                tool_args = json.loads(tool_call.function.arguments)
                tool_call_id = tool_call.id
                
                # excute tool call
                result = await self.session.call_tool(
                    tool_name, 
                    tool_args,
                )
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                # append content
                assistant_message_content.append({
                    "type": "function",
                    "id": tool_call_id,
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args), 
                    },
                })
                
                messages.append({
                    "role": "assistant",
                    "tool_calls": assistant_message_content,
                })
                
                # add tool response messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result.content,
                })
                
                # get next response from chat gpt
                new_response = self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=available_tools,
                    tool_choice="auto",
                    max_tokens=1000,
                )
                
                # append next message text
                new_message = new_response.choices[0].message
                if new_message.content:
                    final_text.append(new_message.content)
        
        return "\n".join(final_text)
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\n Query: ").strip()
                
                if query.lower() == "quit":
                    break
                
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <URL of SSE MCP server (i.e. http://localhost:8000/sse)>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())

