# Open Deep Research Repository

## Project Overview
Open Deep Research is a configurable, fully open-source deep research agent that conducts automated research with parallel processing and comprehensive report generation. It's built on LangGraph and supports multiple model providers, search tools, and MCP (Model Context Protocol) servers.

## Repository Architecture

### Core Implementation (`src/open_deep_research/`)
- `deep_researcher.py` - Main LangGraph workflow implementation (entry point: `deep_researcher`)
  - Multi-stage research pipeline: clarification → research brief → supervisor → final report
  - Parallel research execution with configurable concurrency limits
  - Token limit handling with graceful degradation and retry logic
- `configuration.py` - Centralized configuration management with Pydantic validation
- `state.py` - Graph state definitions and data structures for workflow coordination
- `prompts.py` - System prompts and templates for different research phases
- `utils.py` - Utility functions including search tools, model management, and MCP integration

### Security (`src/security/`)
- `auth.py` - Authentication handler for LangGraph Cloud deployment

### Legacy Implementations (`src/legacy/`)
Contains two earlier research approaches with their own complete implementations:
- `graph.py` - Plan-and-execute workflow with human-in-the-loop approval
- `multi_agent.py` - Supervisor-researcher multi-agent architecture
- `legacy.md` - Documentation for understanding the evolution of approaches
- Complete self-contained modules with their own configuration, state, and utilities

### Evaluation and Testing (`tests/`)
- `run_evaluate.py` - Main evaluation script for Deep Research Bench benchmark
- `evaluators.py` - Specialized evaluation functions for quality metrics
- `pairwise_evaluation.py` - Comparative evaluation tools
- `supervisor_parallel_evaluation.py` - Multi-threaded evaluation capabilities

### Examples (`examples/`)
Research examples demonstrating different use cases:
- `arxiv.md` - Academic research example
- `pubmed.md` - Medical literature research
- `inference-market.md` - Market analysis examples

## Key Technologies and Dependencies

### Core Framework
- **LangGraph** (`>=0.5.4`) - Workflow orchestration and graph execution
- **LangChain** (`>=0.3.9`) - LLM integration and tool calling framework
- **LangSmith** (`>=0.3.37`) - Experiment tracking and evaluation

### Model Providers
- **OpenAI** (`>=1.99.2`) - GPT models including GPT-5 support
- **Anthropic** (`>=0.3.15`) - Claude models including Sonnet 4
- **Google Vertex AI** (`>=2.0.25`) - Gemini models
- **Groq** (`>=0.2.4`) - Fast inference
- **DeepSeek** (`>=0.1.2`) - Alternative model provider
- **AWS Bedrock** (`>=0.2.28`) - Cloud model access

### Search and Data Sources
- **Tavily** (`>=0.5.0`) - Primary search API with academic focus
- **DuckDuckGo** (`>=3.0.0`) - Alternative web search
- **Exa** (`>=1.8.8`) - Semantic search capabilities
- **ArXiv** (`>=2.1.3`) - Academic paper access
- **Azure Search** (`>=11.5.2`) - Enterprise search integration

### Development and Utility
- **PyMuPDF** (`>=1.25.3`) - PDF processing
- **BeautifulSoup4** (`==4.13.3`) - HTML parsing
- **Rich** (`>=13.0.0`) - Terminal formatting
- **Ruff** (`>=0.6.1`) - Code linting and formatting
- **MyPy** (`>=1.11.1`) - Static type checking

## Configuration System

### Model Configuration
Four specialized model roles with independent configuration:
- **Summarization Model** (`openai:gpt-4.1-mini`) - Processes search results
- **Research Model** (`openai:gpt-4.1`) - Powers search agents and supervisor
- **Compression Model** (`openai:gpt-4.1`) - Synthesizes research findings
- **Final Report Model** (`openai:gpt-4.1`) - Generates comprehensive reports

### Search API Options
- **Tavily** (default) - Academic-focused search with content summarization
- **OpenAI Native Web Search** - Built-in web search for OpenAI models
- **Anthropic Native Web Search** - Built-in web search for Claude models
- **None** - Rely on MCP tools only

### Research Control Parameters
- `max_concurrent_research_units` (5) - Parallel research tasks limit
- `max_researcher_iterations` (6) - Supervisor reflection cycles
- `max_react_tool_calls` (10) - Tool usage limit per researcher
- `allow_clarification` (true) - Enable user clarification phase

### MCP Integration
Full Model Context Protocol support for extended capabilities:
- Configurable MCP server URL and authentication
- Tool selection and availability control
- Custom prompt instructions for MCP tool usage

