    Overview

     Refactor the evaluation system to consolidate scattered logic into a unified module,
      improve information density, and maintain functional parity. This addresses the
     primary request to create a unified evaluation module while implementing moderate
     consolidation of small files and duplicates.

     Current Issues Identified

     1. Scattered evaluation logic: Split across evaluate.py, tools/cv_analyzer.py,
     tools/faithfulness_evaluator.py
     2. Redundant utilities: clean_text, is_exact_match, YAML loading duplicated
     3. Circular imports: tools/ → agent/ → tools/ dependencies
     4. Low information density: Multiple small files (<50 lines)
     5. Mixed concerns: Evaluation models in agent/models.py with core CV models

     Refactoring Goals

     Primary Goals

     1. Create unified evaluation module consolidating:
       - Judge/evaluation models from agent/models.py (ATSEvaluation, JudgeAudit,
     FaithfulnessAudit)
       - tools/cv_analyzer.py and tools/faithfulness_evaluator.py
       - Refactor evaluate.py to be a thin runner

     Secondary Goals (Moderate Consolidation)

     1. Merge obvious duplicates and small utilities
     2. Improve information density while maintaining parity
     3. Keep PDF generation as-is (no changes)
     4. Keep evaluation artifacts (no cleanup)
     5. Code deletion preferred if same functionality can be kept

     New Module Structure

     evaluation/                    # New unified evaluation module
     ├── __init__.py               # Module exports
     ├── evaluator.py              # Consolidated evaluation logic (merge of cv_analyzer
     + faithfulness_evaluator)
     ├── models.py                 # Evaluation-specific models (ATSEvaluation,
     JudgeAudit, FaithfulnessAudit)
     └── utils.py                  # Shared utilities (clean_text, is_exact_match,
     hallucination checks)

     tools/                        # Updated tools directory
     ├── cv_builder.py             # Unchanged (63 lines)
     ├── job_search.py             # Unchanged (35 lines)
     └── __init__.py

     agent/                        # Updated agent directory
     ├── models.py                 # Core CV models only (OptimizedCV, Experience,
     Education, AgentState)
     ├── llm_client.py             # Unchanged (53 lines)
     ├── orchestrator.py           # Unchanged (211 lines)
     └── __init__.py

     prompts/                      # Unchanged
     └── templates.py              # Unchanged (38 lines)

     evaluate.py                    # Thin runner (modified, not moved)

     Files to Create

     1. /Users/michaelkao/Git/job_research_agent_v2/evaluation/__init__.py
     2. /Users/michaelkao/Git/job_research_agent_v2/evaluation/evaluator.py (merge
     cv_analyzer.py + faithfulness_evaluator.py)
     3. /Users/michaelkao/Git/job_research_agent_v2/evaluation/models.py (extract
     evaluation models from agent/models.py)
     4. /Users/michaelkao/Git/job_research_agent_v2/evaluation/utils.py (shared utilities
      from evaluate.py)

     Files to Modify

     1. /Users/michaelkao/Git/job_research_agent_v2/evaluate.py - Refactor to be thin
     runner:
       - Remove utility functions that move to evaluation/utils.py
       - Remove evaluation logic that moves to evaluation/evaluator.py
       - Keep experiment orchestration and summary generation
       - Update imports to use new evaluation module
     2. /Users/michaelkao/Git/job_research_agent_v2/agent/models.py - Remove
     ATSEvaluation, JudgeAudit, FaithfulnessAudit
     3. Update imports in all dependent files to use new evaluation module

     Files to Delete

     1. /Users/michaelkao/Git/job_research_agent_v2/tools/cv_analyzer.py (merged into
     evaluation/evaluator.py)
     2. /Users/michaelkao/Git/job_research_agent_v2/tools/faithfulness_evaluator.py
     (merged into evaluation/evaluator.py)

     Dependency Management

     Current Import Chains

     - evaluate.py → tools.cv_analyzer → agent.models → (circular)
     - evaluate.py → tools.faithfulness_evaluator → agent.models → agent.llm_client

     New Import Structure

     - evaluate.py → evaluation.evaluator → evaluation.models
     - evaluation/evaluator.py → agent.llm_client (only LLM dependency)
     - agent/models.py → (no evaluation dependencies)
     - All other files import from evaluation.models instead of agent.models

     Model Consolidation Details

     Move from agent/models.py to evaluation/models.py:

     - ATSEvaluation (lines 23-29)
     - JudgeAudit (lines 31-33)
     - FaithfulnessAudit (lines 35-40)

     Keep in agent/models.py:

     - Experience, Education, OptimizedCV (core CV models)
     - AgentState (TypedDict for orchestration)

     Implementation Phases

     Phase 1: Create New Evaluation Module Structure

     1. Create evaluation/ directory with __init__.py
     2. Create evaluation/models.py with extracted evaluation models
     3. Create evaluation/utils.py with shared utilities:
       - clean_text() and is_exact_match() from evaluate.py
       - check_yoe_hallucination() and check_metric_hallucination() from evaluate.py
     4. Create evaluation/evaluator.py by merging:
       - cv_analyzer.py core logic (markdown parsing, evidence scoring, full audit)
       - faithfulness_evaluator.py core logic (faithfulness evaluation with prompt
     template)
       - Keep both CVAnalyzer and FaithfulnessEvaluator classes initially for
     compatibility

     Phase 2: Update Agent Models

     1. Remove evaluation models from agent/models.py
     2. Update any remaining imports in agent module to use new evaluation.models

     Phase 3: Refactor Evaluate.py as Thin Runner

     1. Modify evaluate.py to be a thin runner:
       - Remove utility functions that moved to evaluation/utils.py
       - Remove evaluation logic that moved to evaluation/evaluator.py
       - Keep experiment orchestration and summary generation
       - Update imports to use new evaluation module
     2. Keep run_evaluation() as main entry point (unchanged)

     Phase 4: Update All Imports

     1. Update agent/orchestrator.py imports if using evaluation models
     2. Update tools/cv_builder.py imports if needed
     3. Update parse_jd_to_yaml.py imports if needed
     4. Update test files (tests/test_agent.py, tests/test_tools.py)

     Phase 5: Cleanup and Finalization

     1. Delete tools/cv_analyzer.py
     2. Delete tools/faithfulness_evaluator.py
     3. Update any documentation references

     Phase 6: Testing and Validation

     1. Run existing test suite: uv run python -m pytest tests/
     2. Test evaluation pipeline: uv run python evaluate.py
     3. Verify import chains work with simple import test script
     4. Run end-to-end evaluation on sample JDs

     Risk Mitigation

     1. Circular imports: Careful dependency management, test imports after each change
     2. Functionality regression: Maintain exact same public APIs, run tests after each
     phase
     3. Import errors: Update imports systematically, use type checking
     4. Model serialization: Ensure Pydantic models work identically in new location

     Testing Strategy

     1. Unit tests: Existing test suite should pass with updated imports
     2. Integration test: Run full evaluation pipeline with sample data
     3. Import test: Create simple script to import all modules and check for errors
     4. End-to-end test: Run agent and evaluation on sample JDs to verify output parity

     Expected Benefits

     1. Clear separation: Evaluation logic separate from agent core
     2. Reduced duplication: Shared utilities in one place
     3. Better cohesion: Related evaluation code together
     4. Simplified imports: No circular dependencies
     5. Improved maintainability: Easier to extend evaluation functionality
     6. Higher information density: Fewer files with clearer organization

     Files to Review Before Implementation

     1. /Users/michaelkao/Git/job_research_agent_v2/agent/models.py - Current evaluation
     models
     2. /Users/michaelkao/Git/job_research_agent_v2/tools/cv_analyzer.py - ATS evaluation
      logic
     3. /Users/michaelkao/Git/job_research_agent_v2/tools/faithfulness_evaluator.py -
     Faithfulness evaluation
     4. /Users/michaelkao/Git/job_research_agent_v2/evaluate.py - Current runner

     Success Metrics

     1. Functionality parity: All existing tests pass
     2. Reduced file count: 2 files deleted, 4 new files created (net +2, but better
     organization)
     3. Import clarity: No circular dependencies
     4. Maintainability: Clear separation of concerns
     5. Performance: No degradation in evaluation speed or accuracy

     Notes

     - PDF generation remains unchanged as requested
     - Evaluation artifacts are kept as requested
     - Moderate consolidation approach: merging evaluation files but keeping small
     utility files separate
     - Code deletion is implemented where functionality can be maintained
