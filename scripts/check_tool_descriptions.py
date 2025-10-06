#!/usr/bin/env python3
"""Script to verify that MCP tool descriptions are properly exposed."""

from keep_mcp.fastmcp_server import create_fastmcp


def main():
    """Check that all tools have detailed descriptions."""
    mcp_server = create_fastmcp()
    
    print("Checking MCP tool descriptions...\n")
    print("=" * 80)
    
    # Access the tools from the FastMCP server
    tools = [
        "memory_add_card",
        "memory_recall", 
        "memory_manage",
        "memory_export"
    ]
    
    for tool_name in tools:
        # Get the tool function
        tool_func = getattr(mcp_server, f"_{tool_name}", None)
        if tool_func is None:
            # Try accessing from _tools dict if available
            print(f"\n❌ Tool '{tool_name}' not found")
            continue
            
        # Check for docstring or description
        description = getattr(tool_func, "__doc__", None) or "No description"
        
        print(f"\n📋 Tool: {tool_name}")
        print("-" * 80)
        if len(description) > 100:
            print(f"✅ Description length: {len(description)} chars")
            print(f"Preview: {description[:200]}...")
        else:
            print(f"⚠️  Short or missing description: {description}")
    
    print("\n" + "=" * 80)
    print("✅ All tool descriptions checked!")


if __name__ == "__main__":
    main()
