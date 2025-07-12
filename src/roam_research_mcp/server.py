"""
Roam Research MCP Server
Provides tools to interact with Roam Research API
"""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    CallToolRequest,
    CallToolResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    ReadResourceRequest,
    ReadResourceResult,
)
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoamResearchMCPServer:
    def __init__(self, token: str, graph_name: str):
        self.token = token
        self.graph_name = graph_name
        self.base_url = "https://api.roamresearch.com"
        self.headers = {
            "X-Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Roam Research API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle empty response for write operations
            if response.text.strip() == "":
                return {"result": "success", "status": response.status_code}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def get_page_content(self, page_name: str) -> Dict[str, Any]:
        """Get content of a specific page"""
        query = f'''[:find (pull ?e [*])
                    :in $ ?PAGE
                    :where
                    [?e :node/title ?PAGE]
                    ]'''
        
        data = {
            "query": query,
            "args": [page_name]
        }
        
        endpoint = f"/api/graph/{self.graph_name}/q"
        return self._make_request("POST", endpoint, data)
    
    def get_page_references(self, page_name: str) -> Dict[str, Any]:
        """Get references to a specific page"""
        query = f'''[:find (pull ?ref [*])
                    :in $ ?PAGE
                    :where
                    [?page :node/title ?PAGE]
                    [?ref :block/refs ?page]
                    ]'''
        
        data = {
            "query": query,
            "args": [page_name]
        }
        
        endpoint = f"/api/graph/{self.graph_name}/q"
        return self._make_request("POST", endpoint, data)
    
    def write_to_page(self, page_name: str, content: str) -> Dict[str, Any]:
        """Write content to a specific page"""
        # First, get the page UID
        page_query = f'''[:find ?uid
                         :in $ ?PAGE
                         :where
                         [?e :node/title ?PAGE]
                         [?e :block/uid ?uid]
                         ]'''
        
        query_data = {
            "query": page_query,
            "args": [page_name]
        }
        
        endpoint = f"/api/graph/{self.graph_name}/q"
        page_result = self._make_request("POST", endpoint, query_data)
        
        # Get page UID
        if not page_result.get("result") or not page_result["result"]:
            raise ValueError(f"Page '{page_name}' not found")
        
        page_uid = page_result["result"][0][0]
        
        # Create block data
        block_data = {
            "action": "create-block",
            "location": {
                "parent-uid": page_uid,
                "order": "last"
            },
            "block": {
                "string": content,
                "uid": f"{datetime.now().strftime('%m-%d-%Y')}-{datetime.now().strftime('%H%M%S')}"
            }
        }
        
        write_endpoint = f"/api/graph/{self.graph_name}/write"
        return self._make_request("POST", write_endpoint, block_data)
    
    def write_to_today_page(self, content: str) -> Dict[str, Any]:
        """Write content to today's daily page"""
        # Use the standard Roam date format
        today = datetime.now().strftime("%B %d, %Y")
        today_uid = datetime.now().strftime("%m-%d-%Y")
        
        # Try to get today's page by UID first
        page_query = f'''[:find ?e
                         :where
                         [?e :block/uid "{today_uid}"]
                         ]'''
        
        query_data = {
            "query": page_query
        }
        
        endpoint = f"/api/graph/{self.graph_name}/q"
        page_result = self._make_request("POST", endpoint, query_data)
        
        if not page_result.get("result") or not page_result["result"]:
            # Try to create today's page
            create_data = {
                "action": "create-page",
                "page": {
                    "title": today,
                    "uid": today_uid
                }
            }
            
            write_endpoint = f"/api/graph/{self.graph_name}/write"
            self._make_request("POST", write_endpoint, create_data)
        
        # Now write the content using the UID
        block_data = {
            "action": "create-block",
            "location": {
                "parent-uid": today_uid,
                "order": "last"
            },
            "block": {
                "string": content,
                "uid": f"{datetime.now().strftime('%m-%d-%Y')}-{datetime.now().strftime('%H%M%S')}"
            }
        }
        
        write_endpoint = f"/api/graph/{self.graph_name}/write"
        return self._make_request("POST", write_endpoint, block_data)

# Create MCP server
server = Server("roam-research-mcp")

# Initialize Roam Research client
roam_client = None

def initialize_roam_client():
    """Initialize Roam Research client with environment variables"""
    global roam_client
    
    token = os.getenv("ROAM_TOKEN")
    graph_name = os.getenv("ROAM_GRAPH_NAME")
    
    if not token or not graph_name:
        logger.error("ROAM_TOKEN and ROAM_GRAPH_NAME environment variables are required")
        return False
    
    roam_client = RoamResearchMCPServer(token, graph_name)
    return True

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_page_content",
            description="Get the content of a specific page in Roam Research",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_name": {
                        "type": "string",
                        "description": "Name of the page to retrieve"
                    }
                },
                "required": ["page_name"]
            }
        ),
        Tool(
            name="get_page_references",
            description="Get references to a specific page in Roam Research",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_name": {
                        "type": "string",
                        "description": "Name of the page to get references for"
                    }
                },
                "required": ["page_name"]
            }
        ),
        Tool(
            name="write_to_page",
            description="Write content to a specific page in Roam Research",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_name": {
                        "type": "string",
                        "description": "Name of the page to write to"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write as a new block"
                    }
                },
                "required": ["page_name", "content"]
            }
        ),
        Tool(
            name="write_to_today",
            description="Write content to today's daily page in Roam Research",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to write as a new block"
                    }
                },
                "required": ["content"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    if not roam_client:
        if not initialize_roam_client():
            return CallToolResult(
                content=[TextContent(type="text", text="Error: Roam Research client not initialized. Please set ROAM_TOKEN and ROAM_GRAPH_NAME environment variables.")]
            )
    
    try:
        if name == "get_page_content":
            result = roam_client.get_page_content(arguments["page_name"])
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )
        
        elif name == "get_page_references":
            result = roam_client.get_page_references(arguments["page_name"])
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )
        
        elif name == "write_to_page":
            result = roam_client.write_to_page(arguments["page_name"], arguments["content"])
            return CallToolResult(
                content=[TextContent(type="text", text=f"Successfully wrote to page '{arguments['page_name']}': {json.dumps(result, indent=2)}")]
            )
        
        elif name == "write_to_today":
            result = roam_client.write_to_today_page(arguments["content"])
            return CallToolResult(
                content=[TextContent(type="text", text=f"Successfully wrote to today's page: {json.dumps(result, indent=2)}")]
            )
        
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")]
        )

def main():
    """Main entry point"""
    import asyncio
    from mcp.server.stdio import stdio_server
    
    # Initialize client
    if not initialize_roam_client():
        logger.error("Failed to initialize Roam Research client")
        return
    
    # Run server
    async def run_server():
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], {})
    
    asyncio.run(run_server())

if __name__ == "__main__":
    main()