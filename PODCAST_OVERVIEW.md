# MCP Graph Engine: A Thinking Tool for AI

## The Problem: AI Has a Memory Problem

When AI assistants like Claude work on complex tasks, they discover information piece by piece. Imagine an AI exploring a large codebase:

First, it finds that the authentication service depends on the user repository. Later, it discovers the user repository talks to a database pool. Even later, it learns the database pool is configured by a config loader. Each discovery happens at different times, in different conversations.

Here's the challenge: the AI has to hold all these relationships in its head, competing with everything else it's thinking about. There's no structured place to put this knowledge. No way to ask questions like "what's the chain of dependencies from the login page to the database?"

This isn't just about code. When an AI researches a topic, it might find that Concept A relates to Concept B, which builds on Concept C, which actually contradicts something mentioned earlier. The web of relationships becomes impossible to reason about.

The core problem is this: AI has excellent pattern recognition and language understanding, but it lacks persistent, queryable structure for the relationships it discovers.

## Current Workarounds Don't Work

Today, AI assistants try to work around this in several ways, and none of them are great.

Some AIs keep notes in text files. But text is hard to query algorithmically. You can't easily ask "what's connected to what?"

Some try to hold a mental model in their context window. But context windows are finite, and this information competes with everything else. When the context gets too long and needs to be summarized, relationship details get lost.

Writing to files just creates storage without any ability to query relationships.

External databases are overkill for this kind of transient thinking work. They require schema design and setup.

## The Solution: A Graph-Based Thinking Tool

This is where the MCP Graph Engine comes in. It's not a database - it's a thinking tool.

A graph is the natural way to represent relationships. Nodes represent entities - things like files, concepts, people, or modules. Edges represent relationships between them - depends-on, relates-to, calls, imports.

What makes graphs powerful is they can answer questions that would be tedious to work out manually:

"What's the shortest path from A to Z?" This reveals dependency chains.

"What are the most connected nodes?" This identifies central concepts that everything else relies on.

"What clusters exist?" This shows natural module boundaries or topic groupings.

"If I remove this component, what becomes disconnected?" This is impact analysis.

The MCP Graph Engine brings these capabilities to AI assistants as a Model Context Protocol server. It lets AI build, query, and analyze relationship graphs during complex tasks.

## Key Design Philosophy

The tool was designed with a specific philosophy: it should be transient, disposable, fast to build, queryable, and able to support multiple AI instances at once.

Transient means graphs live in memory for a session. There's no persistence complexity to worry about.

Disposable means create, use, discard. No schema migrations or cleanup needed.

Fast to build means adding a relationship should be as easy as saying it. The AI shouldn't have to think about data modeling.

Queryable means the AI can ask questions that would be tedious to answer manually.

## The Analysis Toolkit

The real power comes from the analysis tools. These aren't just data storage - they're algorithms that answer questions.

### Finding Paths and Connections

The shortest path tool traces the most direct route between any two nodes. When an AI asks "how does the login page connect to the database?", it gets back the exact chain: LoginController to AuthService to UserRepository to Database. Three hops, clearly laid out.

But sometimes you want to see all the options. The all paths tool finds every possible route between two points. Maybe there are three different ways data flows from the frontend to the backend. Knowing all the paths reveals redundancy, alternative routes, and architectural choices.

### Identifying What Matters Most

PageRank - the algorithm that made Google famous - works beautifully for finding important nodes in any graph. When you run PageRank on a codebase graph, the database module might score highest because everything ultimately depends on it. The authentication service might be second. These rankings tell you where to focus attention.

Degree centrality offers a different lens. It counts direct connections. A node with high in-degree has many things depending on it - it's a hub. A node with high out-degree depends on many things - it might be a coordinator or orchestrator. This reveals communication patterns and coupling issues.

### Finding Structure and Problems

Connected components analysis reveals the natural clusters in your graph. In a codebase, you might discover that the authentication modules form one cluster, the payment modules form another, and there's a utility module sitting off by itself connected to nothing. This shows architectural boundaries - and isolation issues.

Cycle detection is invaluable for codebases. Circular dependencies - where A depends on B which depends on C which depends on A - are often bugs waiting to happen. The cycle detection tool finds all such loops instantly.

Transitive reduction cleans up a graph by removing redundant edges. If A connects to B, and B connects to C, and there's also a direct edge from A to C, that direct edge is often noise. Removing it shows you the essential structure.

### Focused Analysis with Subgraphs

Sometimes a full graph is too much. The subgraph tool extracts just the nodes you care about, along with all the connections between them. You can focus on "just the authentication-related components" and see how they interconnect, without the noise of unrelated modules.

## Real-World Use Cases

Let's look at concrete scenarios where these tools become valuable together.