## Development Commands

### Local Development
```bash
# Install dependencies
uv sync

# Start LangGraph Studio
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking

# Code quality checks
ruff check                    # Linting
mypy                         # Type checking
```

### Evaluation and Testing
```bash
# Run comprehensive evaluation on Deep Research Bench
python tests/run_evaluate.py

# Extract results from LangSmith experiments
python tests/extract_langsmith_data.py --project-name "EXPERIMENT_NAME" --model-name "MODEL" --dataset-name "deep_research_bench"
```

## Workflow Architecture

### Main Research Pipeline
1. **Clarification Phase** (`clarify_with_user`)
   - Analyzes user request for clarity and scope
   - Asks clarifying questions if needed (configurable)
   - Proceeds to research brief generation

2. **Research Brief Generation** (`write_research_brief`)
   - Transforms user messages into structured research brief
   - Initializes supervisor with strategic context and constraints

3. **Research Supervision** (`research_supervisor`)
   - Strategic research planning and task delegation
   - Parallel execution of research units with concurrency limits
   - Iterative refinement based on findings

4. **Final Report Generation** (`final_report_generation`)
   - Synthesizes all research findings into comprehensive report
   - Handles token limit exceeded with progressive truncation
   - Returns structured final report

### Research Execution Details
- **Supervisor Tools**: ConductResearch, ResearchComplete, think_tool
- **Researcher Tools**: Search APIs, MCP tools, think_tool, ResearchComplete  
- **Error Handling**: Token limit detection, graceful degradation, retry logic
- **Concurrency Control**: Configurable limits to prevent resource exhaustion

## File Organization Principles

### Core Module Structure
- Each major component has dedicated state definitions in `state.py`
- Configuration is centralized with environment variable override support
- Prompts are templated and easily customizable in `prompts.py`
- Utilities are organized by functionality (search, models, MCP, validation)

### Legacy Code Preservation
- Complete legacy implementations preserved for reference and learning
- Each legacy approach is self-contained with full documentation
- Evolution from simple to complex approaches documented in blog posts

### Testing and Evaluation Structure
- Benchmark-focused evaluation with standardized metrics
- Support for multiple evaluation approaches (pairwise, parallel, supervised)
- Integration with LangSmith for experiment tracking and analysis

## Performance and Scalability

### Evaluation Results
Current performance on Deep Research Bench:
- **GPT-5**: 0.4943 RACE score (204M tokens)
- **Claude Sonnet 4**: 0.4401 RACE score (138M tokens, $187)
- **Default GPT-4.1**: 0.4309 RACE score (58M tokens, $46)

### Resource Management
- Configurable concurrency limits prevent rate limit issues
- Token limit handling with progressive truncation strategies
- Async execution throughout for optimal performance
- Memory-efficient streaming where supported

### Deployment Options
- **LangGraph Studio** - Local development and testing
- **LangGraph Platform** - Hosted deployment with scaling
- **Open Agent Platform** - No-code configuration interface
- **GitHub Actions** - CI/CD integration for automated evaluation

## Security and Authentication

### API Key Management
- Environment variable configuration with runtime override
- Per-model API key specification support
- Secure handling through LangGraph configuration system

### Deployment Security
- Authentication handler for cloud deployments
- Configurable auth requirements for MCP servers
- Secure environment variable handling in production

## Usage Guidelines for Claude

### Code Modification
- Always understand existing configuration patterns before adding new fields
- Follow the established state management patterns with proper reducers
- Maintain async/await patterns throughout the codebase
- Add proper error handling and token limit management for new features

### Testing and Evaluation
- Run `python tests/run_evaluate.py` for comprehensive testing
- Use LangSmith experiment tracking for performance analysis
- Test with multiple model configurations to ensure compatibility
- Validate configuration changes with small test runs before full evaluation

### Development Workflow
1. Make code changes following existing patterns
2. Run `ruff check` and `mypy` for code quality
3. Test locally with `uvx langgraph dev`
4. Run targeted evaluations to validate changes
5. Update documentation if adding new configuration options

### Performance Considerations
- Be mindful of token limits when modifying prompts or adding context
- Consider concurrency limits when adding new parallel operations  
- Test with different model configurations to ensure broad compatibility
- Monitor evaluation costs when making changes that affect model usage

## Important Notes
- Never commit API keys or sensitive configuration
- Always test configuration changes with small examples before full evaluation
- Maintain backward compatibility when modifying configuration schemas
- Document any new MCP integrations thoroughly for future maintainers