import re
import json
from typing import Dict, List, Any

from agent.llm_client import LLMClient
from config.settings import Settings
from evaluation.models import ATSEvaluation, FaithfulnessAudit, JudgeAudit


class CVAnalyzer:
    @staticmethod
    def parse_markdown_counts(md_text: str) -> Dict[str, int]:
        """
        Deterministically counts items in Markdown sections.
        """
        sections = {"skills": 0, "experience": 0, "education": 0}
        parts = re.split(r'\n## ', md_text)
        for part in parts:
            lines = part.split('\n')
            header = lines[0].lower()
            bullets = [l for l in lines if l.strip().startswith(('-', '•'))]
            h3_count = len([l for l in lines if l.strip().startswith('###')])
            if "skills" in header:
                sections["skills"] = len(bullets)
            elif "experience" in header:
                sections["experience"] = h3_count
            elif "education" in header:
                sections["education"] = len(bullets)
        return sections

    @staticmethod
    def calculate_evidence_score(cv: Any) -> Dict:
        """
        Checks if skills in the skills list are backed by experience/project highlights.
        """
        # 1. Build the Proof Context (Experience, Summaries, and Tech Stacks)
        evidence_context = ""
        for exp in cv.experience:
            evidence_context += f" {exp.role_summary}"
            if exp.project_highlight:
                evidence_context += " " + " ".join(exp.project_highlight)
            if exp.technical_stack:
                evidence_context += " " + exp.technical_stack

        evidence_context = evidence_context.lower()

        # 2. Extract Individual Skills from categories
        unbacked_skills = []
        verified_count = 0
        total_keywords = 0

        for category_string in cv.skills:
            # Strip "LANGUAGES: " prefix
            content = category_string.split(":", 1)[1] if ":" in category_string else category_string
            keywords = re.split(r'[,;]', content)

            for kw in keywords:
                clean_kw = kw.strip().lower()
                if not clean_kw or len(clean_kw) < 2:
                    continue

                total_keywords += 1
                # Check for evidence
                if clean_kw in evidence_context:
                    verified_count += 1
                else:
                    unbacked_skills.append(clean_kw)

        # 3. Calculate Score (0-100)
        score = (verified_count / total_keywords * 100) if total_keywords > 0 else 100

        return {
            "score": score,
            "unbacked": unbacked_skills,
            "checked": total_keywords
        }

    @staticmethod
    def run_full_audit(cv_obj: Any, md_text: str, jd_text: str, master_cv_text: str, llm_client: LLMClient, config=None) -> ATSEvaluation:
        # 1. Parsing Accuracy
        intended = {"skills": len(cv_obj.skills), "experience": len(cv_obj.experience), "education": len(cv_obj.education)}
        actual = CVAnalyzer.parse_markdown_counts(md_text)
        correct_sections = sum(1 for s in intended if intended[s] == actual[s])
        parsing_acc = (correct_sections / 3) * 100

        # 2. Evidence Score (Anti-Keyword Stuffing)
        evidence = CVAnalyzer.calculate_evidence_score(cv_obj)

        # 3. Semantic Alignment (LLM Pass)
        alignment_prompt = f"Score semantic alignment (1-100) of CV against JD. JD: {jd_text} CV Summary: {cv_obj.summary}"
        align_score_str = llm_client.invoke_llm(alignment_prompt, use_strong=True, config=config)
        try:
            align_score = int(re.search(r'\d+', align_score_str).group())
        except:
            align_score = 70

        return ATSEvaluation(
            parsing_accuracy=parsing_acc,
            evidence_score=evidence["score"],
            alignment_score=align_score,
            unbacked_skills=evidence["unbacked"],
            parsing_errors=[f"{s}: fail" for s in intended if intended[s] != actual[s]],
            overall_recommendation="Approve" if parsing_acc == 100 and evidence["score"] > 80 else "Review"
        )


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
$S = \frac{{C_v}}{{C_t}} \times 100$

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
                source_text=source_text,  # No truncation
                generated_cv=generated_cv
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
                hallucinations=[{"claim": "Evaluation error", "reason": f"Faithfulness evaluation failed: {str(e)}"}],
                audit_summary=f"Faithfulness evaluation failed due to error: {str(e)}"
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