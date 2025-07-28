"""
Roam Research MCP Server
Provides tools to interact with Roam Research API
"""

import os
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("roam-research")


class RoamResearchMCPServer:
    def __init__(self, token: str, graph_name: str):
        self.token = token
        self.graph_name = graph_name
        self.base_url = "https://api.roamresearch.com"
        self.headers = {
            "X-Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
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
            print(f"Request failed: {e}", file=sys.stderr)
            raise

    def _convert_block_to_markdown(self, block: Dict[str, Any]) -> str:
        """Convert a Roam block to markdown format"""
        content = block.get(':block/string', '')

        # Convert Roam-style links [[page]] to markdown links
        content = re.sub(r'\[\[([^\]]+)\]\]', r'[\1](\1)', content)

        return content


    def _build_block_with_children(self, block: Dict[str, Any]) -> str:
        """Build a markdown string with block content and all its children"""
        content = self._convert_block_to_markdown(block)

        # Get children from the nested data structure
        children = block.get(':block/children', [])
        if children:
            content += "\n"
            for child in children:
                child_content = self._build_block_with_children(child)
                # Indent child content
                child_lines = child_content.split('\n')
                indented_lines = ['  ' + line for line in child_lines if line.strip()]
                content += '\n'.join(indented_lines) + '\n'

        return content.strip()

    def get_page_content(self, page_name: str) -> Dict[str, Any]:
        """Get content of a specific page with child blocks"""
        # Query to get all blocks on the page with nested children
        query = """[:find (pull ?block [:block/string
                                       :block/uid
                                       :edit/time
                                       :block/order
                                       {:block/children [:block/string
                                                         :block/uid
                                                         :edit/time
                                                         {:block/children [:block/string
                                                                           :block/uid
                                                                           :edit/time
                                                                           {:block/children [:block/string
                                                                                             :block/uid
                                                                                             :edit/time
                                                                                             {:block/children [:block/string
                                                                                                               :block/uid
                                                                                                               :edit/time]}]}]}]}]) ?time
                    :in $ ?PAGE
                    :where
                    [?page :node/title ?PAGE]
                    [?block :block/page ?page]
                    [?block :edit/time ?time]
                    ]"""

        data = {"query": query, "args": [page_name]}
        endpoint = f"/api/graph/{self.graph_name}/q"
        raw_result = self._make_request("POST", endpoint, data)
        
        # Sort by time (descending) 
        results = raw_result.get("result", [])
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
        
        # Transform the result to only include markdown content with children
        simplified_result = []
        for item in sorted_results:
            if item and len(item) > 0:
                block = item[0]
                timestamp = item[1]
                content = self._build_block_with_children(block)
                simplified_result.append({"content": content, "timestamp": timestamp})
        
        return {"result": simplified_result}

    def get_page_references(self, page_name: str, limit: int = 10, cursor: Optional[int] = None) -> Dict[str, Any]:
        """Get references to a specific page with markdown content and child blocks"""
        # Build the query with time-based sorting and pagination
        if cursor:
            # Use cursor-based pagination for subsequent pages
            query = """[:find (pull ?ref [:block/string
                                          :block/uid
                                          :edit/time
                                          {:block/children [:block/string
                                                            :block/uid
                                                            :edit/time
                                                            {:block/children [:block/string
                                                                              :block/uid
                                                                              :edit/time
                                                                              {:block/children [:block/string
                                                                                                :block/uid
                                                                                                :edit/time
                                                                                                {:block/children [:block/string
                                                                                                                  :block/uid
                                                                                                                  :edit/time]}]}]}]}]) ?time
                        :in $ ?PAGE ?cursor-time
                        :where
                        [?page :node/title ?PAGE]
                        [?ref :block/refs ?page]
                        [?ref :edit/time ?time]
                        [(< ?time ?cursor-time)]
                        ]"""
            data = {"query": query, "args": [page_name, cursor]}
        else:
            # First page - no cursor
            query = """[:find (pull ?ref [:block/string
                                          :block/uid
                                          :edit/time
                                          {:block/children [:block/string
                                                            :block/uid
                                                            :edit/time
                                                            {:block/children [:block/string
                                                                              :block/uid
                                                                              :edit/time
                                                                              {:block/children [:block/string
                                                                                                :block/uid
                                                                                                :edit/time
                                                                                                {:block/children [:block/string
                                                                                                                  :block/uid
                                                                                                                  :edit/time]}]}]}]}]) ?time
                        :in $ ?PAGE
                        :where
                        [?page :node/title ?PAGE]
                        [?ref :block/refs ?page]
                        [?ref :edit/time ?time]
                        ]"""
            data = {"query": query, "args": [page_name]}

        endpoint = f"/api/graph/{self.graph_name}/q"
        raw_result = self._make_request("POST", endpoint, data)

        # Sort by time (descending) and apply limit
        results = raw_result.get("result", [])
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
        limited_results = sorted_results[:limit]

        # Transform the result to only include markdown content with children
        simplified_result = []
        next_cursor = None

        for item in limited_results:
            if item and len(item) > 0:
                block = item[0]
                timestamp = item[1]
                content = self._build_block_with_children(block)
                simplified_result.append({"content": content, "timestamp": timestamp})
                next_cursor = timestamp

        result = {"result": simplified_result}

        # Add next_cursor if there are more results
        if len(results) > limit:
            result["next_cursor"] = next_cursor

        return result

    def write_to_page(self, page_name: str, content: str) -> Dict[str, Any]:
        """Write hierarchical content to a specific page"""
        # First, get the page UID
        page_query = f"""[:find ?uid
                         :in $ ?PAGE
                         :where
                         [?e :node/title ?PAGE]
                         [?e :block/uid ?uid]
                         ]"""

        query_data = {"query": page_query, "args": [page_name]}

        endpoint = f"/api/graph/{self.graph_name}/q"
        page_result = self._make_request("POST", endpoint, query_data)

        # Get page UID
        if not page_result.get("result") or not page_result["result"]:
            raise ValueError(f"Page '{page_name}' not found")

        page_uid = page_result["result"][0][0]

        # Parse markdown content into hierarchical blocks
        blocks = self._parse_markdown_to_blocks(content)
        
        # Create the hierarchical structure
        results = self._create_block_hierarchy(page_uid, blocks)
        
        return {"result": "success", "blocks_created": len(results), "details": results}

    def _parse_markdown_to_blocks(self, content: str) -> list:
        """Parse markdown content into hierarchical block structure using dynamic indentation detection"""
        lines = [line.rstrip() for line in content.split('\n') if line.strip()]
        
        # Build indentation level mapping
        indent_map = {}  # {actual_indent: level}
        blocks = []
        stack = []  # Stack to track parent blocks at different levels
        
        for i, line in enumerate(lines):
            actual_indent = len(line) - len(line.lstrip())
            
            # Determine the level for this indentation
            if actual_indent not in indent_map:
                if actual_indent == 0:
                    indent_map[actual_indent] = 0
                else:
                    # Find the closest parent indentation level
                    parent_indents = [k for k in indent_map.keys() if k < actual_indent]
                    if parent_indents:
                        parent_indent = max(parent_indents)
                        indent_map[actual_indent] = indent_map[parent_indent] + 1
                    else:
                        indent_map[actual_indent] = 1
            
            level = indent_map[actual_indent]
            
            # Extract content (remove leading "- " if present)
            text = line.strip()
            if text.startswith('- '):
                text = text[2:]
            
            # Create block structure
            block = {
                "string": text,
                "uid": f"{datetime.now().strftime('%m-%d-%Y')}-{datetime.now().strftime('%H%M%S')}-{i}",
                "children": []
            }
            
            # Adjust stack to current level
            while len(stack) > level:
                stack.pop()
            
            if level == 0:
                # Top-level block
                blocks.append(block)
                stack = [block]
            else:
                # Child block - add to the parent at the appropriate level
                if stack and len(stack) >= level:
                    parent = stack[level - 1]
                    parent["children"].append(block)
                    # Extend stack to current level
                    while len(stack) <= level:
                        stack.append(block)
                    stack[level] = block
                else:
                    # Fallback: treat as top-level if stack is insufficient
                    blocks.append(block)
                    stack = [block]
        
        return blocks

    def _create_block_hierarchy(self, parent_uid: str, blocks: list) -> list:
        """Recursively create blocks with their children"""
        results = []
        
        for block in blocks:
            # Create the main block
            block_data = {
                "action": "create-block",
                "location": {"parent-uid": parent_uid, "order": "last"},
                "block": {
                    "string": block["string"],
                    "uid": block["uid"],
                },
            }
            
            write_endpoint = f"/api/graph/{self.graph_name}/write"
            result = self._make_request("POST", write_endpoint, block_data)
            results.append(result)
            
            # Create children if they exist
            if block["children"]:
                child_results = self._create_block_hierarchy(block["uid"], block["children"])
                results.extend(child_results)
        
        return results

    def write_to_today_page(self, content: str) -> Dict[str, Any]:
        """Write hierarchical content to today's daily page"""
        # Use the standard Roam date format
        today = datetime.now().strftime("%B %d, %Y")
        today_uid = datetime.now().strftime("%m-%d-%Y")

        # Try to get today's page by UID first
        page_query = f'''[:find ?e
                         :where
                         [?e :block/uid "{today_uid}"]
                         ]'''

        query_data = {"query": page_query}

        endpoint = f"/api/graph/{self.graph_name}/q"
        page_result = self._make_request("POST", endpoint, query_data)

        if not page_result.get("result") or not page_result["result"]:
            # Try to create today's page
            create_data = {
                "action": "create-page",
                "page": {"title": today, "uid": today_uid},
            }

            write_endpoint = f"/api/graph/{self.graph_name}/write"
            self._make_request("POST", write_endpoint, create_data)

        # Parse markdown content into hierarchical blocks
        blocks = self._parse_markdown_to_blocks(content)
        
        # Create the hierarchical structure
        results = self._create_block_hierarchy(today_uid, blocks)
        
        return {"result": "success", "blocks_created": len(results), "details": results}


# Initialize Roam Research client
roam_client = None


def get_roam_client():
    """Get or initialize Roam Research client"""
    global roam_client

    if roam_client is None:
        token = os.getenv("ROAM_TOKEN")
        graph_name = os.getenv("ROAM_GRAPH_NAME")

        print(f"DEBUG: ROAM_TOKEN present: {bool(token)}", file=sys.stderr)
        print(f"DEBUG: ROAM_GRAPH_NAME present: {bool(graph_name)}", file=sys.stderr)

        if not token or not graph_name:
            raise Exception("ROAM_TOKEN and ROAM_GRAPH_NAME environment variables are required")

        roam_client = RoamResearchMCPServer(token, graph_name)
        print("DEBUG: Roam client initialized successfully", file=sys.stderr)

    return roam_client


@mcp.tool()
async def get_page_content(page_name: str) -> str:
    """Get the complete content of a specific page in Roam Research with all nested child blocks.
    
    Retrieves all blocks on the specified page with their hierarchical structure,
    including nested children up to 5 levels deep. Returns content in markdown format
    with proper indentation to reflect the block hierarchy.

    Args:
        page_name: Exact name of the page to retrieve (case-sensitive)
        
    Returns:
        JSON string containing:
        - result: Array of blocks with content and timestamps
        - Each block includes: content (markdown), timestamp (edit time)
        
    Examples:
        get_page_content("Daily Notes")
        get_page_content("Project Planning")
        get_page_content("信用卡")
    """
    try:
        client = get_roam_client()
        result = client.get_page_content(page_name)
        return json.dumps(result, indent=2)
    except Exception as e:
        print(f"Error getting page content: {e}", file=sys.stderr)
        return f"Error: {str(e)}"


@mcp.tool()
async def get_page_references(page_name: str, limit: int = 10, cursor: Optional[int] = None) -> str:
    """Get all blocks that reference a specific page in Roam Research with pagination support.
    
    Finds all blocks across your Roam database that contain links to the specified page.
    Results are sorted by most recent edit time and include the full hierarchical context
    of each referencing block.

    Args:
        page_name: Exact name of the page to find references for (case-sensitive)
        limit: Maximum number of references to return per request (default: 10)
        cursor: Timestamp cursor for pagination - use next_cursor from previous response
               to get additional results
               
    Returns:
        JSON string containing:
        - result: Array of referencing blocks with content and timestamps  
        - next_cursor: Timestamp for pagination (if more results available)
        - total_matches: Number of references found in this batch
        
    Examples:
        get_page_references("GTD")
        get_page_references("Project Alpha", limit=20)
        get_page_references("Meeting Notes", limit=5, cursor=1640995200000)
    """
    try:
        client = get_roam_client()
        result = client.get_page_references(page_name, limit, cursor)
        return json.dumps(result, indent=2)
    except Exception as e:
        print(f"Error getting page references: {e}", file=sys.stderr)
        return f"Error: {str(e)}"


@mcp.tool()
async def write_to_page(page_name: str, content: str) -> str:
    """Write hierarchical markdown content to a specific page in Roam Research.
    
    Creates a new block structure on the specified page with automatic indentation
    detection. Supports nested bullet points and maintains proper parent-child
    relationships between blocks. Content is appended to the end of the page.

    Args:
        page_name: Exact name of the target page (case-sensitive, must exist)
        content: Hierarchical markdown content using '- ' prefix and indentation
                Format: "- Main topic\n    - Subtopic\n        - Details"
                Supports any indentation level with automatic detection
                
    Returns:
        JSON string containing:
        - result: "success" if completed
        - blocks_created: Total number of blocks created (including children)
        - details: Array of individual block creation results
        
    Examples:
        write_to_page("Project Notes", "- New milestone\n    - Task 1\n    - Task 2")
        write_to_page("信用卡", "- [[銀行/國泰]]\n    - 現金回饋 2%")
    """
    try:
        client = get_roam_client()
        result = client.write_to_page(page_name, content)
        return f"Successfully wrote to page '{page_name}': {json.dumps(result, indent=2)}"
    except Exception as e:
        print(f"Error writing to page: {e}", file=sys.stderr)
        return f"Error: {str(e)}"


@mcp.tool()
async def write_to_today(content: str) -> str:
    """Write hierarchical markdown content to today's daily page in Roam Research.
    
    Automatically creates today's daily page if it doesn't exist, then adds the
    provided content as a hierarchical block structure. Uses Roam's standard
    date format (e.g., "July 28, 2025") and maintains proper block relationships.

    Args:
        content: Hierarchical markdown content using '- ' prefix and indentation
                Format: "- Main topic\n    - Subtopic\n        - Details"
                Supports any indentation level with automatic detection
                
    Returns:
        JSON string containing:
        - result: "success" if completed
        - blocks_created: Total number of blocks created (including children) 
        - details: Array of individual block creation results
        
    Examples:
        write_to_today("- Daily standup\n    - Completed: Bug fixes\n    - Next: Feature review")
        write_to_today("- [[會議/週會]]\n    - 參與者: @John, @Mary\n    - 議題: Q4 規劃")
    """
    try:
        client = get_roam_client()
        result = client.write_to_today_page(content)
        return f"Successfully wrote to today's page: {json.dumps(result, indent=2)}"
    except Exception as e:
        print(f"Error writing to today's page: {e}", file=sys.stderr)
        return f"Error: {str(e)}"


if __name__ == "__main__":
    print("DEBUG: Starting FastMCP server", file=sys.stderr)
    mcp.run(transport='stdio')
