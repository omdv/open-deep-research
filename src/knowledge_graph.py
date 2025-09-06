"""Neo4j knowledge graph utilities for storing research results using Sources, Claims, and Concepts model."""

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from neo4j import Driver, GraphDatabase
from open_deep_research.configuration import Neo4jConfig
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SourceType(Enum):
  """Types of sources for information."""

  ARTICLE = "Article"
  RESEARCH_PAPER = "ResearchPaper"
  WEBSITE = "Website"
  VIDEO = "Video"
  DOCUMENT = "Document"
  API = "API"


class ConceptType(Enum):
  """Types of concepts that can be extracted."""

  PERSON = "Person"
  ORGANIZATION = "Organization"
  TOPIC = "Topic"
  TECHNOLOGY = "Technology"
  LOCATION = "Location"
  EVENT = "Event"


class Source(BaseModel):
  """Represents a source of information in the knowledge graph."""

  id: str
  url: Optional[str] = None
  title: str
  author: Optional[str] = None
  publication_date: Optional[datetime] = None
  source_type: SourceType = SourceType.WEBSITE
  metadata: Optional[Dict[str, Any]] = None


class Claim(BaseModel):
  """Represents an individual, verifiable statement extracted from a source."""

  id: str
  text: str  # Concise summary of the claim
  quote: Optional[str] = None  # Direct text from source
  confidence_score: float = 0.8  # Agent's confidence in extraction
  timestamp: datetime
  source_id: str


class Concept(BaseModel):
  """Represents a normalized entity or abstract topic."""

  id: str
  name: str  # Canonical name
  concept_type: ConceptType
  aliases: List[str] = []  # Alternative names
  description: Optional[str] = None


class AgentRun(BaseModel):
  """Represents a research session/run by the agent."""

  id: str
  initial_query: str
  timestamp: datetime
  agent_version: str = "open_deep_research_v1"
  status: str = "completed"
  metadata: Optional[Dict[str, Any]] = None


