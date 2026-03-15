from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field

class Experience(BaseModel):
    job_title: str = Field(description="The title of the position held")
    company: str = Field(description="The name of the company")
    dates: str = Field(description="The date range of employment")
    responsibilities: List[str] = Field(description="A list of key responsibilities and achievements")

class Education(BaseModel):
    degree: str = Field(description="The degree obtained")
    institution: str = Field(description="The name of the educational institution")
    completion_year: str = Field(description="The year of completion")

class OptimizedCV(BaseModel):
    summary: str = Field(description="A professional summary tailored to the job description")
    experience: List[Experience] = Field(description="A list of work experiences, keyword-optimized for ATS")
    skills: List[str] = Field(description="A list of relevant technical and soft skills")
    education: List[Education] = Field(description="A list of educational qualifications")

class ATSEvaluation(BaseModel):
    parsing_accuracy: float = Field(description="0-100: % of items correctly parsed from MD vs intended")
    evidence_score: float = Field(description="0-100: % of skills backed by experience/projects")
    alignment_score: int = Field(description="1-100: Semantic match between CV and JD")
    unbacked_skills: List[str] = Field(description="Skills found in list but not in experience context")
    parsing_errors: List[str] = Field(description="Sections where counts did not match")
    overall_recommendation: str = Field(description="Approve, Review, or Reject")

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
    research_evaluation: str # 'satisfactory' or 'needs_refinement'
    research_gaps: Optional[str]
    application_strategy: str
    personalization_instructions: Optional[str]
    cv_audit_log: Optional[str]
    final_ats_cv: Optional[OptimizedCV]
