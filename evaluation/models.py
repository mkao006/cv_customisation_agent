from typing import List, Dict
from pydantic import BaseModel, Field


class ATSEvaluation(BaseModel):
    parsing_accuracy: float = Field(description="0-100: % of items correctly parsed")
    evidence_score: float = Field(description="0-100: % of skills backed by experience")
    alignment_score: int = Field(description="1-100: Semantic match")
    unbacked_skills: List[str] = Field(description="Skills found in list but not in experience context")
    parsing_errors: List[str] = Field(description="Sections where counts did not match")
    overall_recommendation: str = Field(description="Approve, Review, or Reject")


class JudgeAudit(BaseModel):
    hallucinations: List[str] = Field(description="List of tools or tech NOT found in Master Records")
    count: int = Field(description="Number of hallucinations found")


class FaithfulnessAudit(BaseModel):
    faithfulness_score: float = Field(description="Percentage of verified claims (0-100)")
    total_claims: int = Field(description="Total number of claims identified in CV")
    verified_claims: int = Field(description="Number of claims verified against source")
    hallucinations: List[Dict[str, str]] = Field(description="List of unfaithful claims with reasons")
    audit_summary: str = Field(description="Short paragraph explaining overall integrity")