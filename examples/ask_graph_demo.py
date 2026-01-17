#!/usr/bin/env python3
"""
Demo of the ask_graph natural language query feature.

This demonstrates how LLMs can interact with the graph using natural queries
instead of remembering specific tool names.
"""

import asyncio
import json
from mcp_graph_engine.server import GraphServer


async def demo():
    """Run ask_graph demo."""
    server = GraphServer()

    # First, create a sample dependency graph
    print("Setting up a sample codebase dependency graph...\n")

    knowledge = """
# Authentication layer
LoginController uses AuthService
AuthService depends_on UserRepository
AuthService depends_on SessionManager

# Data layer
UserRepository depends_on DatabasePool
SessionManager depends_on RedisClient

# Infrastructure
ConfigLoader configures DatabasePool
ConfigLoader configures RedisClient
DatabasePool depends_on ConnectionFactory

# API layer
APIGateway routes_to LoginController
APIGateway routes_to UserController
UserController uses UserRepository

# Create a cycle for demo
CycleA depends_on CycleB
CycleB depends_on CycleC
CycleC depends_on CycleA
"""

    await server._handle_tool("add_knowledge", {"knowledge": knowledge})

    print("Graph created! Now let's ask natural language questions...\n")
    print("=" * 70)

    # Demo various query types
    queries = [
        "what depends on DatabasePool",
        "what does AuthService depend on",
        "dependencies of LoginController",
        "path from APIGateway to DatabasePool",
        "cycles",
        "most connected",
        "orphans",
        "components",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 70)
        result = await server._handle_tool("ask_graph", {"query": query})
        print(f"Result:\n{result['result']}\n")

    # Demo unrecognized query fallback
    print("\n" + "=" * 70)
    print("\nUnrecognized Query: 'show me everything'")
    print("-" * 70)
    result = await server._handle_tool("ask_graph", {"query": "show me everything"})
    if "help" in result:
        print(f"Error: {result['error']}")
        print(f"\n{result['help']}")


if __name__ == "__main__":
    asyncio.run(demo())
