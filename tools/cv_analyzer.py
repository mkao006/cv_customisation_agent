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
        sections = {
            "skills": 0,
            "experience": 0,
            "education": 0
        }
        
        # Split by section headers (using \n## to avoid literal newline breakage)
        parts = re.split(r'\n## ', md_text)
        
        for part in parts:
            lines = part.split('\n')
            header = lines[0].lower()
            
            # Count bullet points starting with '- ' or '• '
            bullets = [l for l in lines if l.strip().startswith(('-', '•'))]
            # For experience, we count subheaders (###)
            h3_count = len([l for l in lines if l.strip().startswith('###')])
            
            if "skills" in header:
                sections["skills"] = len(bullets)
            elif "experience" in header:
                sections["experience"] = h3_count
            elif "education" in header:
                sections["education"] = len(bullets)
                
        return sections

    @staticmethod
    def calculate_evidence_score(cv: OptimizedCV) -> Dict:
        """
        Checks if skills in the skills list appear in the experience bullets.
        """
        # Create a giant string of all experience context
        experience_context = " ".join([
            " ".join(exp.responsibilities) for exp in cv.experience
        ]).lower()
        
        # Also include the professional summary in the context
        experience_context += " " + cv.summary.lower()
        
        unbacked_skills = []
        verified_count = 0
        total_keywords_checked = 0
        
        for category_string in cv.skills:
            # Handle categories like "LANGUAGES: Python, SQL"
            # Strip the category name if present
            content = category_string
            if ":" in category_string:
                content = category_string.split(":", 1)[1]
            
            # Extract keywords by splitting on common delimiters
            keywords = re.split(r'[,;]', content)
            for kw in keywords:
                kw = kw.strip().lower()
                if not kw or len(kw) < 2:
                    continue
                
                total_keywords_checked += 1
                # Check for keyword in experience context
                if kw in experience_context:
                    verified_count += 1
                else:
                    unbacked_skills.append(kw)
        
        score = (verified_count / total_keywords_checked * 100) if total_keywords_checked > 0 else 100
        
        return {
            "score": score,
            "unbacked": unbacked_skills
        }

    @staticmethod
    def run_full_audit(cv_obj: OptimizedCV, md_text: str, jd_text: str, llm_client: LLMClient, config=None) -> ATSEvaluation:
        # 1. Parsing Accuracy
        intended = {
            "skills": len(cv_obj.skills),
            "experience": len(cv_obj.experience),
            "education": len(cv_obj.education)
        }
        actual = CVAnalyzer.parse_markdown_counts(md_text)
        
        errors = []
        correct_sections = 0
        for section in intended:
            if intended[section] == actual[section]:
                correct_sections += 1
            else:
                errors.append(f"{section}: intended {intended[section]}, found {actual[section]}")
        
        parsing_acc = (correct_sections / 3) * 100
        
        # 2. Evidence Score (Keyword Stuffing)
        evidence = CVAnalyzer.calculate_evidence_score(cv_obj)
        
        # 3. Semantic Alignment (LLM Pass)
        alignment_prompt = f"""
        Score the semantic alignment (1-100) of this CV impact against the JD.
        Does the candidate's demonstrated experience solve the problems mentioned in the JD?
        
        JD: {jd_text[:1500]}
        CV SUMMARY: {cv_obj.summary}
        
        Return ONLY the integer score.
        """
        align_score_str = llm_client.invoke_llm(alignment_prompt, use_strong=True, config=config)
        try:
            align_score = int(re.search(r'\d+', align_score_str).group())
        except:
            align_score = 70

        # 4. Final Recommendation
        rec = "Approve"
        if parsing_acc < 100 or evidence["score"] < 70 or align_score < 60:
            rec = "Review"
        if evidence["score"] < 40 or align_score < 40:
            rec = "Reject"

        return ATSEvaluation(
            parsing_accuracy=parsing_acc,
            evidence_score=evidence["score"],
            alignment_score=align_score,
            unbacked_skills=evidence["unbacked"][:15],
            parsing_errors=errors,
            overall_recommendation=rec
        )
