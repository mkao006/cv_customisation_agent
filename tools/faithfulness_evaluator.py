import json
import re
from typing import Dict, Any
from agent.models import FaithfulnessAudit
from agent.llm_client import LLMClient
from config.settings import Settings

class FaithfulnessEvaluator:
    """Evaluates faithfulness of generated CV against source master CV."""

    # Prompt template based on user's V2 specification
    FAITHFULNESS_PROMPT_TEMPLATE = """System Role: You are a precision-oriented Document Auditor. Your task is to perform a side-by-side consistency check between a Source Document and a Generated CV.

Input Data
Source Document: {source_text}
Generated CV: {generated_cv}

Audit Protocol
1. Decomposition: Break the Generated CV into individual factual claims (e.g., "Worked at Google," "Python proficiency," "2019-2022").
2. Source Mapping: For every claim, search the Source Document for a direct or synonymous match.
3. Conflict Detection: Flag any claim that is:
   - Contradictory: Dates or titles that differ from the source.
   - Unsupported: Information that appears in the CV but is entirely absent from the source (Hallucination).
   - Embellished: Skills or responsibilities that are significantly upgraded beyond what the source suggests.

Scoring Logic
Use the following calculation for the final metric:
$S = \\frac{{C_v}}{{C_t}} \\times 100$

Where:
$S$ = Faithfulness Score
$C_v$ = Number of Verified Claims
$C_t$ = Total Number of Claims in the CV

Required Output Format (JSON)
Return the evaluation in the following structure:
{{
  "faithfulness_score": 0.0,
  "total_claims": 0,
  "verified_claims": 0,
  "hallucinations": [
    {{"claim": "String", "reason": "Why it is unfaithful"}}
  ],
  "audit_summary": "Short paragraph explaining the overall integrity."
}}

Important: Be strict but fair. Claims should be considered verified if they are directly supported by the source or if they are reasonable interpretations/synonyms.
For dates, allow small variations in formatting but flag actual contradictions.
For skills, verify that the skill is mentioned in the source context.
"""

    def __init__(self, model_name: str = None):
        """Initialize faithfulness evaluator.

        Args:
            model_name: Optional model name to use for evaluation. If not provided,
                       uses Settings.FAITHFULNESS_MODEL (default: google/gemini-2.5-pro)
        """
        self.model_name = model_name or Settings.FAITHFULNESS_MODEL
        # Create a separate LLM client for faithfulness evaluation
        # We'll use the existing LLMClient but with a different model
        self.llm_client = LLMClient(model_name=self.model_name)

    def evaluate(self, source_text: str, generated_cv: str, config=None) -> FaithfulnessAudit:
        """Evaluate faithfulness of generated CV against source.

        Args:
            source_text: The source/master CV text (YAML format)
            generated_cv: The generated CV text (markdown format)
            config: Optional LangChain run configuration

        Returns:
            FaithfulnessAudit object with evaluation results
        """
        try:
            # Format the prompt
            prompt = self.FAITHFULNESS_PROMPT_TEMPLATE.format(
                source_text=source_text[:3000],  # Limit to avoid token limits
                generated_cv=generated_cv[:3000]
            )

            # Get structured output
            structured_llm = self.llm_client.with_structured_output(FaithfulnessAudit, use_strong=False)

            try:
                result = structured_llm.invoke(prompt, config=config)
                return result
            except Exception as e:
                # Fallback: try to parse as JSON if structured output fails
                print(f"Faithfulness evaluation: structured output failed, falling back to text parsing: {e}")
                text_result = self.llm_client.invoke_llm(prompt, use_strong=False, config=config)
                return self._parse_text_response(text_result)
        except Exception as e:
            # Complete failure - return error audit
            print(f"Faithfulness evaluation completely failed: {e}")
            return FaithfulnessAudit(
                faithfulness_score=0.0,
                total_claims=0,
                verified_claims=0,
                hallucinations=[{"claim": "Evaluation error", "reason": f"Faithfulness evaluation failed: {str(e)[:100]}"}],
                audit_summary=f"Faithfulness evaluation failed due to error: {str(e)[:200]}"
            )

    def _parse_text_response(self, text_response: str) -> FaithfulnessAudit:
        """Parse text response into FaithfulnessAudit object.

        Used as fallback when structured output fails.
        """
        # Try to extract JSON from text
        json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # Ensure hallucinations list has proper structure
                hallucinations = []
                if "hallucinations" in data:
                    for h in data["hallucinations"]:
                        if isinstance(h, dict) and "claim" in h and "reason" in h:
                            hallucinations.append(h)
                        elif isinstance(h, str):
                            hallucinations.append({"claim": h, "reason": "Unsupported by source"})
                        else:
                            hallucinations.append({"claim": str(h), "reason": "Unsupported by source"})

                return FaithfulnessAudit(
                    faithfulness_score=float(data.get("faithfulness_score", 0.0)),
                    total_claims=int(data.get("total_claims", 0)),
                    verified_claims=int(data.get("verified_claims", 0)),
                    hallucinations=hallucinations,
                    audit_summary=data.get("audit_summary", "Failed to parse audit summary")
                )
            except json.JSONDecodeError:
                pass

        # Default fallback if parsing fails
        return FaithfulnessAudit(
            faithfulness_score=0.0,
            total_claims=0,
            verified_claims=0,
            hallucinations=[{"claim": "Parse error", "reason": "Failed to parse evaluation response"}],
            audit_summary="Evaluation failed: could not parse LLM response"
        )

    @staticmethod
    def should_pass(faithfulness_score: float, threshold: float = 98.0) -> bool:
        """Determine if CV passes faithfulness check.

        Args:
            faithfulness_score: Score from 0-100
            threshold: Minimum score to pass (default 98% as suggested)

        Returns:
            True if score meets or exceeds threshold
        """
        return faithfulness_score >= threshold