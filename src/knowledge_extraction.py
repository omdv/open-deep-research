"""LLM-based knowledge extraction and concept normalization for the research supervisor."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from open_deep_research.configuration import Configuration
from open_deep_research.helpers import get_api_key_for_model
from open_deep_research.knowledge_graph import (
  AgentRun,
  Claim,
  Concept,
  ConceptType,
  Neo4jKnowledgeGraph,
  Source,
  SourceType,
  generate_id,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Structured outputs for LLM-based extraction
class ExtractedClaim(BaseModel):
  """A claim extracted by the LLM from research content."""

  claim_text: str = Field(
    description="A concise, factual statement extracted from the source",
  )
  quote: Optional[str] = Field(
    description="Direct quote from source that supports this claim",
  )
  confidence: float = Field(
    description="Confidence score 0.0-1.0 for this extraction",
    ge=0.0,
    le=1.0,
  )
  key_evidence: str = Field(
    description="Brief explanation of what makes this claim important",
  )


class ExtractedConcept(BaseModel):
  """A concept extracted by the LLM from research content."""

  name: str = Field(description="Canonical name for the concept")
  type: str = Field(
    description="Type: Person, Organization, Topic, Technology, Location, Event",
  )
  description: str = Field(
    description="Brief description of what this concept represents",
  )
  aliases: List[str] = Field(
    description="Alternative names or synonyms for this concept",
    default=[],
  )
  importance: float = Field(
    description="Importance score 0.0-1.0 for this concept",
    ge=0.0,
    le=1.0,
  )


class ConceptNormalization(BaseModel):
  """Result of concept normalization check."""

  is_similar: bool = Field(
    description="Whether the concept is similar to existing ones",
  )
  canonical_name: str = Field(description="The canonical name to use (existing or new)")
  explanation: str = Field(description="Explanation of the normalization decision")


class ResearchExtraction(BaseModel):
  """Complete extraction result from research content."""

  claims: List[ExtractedClaim] = Field(description="Claims extracted from the research")
  concepts: List[ExtractedConcept] = Field(
    description="Concepts extracted from the research",
  )
  key_insights: List[str] = Field(description="High-level insights or conclusions")


class KnowledgeExtractor:
  """LLM-based knowledge extraction service for the research supervisor."""

  def __init__(self, config: Configuration):
    """Initialize the knowledge extractor."""
    self.config = config
    self.model = init_chat_model(
      configurable_fields=("model", "max_tokens", "api_key"),
    )

  async def extract_knowledge_from_research(
    self,
    research_content: str,
    research_topic: str,
    config: RunnableConfig,
  ) -> ResearchExtraction:
    """Extract claims and concepts from research content using LLM."""
    extraction_prompt = f"""You are a research analyst tasked with extracting key claims and concepts from research content.

RESEARCH TOPIC: {research_topic}

RESEARCH CONTENT:
{research_content[:8000]}  # Limit content to avoid token limits

Your task:
1. Extract 3-7 key CLAIMS - factual statements that can be verified
2. Extract 5-12 CONCEPTS - important entities, topics, or ideas mentioned
3. Provide 2-4 high-level INSIGHTS or conclusions

Guidelines for CLAIMS:
- Must be specific and factual
- Should be verifiable from the source material
- Include direct quotes when possible
- Avoid opinions or speculation
- Focus on novel or important information

Guidelines for CONCEPTS:
- Include people, organizations, technologies, topics, locations, events
- Use canonical names (e.g., "Artificial Intelligence" not "AI")
- Provide clear, brief descriptions
- List common aliases or synonyms
- Rate importance based on relevance to research topic

Be precise and focus on quality over quantity."""

    model_config = {
      "model": self.config.research_model,
      "max_tokens": self.config.research_model_max_tokens,
      "api_key": get_api_key_for_model(self.config.research_model, config),
    }

    extraction_model = self.model.with_structured_output(
      ResearchExtraction,
    ).with_config(model_config)

    try:
      result = await extraction_model.ainvoke(
        [
          SystemMessage(
            content="You are an expert research analyst specializing in knowledge extraction.",
          ),
          HumanMessage(content=extraction_prompt),
        ],
      )

      logger.info(
        f"Extracted {len(result.claims)} claims and {len(result.concepts)} concepts",
      )
      return result

    except Exception as e:
      logger.error(f"Failed to extract knowledge: {e}")
      # Return empty result on failure
      return ResearchExtraction(claims=[], concepts=[], key_insights=[])

  async def normalize_concept(
    self,
    new_concept: ExtractedConcept,
    existing_concepts: List[str],
    config: RunnableConfig,
  ) -> ConceptNormalization:
    """Use LLM to determine if a concept should be merged with existing ones."""
    if not existing_concepts:
      return ConceptNormalization(
        is_similar=False,
        canonical_name=new_concept.name,
        explanation="No existing concepts to compare against",
      )

    normalization_prompt = f"""You are tasked with concept normalization in a knowledge graph.

