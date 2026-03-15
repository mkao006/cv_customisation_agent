# Development Context: Job Research Agent V2

## Core Philosophy
This agent is designed to produce high-integrity, ATS-optimized, and project-centric CVs. It prioritizes empirical evidence from a "Master CV" (Source of Truth) to prevent hallucinations.

## Architectural Patterns

### 1. Structured LLM Output
- **Mandate**: Avoid manual JSON parsing from raw LLM strings.
- **Pattern**: Use `llm_client.with_structured_output(Model)` with Pydantic models.
- **Why**: Ensures type safety, handles LLM conversational "fluff," and provides reliable data for downstream tools.

### 2. CV Generation Strategy
- **Project-Centric**: Each work experience role should focus on a "Project Highlight" followed by a specific "Technical Stack" line.
- **Schema**: `OptimizedCV` (in `agent/models.py`) requires `role_summary`, `project_highlight` (list), and `technical_stack` (string).
- **Indentation**: Markdown output in `CVBuilder.generate_cv_markdown` must be strictly validated to ensure proper rendering for both PDF and parsing.

### 3. Hybrid Evaluation (ATS Mock)
- **Deterministic Audits**: `evaluate.py` uses regex for Year of Experience (YoE) and Metric hallucination checks.
- **Semantic Judge**: Uses the `JudgeAudit` model to compare CV keywords against the Master CV records.
- **Evidence Scoring**: `CVAnalyzer.calculate_evidence_score` checks if listed skills appear in the experience descriptions or tech stacks.

## Key Files
- `agent/models.py`: All Pydantic schemas and `AgentState`.
- `evaluate.py`: The main entry point for running experiment batches.
- `agent/orchestrator.py`: The LangGraph-based workflow (Ingest -> Validate -> Research -> Synthesize -> Generate -> Sanitize).
- `agent/llm_client.py`: Wrapper for OpenRouter and LangChain integration.

## Common Workflows
- **Execution**: Always use `uv run python <file>.py`.
- **Tracing**: Ensure Arize Phoenix is running (`uv run phoenix serve`) as `Settings.init_tracing()` is called in main entry points.
- **Adding Tests**: Reproduction scripts should be used to verify LLM response formats before updating core logic.