class Neo4jKnowledgeGraph:
  """Neo4j client for managing research knowledge graph using Sources, Claims, and Concepts model."""

  def __init__(self, config: Neo4jConfig):
    """Initialize Neo4j connection."""
    self.config = config
    self.driver: Optional[Driver] = None

  async def connect(self) -> bool:
    """Connect to Neo4j database."""
    try:
      self.driver = GraphDatabase.driver(
        self.config.uri, auth=(self.config.username, self.config.password),
      )
      # Test the connection
      with self.driver.session(database=self.config.database) as session:
        session.run("RETURN 1")
      logger.info("Successfully connected to Neo4j database")
      return True
    except Exception as e:
      logger.error(f"Failed to connect to Neo4j: {e}")
      return False

  async def close(self):
    """Close Neo4j connection."""
    if self.driver:
      self.driver.close()
      logger.info("Neo4j connection closed")

  async def create_indexes(self):
    """Create necessary indexes for performance."""
    if not self.driver:
      return

    with self.driver.session(database=self.config.database) as session:
      # Create indexes for the Sources, Claims, and Concepts schema
      queries = [
        # Source indexes
        "CREATE INDEX source_id_index IF NOT EXISTS FOR (s:Source) ON (s.id)",
        "CREATE INDEX source_url_index IF NOT EXISTS FOR (s:Source) ON (s.url)",
        # Claim indexes
        "CREATE INDEX claim_id_index IF NOT EXISTS FOR (c:Claim) ON (c.id)",
        "CREATE INDEX claim_source_id_index IF NOT EXISTS FOR (c:Claim) ON (c.source_id)",
        "CREATE INDEX claim_timestamp_index IF NOT EXISTS FOR (c:Claim) ON (c.timestamp)",
        # Concept indexes
        "CREATE INDEX concept_id_index IF NOT EXISTS FOR (con:Concept) ON (con.id)",
        "CREATE INDEX concept_name_index IF NOT EXISTS FOR (con:Concept) ON (con.name)",
        "CREATE TEXT INDEX concept_aliases_index IF NOT EXISTS FOR (con:Concept) ON (con.aliases)",
        # AgentRun indexes
        "CREATE INDEX agent_run_id_index IF NOT EXISTS FOR (ar:AgentRun) ON (ar.id)",
        "CREATE INDEX agent_run_timestamp_index IF NOT EXISTS FOR (ar:AgentRun) ON (ar.timestamp)",
      ]

      for query in queries:
        try:
          session.run(query)
        except Exception as e:
          logger.warning(f"Index creation warning: {e}")

  async def store_agent_run(self, agent_run: AgentRun) -> bool:
    """Store an agent run node."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return False

    try:
      with self.driver.session(database=self.config.database) as session:
        query = """
                MERGE (ar:AgentRun {id: $id})
                SET ar.initial_query = $initial_query,
                    ar.timestamp = $timestamp,
                    ar.agent_version = $agent_version,
                    ar.status = $status,
                    ar.metadata = $metadata
                RETURN ar
                """

        result = session.run(
          query,
          {
            "id": agent_run.id,
            "initial_query": agent_run.initial_query,
            "timestamp": agent_run.timestamp.isoformat(),
            "agent_version": agent_run.agent_version,
            "status": agent_run.status,
            "metadata": agent_run.metadata or {},
          },
        )

        logger.info(f"Stored agent run: {agent_run.id}")
        return True

    except Exception as e:
      logger.error(f"Failed to store agent run: {e}")
      return False

  async def store_source(self, source: Source) -> bool:
    """Store a source node with appropriate label."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return False

    try:
      with self.driver.session(database=self.config.database) as session:
        # Use dynamic label based on source type
        query = f"""
                MERGE (s:Source:{source.source_type.value} {{id: $id}})
                SET s.url = $url,
                    s.title = $title,
                    s.author = $author,
                    s.publication_date = $publication_date,
                    s.source_type = $source_type,
                    s.metadata = $metadata
                RETURN s
                """

        result = session.run(
          query,
          {
            "id": source.id,
            "url": source.url,
            "title": source.title,
            "author": source.author,
            "publication_date": source.publication_date.isoformat()
            if source.publication_date
            else None,
            "source_type": source.source_type.value,
            "metadata": source.metadata or {},
          },
        )

        logger.info(f"Stored source: {source.id} ({source.source_type.value})")
        return True

    except Exception as e:
      logger.error(f"Failed to store source: {e}")
      return False

  async def store_claim(self, claim: Claim, agent_run_id: str) -> bool:
    """Store a claim node and link it to source and agent run."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return False

    try:
      with self.driver.session(database=self.config.database) as session:
        query = """
                MERGE (c:Claim {id: $id})
                SET c.text = $text,
                    c.quote = $quote,
                    c.confidence_score = $confidence_score,
                    c.timestamp = $timestamp,
                    c.source_id = $source_id
                WITH c
                MATCH (s:Source {id: $source_id})
                MERGE (c)-[:EXTRACTED_FROM]->(s)
                WITH c
                MATCH (ar:AgentRun {id: $agent_run_id})
                MERGE (ar)-[:GENERATED]->(c)
                RETURN c
                """

        result = session.run(
          query,
          {
            "id": claim.id,
            "text": claim.text,
            "quote": claim.quote,
            "confidence_score": claim.confidence_score,
            "timestamp": claim.timestamp.isoformat(),
            "source_id": claim.source_id,
            "agent_run_id": agent_run_id,
          },
        )

        logger.info(f"Stored claim: {claim.id}")
        return True

    except Exception as e:
      logger.error(f"Failed to store claim: {e}")
      return False

  async def store_concept(self, concept: Concept) -> bool:
    """Store a concept node with appropriate label."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return False

    try:
      with self.driver.session(database=self.config.database) as session:
        # Use dynamic label based on concept type
        query = f"""
                MERGE (con:Concept:{concept.concept_type.value} {{name: $name}})
                SET con.id = $id,
                    con.aliases = $aliases,
                    con.description = $description,
                    con.concept_type = $concept_type
                RETURN con
                """

        result = session.run(
          query,
          {
            "id": concept.id,
            "name": concept.name,
            "aliases": concept.aliases,
            "description": concept.description,
            "concept_type": concept.concept_type.value,
          },
        )

        logger.info(f"Stored concept: {concept.name} ({concept.concept_type.value})")
        return True

    except Exception as e:
      logger.error(f"Failed to store concept: {e}")
      return False

  async def link_claim_to_concepts(
    self, claim_id: str, concept_names: List[str],
  ) -> bool:
    """Create MENTIONS relationships between a claim and concepts."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return False

    try:
      with self.driver.session(database=self.config.database) as session:
        query = """
                MATCH (c:Claim {id: $claim_id})
                UNWIND $concept_names as concept_name
                MATCH (con:Concept {name: concept_name})
                MERGE (c)-[:MENTIONS]->(con)
                RETURN COUNT(*) as relationships_created
                """

        result = session.run(
          query, {"claim_id": claim_id, "concept_names": concept_names},
        )

        record = result.single()
        count = record["relationships_created"] if record else 0
        logger.info(f"Created {count} MENTIONS relationships for claim {claim_id}")
        return True

    except Exception as e:
      logger.error(f"Failed to link claim to concepts: {e}")
      return False

  async def link_claims(
    self, claim1_id: str, claim2_id: str, relationship_type: str = "SUPPORTS",
  ) -> bool:
    """Create relationships between claims (SUPPORTS or CONTRADICTS)."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return False

    if relationship_type not in ["SUPPORTS", "CONTRADICTS"]:
      logger.error(f"Invalid relationship type: {relationship_type}")
      return False

    try:
      with self.driver.session(database=self.config.database) as session:
        query = f"""
                MATCH (c1:Claim {{id: $claim1_id}})
                MATCH (c2:Claim {{id: $claim2_id}})
                MERGE (c1)-[:{relationship_type}]->(c2)
                RETURN c1, c2
                """

        result = session.run(query, {"claim1_id": claim1_id, "claim2_id": claim2_id})

        logger.info(
          f"Created {relationship_type} relationship between {claim1_id} and {claim2_id}",
        )
        return True

    except Exception as e:
      logger.error(f"Failed to link claims: {e}")
      return False

  async def find_related_claims(
    self, concept_names: List[str], limit: int = 10,
  ) -> List[Dict[str, Any]]:
    """Find claims that mention any of the given concepts."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return []

    try:
      with self.driver.session(database=self.config.database) as session:
        query = """
                MATCH (c:Claim)-[:MENTIONS]->(con:Concept)
                WHERE con.name IN $concept_names
                OPTIONAL MATCH (c)-[:EXTRACTED_FROM]->(s:Source)
                RETURN DISTINCT c.id as claim_id, c.text as claim_text,
                      c.confidence_score as confidence_score,
                      c.timestamp as timestamp,
                      s.title as source_title, s.url as source_url,
                      COLLECT(DISTINCT con.name) as mentioned_concepts
                ORDER BY c.confidence_score DESC, c.timestamp DESC
                LIMIT $limit
                """

        result = session.run(query, {"concept_names": concept_names, "limit": limit})

        claims = [
          {
            "claim_id": record["claim_id"],
            "claim_text": record["claim_text"],
            "confidence_score": record["confidence_score"],
            "timestamp": record["timestamp"],
            "source_title": record["source_title"],
            "source_url": record["source_url"],
            "mentioned_concepts": record["mentioned_concepts"],
          }
          for record in result
        ]

        logger.info(f"Found {len(claims)} related claims for concepts: {concept_names}")
        return claims

    except Exception as e:
      logger.error(f"Failed to find related claims: {e}")
      return []

  async def get_agent_run_summary(self, agent_run_id: str) -> Optional[Dict[str, Any]]:
    """Get summary of an agent run with all generated claims."""
    if not self.driver:
      logger.error("No Neo4j connection available")
      return None

    try:
      with self.driver.session(database=self.config.database) as session:
        query = """
                MATCH (ar:AgentRun {id: $agent_run_id})
                OPTIONAL MATCH (ar)-[:GENERATED]->(c:Claim)-[:EXTRACTED_FROM]->(s:Source)
                OPTIONAL MATCH (c)-[:MENTIONS]->(con:Concept)
                RETURN ar,
                      COUNT(DISTINCT c) as total_claims,
                      COUNT(DISTINCT s) as total_sources,
                      COUNT(DISTINCT con) as total_concepts,
                      COLLECT(DISTINCT {
                          claim_id: c.id,
                          claim_text: c.text,
                          confidence_score: c.confidence_score,
                          source_title: s.title,
                          concepts: COLLECT(DISTINCT con.name)
                      }) as claims_details
                """

        result = session.run(query, {"agent_run_id": agent_run_id})
        record = result.single()

        if record:
          agent_run = record["ar"]
          return {
            "agent_run": {
              "id": agent_run["id"],
              "initial_query": agent_run["initial_query"],
              "timestamp": agent_run["timestamp"],
              "agent_version": agent_run["agent_version"],
              "status": agent_run["status"],
            },
            "summary": {
              "total_claims": record["total_claims"],
              "total_sources": record["total_sources"],
              "total_concepts": record["total_concepts"],
            },
            "claims": [c for c in record["claims_details"] if c["claim_id"]],
          }

        return None

    except Exception as e:
      logger.error(f"Failed to get agent run summary: {e}")
      return None


async def create_knowledge_graph_client(
  config: Neo4jConfig,
) -> Optional[Neo4jKnowledgeGraph]:
  """Create and initialize a Neo4j knowledge graph client."""
  if not config.enabled:
    logger.info("Neo4j knowledge graph storage is disabled")
    return None

  client = Neo4jKnowledgeGraph(config)
  if await client.connect():
    await client.create_indexes()
    return client
  return None


def generate_id() -> str:
  """Generate a unique ID for nodes."""
  return str(uuid.uuid4())