### Understanding Codebases

When an AI explores a new codebase, it adds nodes for components it discovers - controllers, services, repositories, databases. It adds edges for relationships - imports, calls, instantiates.

The analysis workflow might go like this: First, run PageRank to find the most critical modules. Then use degree centrality to identify hubs and potential coupling issues. Run cycle detection to find any circular dependencies that need attention. Use shortest path to trace how requests flow from entry points to data storage. Finally, use connected components to understand module boundaries.

### Research Synthesis

When an AI researches a technical topic, it can add nodes for papers, concepts, authors, and techniques. Edges represent citations, contradictions, extensions, and authorship.

PageRank identifies foundational papers - the ones that everything else builds on. All paths shows the citation chain between any two papers. Connected components might reveal that there are actually two separate schools of thought that rarely cite each other. Degree centrality finds the authors who are most central to the field.

### Debugging and Root Cause Analysis

When debugging an issue, an AI can add nodes for symptoms, hypotheses, evidence, and code locations. Edges show what supports or contradicts each hypothesis, causal relationships, and locations.

Degree centrality quickly shows which hypothesis has the most supporting evidence pointing to it. Shortest path traces how a bug in one location could propagate to cause symptoms elsewhere. Subgraph extraction lets you focus just on the relevant parts of your debugging graph.

### Architecture Review and Refactoring

Before a major refactoring, the AI can map out the current architecture. Transitive reduction simplifies the dependency graph to show only essential relationships. Cycle detection flags problematic circular dependencies that should be broken. PageRank identifies the highest-impact modules - change these carefully. Connected components shows natural boundaries where you might split services.

## The LLM-Friendly Interface

One of the biggest design challenges was making the interface natural for AI to use.

Traditional graph APIs require tracking identifiers. You add a node, get back an ID like "a1b2c3d4", then have to remember that ID to create edges. This is problematic for AI assistants - they have to track arbitrary ID strings across conversation turns, the IDs compete for context window space, typos cause failures, and IDs have no semantic meaning.

The solution is fuzzy matching on node labels. Instead of IDs, the AI references nodes by their natural names. When the AI says "connect the authentication service to the user repository," the system understands what's meant.

This works through a matching pipeline. First, it tries an exact match. If that fails, it tries normalized matching - case-insensitive, whitespace-normalized. If that still doesn't match, it uses embedding-based semantic similarity to find the closest match.

This means an AI can say "Auth Service" or "the authentication service" or "AuthService" and they'll all match the same node. It's robust to the natural variations in how an AI might refer to something.

When there's ambiguity - say, multiple services that all partially match "service" - the system returns candidates and lets the AI be more specific. It's a collaborative process.

## Named Sessions for Memory Recovery

Another challenge is session management. What happens when an AI's context gets compacted and it loses track of what graphs it was working with?

The solution is named sessions with defaults. For simple cases, everything goes into a "default" graph automatically. No session management needed.

For more complex work, the AI can use memorable names - "codebase" or "research" or "before-refactor" and "after-refactor" for comparison work.

If the AI ever forgets what graphs exist, it can just ask. The list_graphs command returns all active graphs with their statistics. This makes the system recoverable even after context loss.

## The Technology Under the Hood

The engine is built on NetworkX, a well-established Python graph library. NetworkX provides excellent implementations of shortest path algorithms, PageRank, connected components, cycle detection, transitive reduction, and many other graph algorithms.

For semantic matching, the system uses a small local embedding model - all-MiniLM-L6-v2. It's about 80 megabytes, produces 384-dimensional embeddings, and runs fast even on CPU. It runs entirely locally with no API calls needed.

Embeddings are computed once per node label and cached for the session. This makes repeated fuzzy lookups fast.

## Import and Export

AI assistants often know standard graph formats. The engine supports importing and exporting DOT format from GraphViz, CSV edge lists, JSON, and GraphML.

This means an AI can generate a DOT file from its understanding of relationships and import the entire structure in one call. Or export a graph for visualization with GraphViz.

## What This Enables

The MCP Graph Engine fundamentally changes what's possible for AI assistants working on complex tasks.

Instead of losing track of relationships as context grows, the AI has a structured place to record discoveries. Instead of manually tracing dependency chains, the AI can query for paths algorithmically. Instead of guessing at which components are most important, the AI can compute centrality measures.

It's a thinking tool that extends AI capabilities - giving them the kind of structured memory and algorithmic query power that makes complex reasoning tasks tractable.

The design prioritizes being natural for AI to use over raw features. Every decision asks: "Will this be natural for an AI assistant to work with?" The result is a tool that fits seamlessly into how AI already thinks and works, while giving it powerful new capabilities for understanding and reasoning about relationships.
