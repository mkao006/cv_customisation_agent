import os
import yaml
import json
import glob
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent.orchestrator import Orchestrator
from agent.llm_client import LLMClient

def clean_text(text):
    """Normalize text for better matching."""
    return re.sub(r'\s+', ' ', str(text).lower()).strip()

def is_exact_match(keyword, master_text):
    """Check if the keyword exists as a substring in the normalized master text."""
    kw = clean_text(keyword)
    # Match whole words or standard phrases
    pattern = rf"\b{re.escape(kw)}\b"
    return re.search(pattern, master_text) is not None

def evaluate_jd(jd_file, master_cv_path, master_cv_text, normalized_master, orchestrator, llm_client):
    """Evaluates a single JD using two independent methods: Exact Match and LLM Judge."""
    jd_filename = os.path.basename(jd_file)
    print(f">> Evaluating JD: {jd_filename}")
    
    with open(jd_file, "r") as f:
        jd_data = yaml.safe_load(f)
        jd_text = yaml.dump(jd_data, default_flow_style=False)

    initial_state = {
        "original_cv": master_cv_path,
        "jd_source": jd_file,
        "jd_text": "",
        "jd_validation_error": None,
        "research_iteration": 0,
        "max_research_iterations": 1,
        "research_gaps": "",
        "company_research": "",
        "best_practices_research": "",
        "competing_candidates_research": "",
        "application_strategy": "",
        "personalization_instructions": "Focus on strict adherence to the original CV content.",
        "final_ats_cv": None
    }
    
    try:
        final_state = orchestrator.run(initial_state)
        tailored_cv = final_state.get("final_ats_cv")
        
        if not tailored_cv:
            print(f"   [!] Failed to generate CV for {jd_filename}")
            return None

        # STEP 1: Extract keywords from Tailored CV
        extract_prompt = f"Extract a list of all technical skills, tools, and methodologies from this CV: {tailored_cv.skills}. Return JSON list of strings only."
        extraction_response = llm_client.invoke_llm(extract_prompt)
        if "```json" in extraction_response:
            extraction_response = extraction_response.split("```json")[1].split("```")[0].strip()
        elif "```" in extraction_response:
            extraction_response = extraction_response.split("```")[1].split("```")[0].strip()
        
        extracted_keywords = json.loads(extraction_response)
        
        # METHOD 1: Programmatic Exact Match Audit
        exact_match_hallucinations = []
        for kw in extracted_keywords:
            if not is_exact_match(kw, normalized_master):
                exact_match_hallucinations.append(kw)

        # METHOD 2: LLM as a Judge Audit
        judge_prompt = f"""
        Compare keywords from a 'Tailored CV' against a 'Master CV'.
        Identify true hallucinations. 
        - ALLOW: Industry synonyms (ML/Machine Learning), standard abbreviations, common role-based tasks.
        - FLAG: Specific tools or methodologies NOT in Master CV.
        
        MASTER CV: {master_cv_text}
        KEYWORDS: {extracted_keywords}
        
        Return JSON: {{"hallucinations": [], "explanation": ""}}
        """
        judge_response = llm_client.invoke_llm(judge_prompt)
        if "```json" in judge_response:
            judge_response = judge_response.split("```json")[1].split("```")[0].strip()
        elif "```" in judge_response:
            judge_response = judge_response.split("```")[1].split("```")[0].strip()
        
        llm_judge_data = json.loads(judge_response)
        llm_judge_hallucinations = llm_judge_data.get("hallucinations", [])

        print(f"   [+] {jd_filename}: Exact Match Found {len(exact_match_hallucinations)} | LLM Judge Found {len(llm_judge_hallucinations)}")

        return {
            "jd": jd_filename,
            "total_keywords": len(extracted_keywords),
            "exact_match_audit": {
                "hallucinations": exact_match_hallucinations,
                "count": len(exact_match_hallucinations)
            },
            "llm_judge_audit": {
                "hallucinations": llm_judge_hallucinations,
                "count": len(llm_judge_hallucinations),
                "explanation": llm_judge_data.get("explanation", "")
            }
        }
    except Exception as e:
        print(f"   [X] Error during evaluation of {jd_filename}: {e}")
        return None

def run_evaluation():
    master_cv_path = "data/base_cv/master_cv.yaml"
    with open(master_cv_path, "r") as f:
        master_cv_data = yaml.safe_load(f)
    
    master_cv_text = yaml.dump(master_cv_data, default_flow_style=False)
    normalized_master = clean_text(master_cv_text)
    
    jd_files = glob.glob("data/eval_jd/*.yaml")
    
    print(f"--- Starting Comparative Evaluation against {len(jd_files)} JDs ---")
    
    orchestrator = Orchestrator()
    llm_client = LLMClient()
    
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(evaluate_jd, jd_file, master_cv_path, master_cv_text, normalized_master, orchestrator, llm_client) 
            for jd_file in jd_files
        ]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    # Aggregated Comparative Stats
    total_exact = sum(r["exact_match_audit"]["count"] for r in results)
    total_llm = sum(r["llm_judge_audit"]["count"] for r in results)
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "total_jds": len(results),
            "total_exact_hallucinations": total_exact,
            "total_llm_judge_hallucinations": total_llm,
            "average_exact_per_jd": total_exact / len(results) if results else 0,
            "average_llm_per_jd": total_llm / len(results) if results else 0
        },
        "details": results
    }

    print("\n" + "="*50)
    print("COMPARATIVE EVALUATION SUMMARY")
    print("="*50)
    print(f"Total JDs Evaluated:           {summary['metrics']['total_jds']}")
    print(f"Total Exact Match Flagged:     {summary['metrics']['total_exact_hallucinations']}")
    print(f"Total LLM Judge Flagged:       {summary['metrics']['total_llm_judge_hallucinations']}")
    print("-" * 50)
    print(f"Avg Hallucinations (Exact):    {summary['metrics']['average_exact_per_jd']:.2f}")
    print(f"Avg Hallucinations (LLM):      {summary['metrics']['average_llm_per_jd']:.2f}")
    print("="*50)

    os.makedirs("data/eval_results", exist_ok=True)
    report_name = f"comparative_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join("data/eval_results", report_name)
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=4)
    
    print(f"Detailed comparative report saved to: {report_path}")

if __name__ == "__main__":
    run_evaluation()
