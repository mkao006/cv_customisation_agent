from typing import TypedDict, List, Optional, Dict
from pydantic import BaseModel, Field

class Experience(BaseModel):
    job_title: str = Field(description="The title of the position held")
    company: str = Field(description="The name of the company")
    dates: str = Field(description="The date range of employment")
    role_summary: str = Field(description="A high-impact one-liner summarising the core responsibility")
    project_highlight: Optional[List[str]] = Field(description="Tailored bullet points of the most relevant project")
    technical_stack: Optional[str] = Field(description="The specific tools used for this project (formatted as 'Tech Stack: tool1, tool2')")

class Education(BaseModel):
    degree: str = Field(description="The degree obtained")
    institution: str = Field(description="The name of the educational institution")
    completion_year: str = Field(description="The year of completion")

class OptimizedCV(BaseModel):
    summary: str = Field(description="Professional summary tailored to the JD")
    skills: List[str] = Field(description="Categorical technical skills")
    experience: List[Experience] = Field(description="Work experiences sorted reverse-chronologically")
    education: List[Education] = Field(description="Educational qualifications")

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

class AgentState(TypedDict):
    original_cv: str
    jd_source: str
    jd_text: str
    jd_validation_error: Optional[str]
    company_research: str
    best_practices_research: str
    competing_candidates_research: str
    research_iteration: int
    max_research_iterations: int
    research_evaluation: str
    research_gaps: Optional[str]
    application_strategy: str
    personalization_instructions: Optional[str]
    cv_audit_log: Optional[str]
    final_ats_cv: Optional[OptimizedCV]
