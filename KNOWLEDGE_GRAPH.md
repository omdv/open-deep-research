# Knowledge Graph Integration

This document explains the optional knowledge graph integration using Neo4j for storing and retrieving research insights.

## Overview

The system uses a **Sources, Claims, and Concepts** model to build a knowledge graph that captures:

- **Sources**: Where information comes from (articles, papers, websites, etc.)
- **Claims**: Factual statements extracted from sources 
- **Concepts**: Named entities, topics, technologies, organizations, etc.
- **AgentRuns**: Metadata about research sessions

## Schema Design

### Node Types
- `Source` (with subtypes: Article, ResearchPaper, Website, Video, Document)
- `Claim` - Individual verifiable statements
- `Concept` (with subtypes: Person, Organization, Topic, Technology, Location, Event)  
- `AgentRun` - Research session metadata

### Relationships
- `(Claim)-[:EXTRACTED_FROM]->(Source)` - Claims come from sources
- `(Claim)-[:MENTIONS]->(Concept)` - Claims reference concepts
- `(AgentRun)-[:GENERATED]->(Claim)` - Research sessions produce claims
- `(Claim)-[:SUPPORTS|CONTRADICTS]->(Claim)` - Claims can support or contradict each other

## Configuration

Add Neo4j configuration to enable knowledge graph storage:

```python
# In your configuration
neo4j_config = Neo4jConfig(
    enabled=True,
    uri="bolt://localhost:7687",  # Neo4j connection URI
    username="neo4j",
    password="your-password",
    database="neo4j"
)
```

## How It Works

### 1. Automatic Integration
When enabled, the research supervisor can use the `ExtractKnowledge` tool to:
- Extract key claims and concepts from research findings using LLM
- Normalize concepts to prevent duplicates (e.g., "AI" and "Artificial Intelligence")
- Store everything in the Neo4j knowledge graph with proper relationships

### 2. LLM-Powered Extraction
The system uses the research model to:
- **Extract Claims**: Identify factual statements worth preserving
- **Extract Concepts**: Find important entities, topics, technologies, etc.
- **Normalize Concepts**: Use LLM to determine if new concepts should merge with existing ones

### 3. Supervisor Workflow
The research supervisor can:
```
1. Conduct research using ConductResearch tool
2. Use ExtractKnowledge tool to capture important findings
3. Continue research or complete with ResearchComplete
```

## Example Usage

```python
# The supervisor might call:
ExtractKnowledge(
    research_content="GPT-4 achieved 90% accuracy on benchmark tests. OpenAI reported significant improvements in reasoning capabilities.",
    research_context="AI model performance comparison"
)
```

This would create:
- **Source**: Document about AI model performance  
- **Claims**: 
  - "GPT-4 achieved 90% accuracy on benchmark tests" 
  - "OpenAI reported significant improvements in reasoning capabilities"
- **Concepts**: 
  - GPT-4 (Technology)
  - OpenAI (Organization)
  - Benchmark Tests (Topic)

## Benefits

### 1. Knowledge Accumulation
- Build institutional memory across research sessions
- Avoid re-researching the same topics
- Connect related findings from different sessions

### 2. Concept Normalization  
- LLM prevents duplicate concepts (e.g., merges "AI", "Artificial Intelligence", "A.I.")
- Maintains clean, queryable knowledge graph
- Preserves semantic relationships

### 3. Fact Verification
- Track contradictory claims from different sources
- Maintain provenance for fact-checking
- Build evidence networks for complex topics

## Querying the Knowledge Graph

You can query the Neo4j database directly:

```cypher
// Find all claims about a specific concept
MATCH (c:Claim)-[:MENTIONS]->(con:Concept {name: "Artificial Intelligence"})
RETURN c.text, c.confidence_score

// Find related research sessions
MATCH (ar:AgentRun)-[:GENERATED]->(c:Claim)-[:MENTIONS]->(con:Concept)
WHERE con.name CONTAINS "AI"
RETURN ar.initial_query, count(c) as claim_count

// Find contradictory claims
MATCH (c1:Claim)-[:CONTRADICTS]->(c2:Claim)
RETURN c1.text, c2.text
```

## Setup Requirements

1. **Neo4j Database**: Running Neo4j instance (local or cloud)
2. **Configuration**: Enable `neo4j_config.enabled = True` 
3. **Dependencies**: The `neo4j>=5.28.2` package is included
4. **Network**: Ensure Neo4j is accessible from your application

## Future Enhancements

- **Semantic Search**: Use embeddings to find conceptually similar claims
- **Entity Resolution**: More sophisticated concept merging using embeddings
- **Claim Verification**: Automatic detection of supporting/contradicting claims
- **Knowledge Retrieval**: Use graph context to inform future research sessions