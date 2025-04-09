# https://platform.openai.com/docs/libraries?language=python
# https://modelcontextprotocol.io/quickstart/client
import asyncio
import json

from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI()
    
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
        
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        # in python, context is critical section like OS that manages System resource safely 
        # the context manager code implemented python function is good to dynamic resource management
        # similar to socket generation
        # like generating socket
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        # get write stream, read stream
        self.stdio, self.write = stdio_transport
        # get high level session with streams
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
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
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
    
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()
        
if __name__ == "__main__":
    import sys
    asyncio.run(main())
    # What are the weather alerts in California