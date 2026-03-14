import os
import yaml
import json
import glob
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent.orchestrator import Orchestrator
from agent.llm_client import LLMClient

def evaluate_jd(jd_file, master_cv_path, master_cv_text, orchestrator, llm_client):
    """Evaluates a single JD against the master CV using semantic matching."""
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
        "personalization_instructions": "Focus on strict adherence to the original CV content. Do not add skills or tools I do not have in my master CV.",
        "final_ats_cv": None
    }
    
    try:
        final_state = orchestrator.run(initial_state)
        tailored_cv = final_state.get("final_ats_cv")
        
        if not tailored_cv:
            print(f"   [!] Failed to generate CV for {jd_filename}")
            return None

        # STEP 1: Extract keywords that appear in both Tailored CV and JD
        extract_prompt = f"""
        Identify all technical keywords, tools, frameworks, and methodologies that appear in BOTH the Tailored CV and the Job Description.
        
        TAILORED CV SKILLS & SUMMARY:
        {tailored_cv.skills}
        {tailored_cv.summary}
        
        JOB DESCRIPTION:
        {jd_text[:2000]}
        
        Return your answer ONLY as a JSON list of strings: ["keyword1", "keyword2", ...]
        """
        
        extraction_response = llm_client.invoke_llm(extract_prompt)
        if "```json" in extraction_response:
            extraction_response = extraction_response.split("```json")[1].split("```")[0].strip()
        elif "```" in extraction_response:
            extraction_response = extraction_response.split("```")[1].split("```")[0].strip()
        
        borrowed_keywords = json.loads(extraction_response)
        
        # STEP 2: Semantic Hallucination Check via LLM Judge
        # We ask the LLM to filter the borrowed keywords against the Master CV
        judge_prompt = f"""
        You are an expert recruitment auditor. Compare a list of keywords from a 'Tailored CV' against a 'Master CV' (Source of Truth).
        
        MASTER CV CONTENT:
        {master_cv_text}
        
        KEYWORDS TO AUDIT:
        {borrowed_keywords}
        
        TASK:
        Identify which keywords are 'Hallucinations'.
        - NOT A HALLUCINATION: Industry synonyms, common tasks associated with listed roles (e.g., 'model development' if they are a 'Data Scientist'), or direct mappings.
        - IS A HALLUCINATION: Specific tools, software, or advanced methodologies NOT mentioned or reasonably inferred from the Master CV (e.g., claiming 'Kubernetes' or 'Reinforcement Learning' if it's nowhere in the Master CV).
        
        Return your answer ONLY as a JSON object:
        {{
            "hallucinations": ["list", "of", "true", "hallucinations"],
            "valid_mappings": ["list", "of", "keywords", "that", "were", "actually", "valid", "inferences"],
            "explanation": "briefly explain the worst hallucination found"
        }}
        """
        
        judge_response = llm_client.invoke_llm(judge_prompt)
        if "```json" in judge_response:
            judge_response = judge_response.split("```json")[1].split("```")[0].strip()
        elif "```" in judge_response:
            judge_response = judge_response.split("```")[1].split("```")[0].strip()
            
        audit_data = json.loads(judge_response)
        hallucinations = audit_data.get("hallucinations", [])
        h_count = len(hallucinations)

        if h_count > 0:
            print(f"   [!] {jd_filename}: Found {h_count} true hallucinations: {', '.join(hallucinations)}")
        else:
            print(f"   [+] {jd_filename}: No true hallucinations detected. {len(audit_data.get('valid_mappings', []))} keywords were validated as reasonable inferences.")

        return {
            "jd": jd_filename,
            "borrowed_keywords_count": len(borrowed_keywords),
            "hallucinations": hallucinations,
            "count": h_count,
            "explanation": audit_data.get("explanation", "")
        }
    except Exception as e:
        print(f"   [X] Error during evaluation of {jd_filename}: {e}")
        return None

def run_evaluation():
    # 1. Load Master CV
    master_cv_path = "data/base_cv/master_cv.yaml"
    if not os.path.exists(master_cv_path):
        print(f"Error: Master CV not found at {master_cv_path}")
        return

    with open(master_cv_path, "r") as f:
        master_cv_data = yaml.safe_load(f)
    
    master_cv_text = yaml.dump(master_cv_data, default_flow_style=False)
    
    # 2. Get all JDs for evaluation
    jd_files = glob.glob("data/eval_jd/*.yaml")
    if not jd_files:
        print("No evaluation JDs found in data/eval_jd/")
        return

    print(f"--- Starting Parallel Semantic Evaluation against {len(jd_files)} JDs ---")
    
    orchestrator = Orchestrator()
    llm_client = LLMClient()
    
    results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(evaluate_jd, jd_file, master_cv_path, master_cv_text, orchestrator, llm_client) 
            for jd_file in jd_files
        ]
        
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    # 3. Summary & Reporting
    total_hallucinations = sum(r["count"] for r in results)
    jds_with_hallucinations = sum(1 for r in results if r["count"] > 0)
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "total_jds_evaluated": len(jd_files),
            "total_processed": len(results),
            "total_hallucination_cases": total_hallucinations,
            "jds_with_hallucinations_count": jds_with_hallucinations,
            "hallucination_rate": jds_with_hallucinations / len(results) if results else 0
        },
        "details": results
    }

    print("\n" + "="*40)
    print("SEMANTIC EVALUATION SUMMARY")
    print("="*40)
    print(f"Total JDs Evaluated:      {summary['metrics']['total_jds_evaluated']}")
    print(f"Total Hallucination Count: {summary['metrics']['total_hallucination_cases']}")
    print(f"Affected JDs Count:       {summary['metrics']['jds_with_hallucinations_count']}")
    print(f"Hallucination Rate:       {summary['metrics']['hallucination_rate']:.2%}")
    print("="*40)

    os.makedirs("data/eval_results", exist_ok=True)
    report_name = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join("data/eval_results", report_name)
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=4)
    
    print(f"Detailed report saved to: {report_path}")

if __name__ == "__main__":
    run_evaluation()