NEW CONCEPT:
Name: {new_concept.name}
Type: {new_concept.type}
Description: {new_concept.description}
Aliases: {new_concept.aliases}

EXISTING CONCEPTS:
{chr(10).join(f"- {concept}" for concept in existing_concepts[:20])}

Task: Determine if the NEW CONCEPT should be merged with any EXISTING CONCEPT.

Consider:
1. Semantic similarity (same entity/topic with different names)
2. Hierarchical relationships (parent/child topics)
3. Aliases and abbreviationsappend
4. Domain-specific terminology

If similar concept found:
- Set is_similar = true
- Use the existing concept name as canonical_name
- Explain the similarity

If no similar concept:
- Set is_similar = false
- Use new concept name as canonical_name
- Explain why it's distinct

Be conservative - only merge if concepts are clappendearly the same entity or very closely related."""

    model_config = {
      "model": self.config.research_model,
      "max_tokens": 1000,
      "api_key": get_api_key_for_model(self.config.research_model, config),
    }

    normalization_model = self.model.with_structured_output(
      ConceptNormalization,
    ).with_config(model_config)

    try:
      result = await normalization_model.ainvoke(
        [
          SystemMessage(
            content="You are an expert in knowledge graph concept normalization.",
          ),
          HumanMessage(content=normalization_prompt),
        ],
      )

      return result

    except Exception as e:
      logger.error(f"Failed to normalize concept: {e}")
      # Default to not merging on error
      return ConceptNormalization(
        is_similar=False,
        canonical_name=new_concept.name,
        explanation=f"Error during normalization: {e}",
      )


class KnowledgeGraphIntegrator:
  """Integrates extracted knowledge with the Neo4j knowledge graph."""

  def __init__(
    self,
    kg_client: Optional[Neo4jKnowledgeGraph],
    extractor: KnowledgeExtractor,
  ):
    """Initialize the knowledge graph integrator."""
    self.kg_client = kg_client
    self.extractor = extractor
    self.current_agent_run_id: Optional[str] = None
    self.concept_cache: Dict[str, str] = {}  # concept_name -> canonical_name

  async def initialize_research_session(
    self,
    initial_query: str,
    research_brief: str,
  ) -> Optional[str]:
    """Initialize a new research session in the knowledge graph."""
    if not self.kg_client:
      return None

    try:
      agent_run = AgentRun(
        id=generate_id(),
        initial_query=initial_query,
        timestamp=datetime.now(),
        metadata={"research_brief": research_brief},
      )

      success = await self.kg_client.store_agent_run(agent_run)
      if success:
        self.current_agent_run_id = agent_run.id
        # Load existing concepts for normalization
        await self._load_concept_cache()
        logger.info(f"Initialized knowledge graph session: {agent_run.id}")
        return agent_run.id

    except Exception as e:
      logger.error(f"Error initializing knowledge graph session: {e}")

    return None

  async def process_research_results(
    self,
    research_content: str,
    research_topic: str,
    source_metadata: Dict[str, Any],
    config: RunnableConfig,
  ) -> bool:
    """Process research results and store in knowledge graph."""
    if not self.kg_client or not self.current_agent_run_id:
      return False

    try:
      # Extract knowledge using LLM
      extraction = await self.extractor.extract_knowledge_from_research(
        research_content,
        research_topic,
        config,
      )

      # Create source node
      source = Source(
        id=generate_id(),
        url=source_metadata.get("url"),
        title=source_metadata.get("title", research_topic),
        author=source_metadata.get("author"),
        source_type=self._determine_source_type(source_metadata),
        metadata=source_metadata,
      )

      await self.kg_client.store_source(source)

      # Process concepts with normalization
      normalized_concepts = {}
      for concept in extraction.concepts:
        canonical_name = await self._normalize_and_store_concept(concept, config)
        normalized_concepts[concept.name] = canonical_name

      # Process claims and link to concepts
      for claim in extraction.claims:
        claim_node = Claim(
          id=generate_id(),
          text=claim.claim_text,
          quote=claim.quote,
          confidence_score=claim.confidence,
          timestamp=datetime.now(),
          source_id=source.id,
        )

        await self.kg_client.store_claim(claim_node, self.current_agent_run_id)

        # Link claim to relevant concepts
        relevant_concepts = self._find_relevant_concepts(
          claim.claim_text,
          normalized_concepts,
        )
        if relevant_concepts:
          await self.kg_client.link_claim_to_concepts(claim_node.id, relevant_concepts)

      logger.info(
        f"Processed research: {len(extraction.claims)} claims, {len(extraction.concepts)} concepts",
      )
      return True

    except Exception as e:
      logger.error(f"Error processing research results: {e}")
      return False

  async def _normalize_and_store_concept(
    self,
    concept: ExtractedConcept,
    config: RunnableConfig,
  ) -> str:
    """Normalize concept against existing ones and store."""
    if concept.name in self.concept_cache:
      return self.concept_cache[concept.name]

    # Get existing concepts for normalization
    existing_concepts = list(self.concept_cache.keys())

    # Use LLM to check for similar concepts
    normalization = await self.extractor.normalize_concept(
      concept,
      existing_concepts,
      config,
    )

    canonical_name = normalization.canonical_name

    if not normalization.is_similar:
      # Store new concept
      concept_type = self._convert_concept_type(concept.type)
      concept_node = Concept(
        id=generate_id(),
        name=canonical_name,
        concept_type=concept_type,
        aliases=concept.aliases + [concept.name]
        if concept.name != canonical_name
        else concept.aliases,
        description=concept.description,
      )

      await self.kg_client.store_concept(concept_node)

    # Update cache
    self.concept_cache[concept.name] = canonical_name
    logger.info(
      f"Normalized concept '{concept.name}' -> '{canonical_name}' ({normalization.explanation})",
    )

    return canonical_name

  async def _load_concept_cache(self):
    """Load existing concepts for normalization."""
    # This would query existing concepts from the database
    # For now, we'll start with an empty cache and build it during the session
    self.concept_cache = {}

  def _determine_source_type(self, metadata: Dict[str, Any]) -> SourceType:
    """Determine source type from metadata."""
    url = metadata.get("url", "").lower()
    title = metadata.get("title", "").lower()

    if "arxiv" in url or "research" in title:
      return SourceType.RESEARCH_PAPER
    if "youtube" in url:
      return SourceType.VIDEO
    if url:
      return SourceType.WEBSITE
    return SourceType.DOCUMENT

  def _convert_concept_type(self, type_str: str) -> ConceptType:
    """Convert string type to ConceptType enum."""
    type_mapping = {
      "Person": ConceptType.PERSON,
      "Organization": ConceptType.ORGANIZATION,
      "Topic": ConceptType.TOPIC,
      "Technology": ConceptType.TECHNOLOGY,
      "Location": ConceptType.LOCATION,
      "Event": ConceptType.EVENT,
    }
    return type_mapping.get(type_str, ConceptType.TOPIC)

  def _find_relevant_concepts(
    self,
    claim_text: str,
    concept_mapping: Dict[str, str],
  ) -> List[str]:
    """Find concepts mentioned in claim text."""
    relevant_concepts = []
    claim_lower = claim_text.lower()

    for original_name, canonical_name in concept_mapping.items():
      if original_name.lower() in claim_lower:
        if canonical_name not in relevant_concepts:
          relevant_concepts.append(canonical_name)

    return relevant_concepts

  async def close(self):
    """Close knowledge graph connection."""
    if self.kg_client:
      await self.kg_client.close()


async def create_knowledge_integrator(
  config: Configuration,
) -> Optional[KnowledgeGraphIntegrator]:
  """Create and initialize a knowledge graph integrator."""
  if not config.neo4j_config or not config.neo4j_config.enabled:
    return None

  from open_deep_research.knowledge_graph import create_knowledge_graph_client

  kg_client = await create_knowledge_graph_client(config.neo4j_config)
  if not kg_client:
    return None

  extractor = KnowledgeExtractor(config)
  return KnowledgeGraphIntegrator(kg_client, extractor)
