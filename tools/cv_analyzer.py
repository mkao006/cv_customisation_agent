import re
from typing import Dict, List
from agent.models import OptimizedCV, ATSEvaluation
from agent.llm_client import LLMClient

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
            if "skills" in header: sections["skills"] = len(bullets)
            elif "experience" in header: sections["experience"] = h3_count
            elif "education" in header: sections["education"] = len(bullets)
        return sections

    @staticmethod
    def calculate_evidence_score(cv: OptimizedCV) -> Dict:
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
    def run_full_audit(cv_obj: OptimizedCV, md_text: str, jd_text: str, master_cv_text: str, llm_client: LLMClient, config=None) -> ATSEvaluation:
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
