import os
import yaml
import json
import glob
from datetime import datetime
from agent.orchestrator import Orchestrator
from agent.llm_client import LLMClient

def run_evaluation():
    # 1. Load Master CV (Source of Truth)
    master_cv_path = "data/base_cv/master_cv.yaml"
    if not os.path.exists(master_cv_path):
        print(f"Error: Master CV not found at {master_cv_path}")
        return

    with open(master_cv_path, "r") as f:
        master_cv_data = yaml.safe_load(f)
    
    # Flatten master CV to a single lowercase string for exact matching
    master_cv_text = yaml.dump(master_cv_data, default_flow_style=False).lower()
    
    # 2. Get all JDs for evaluation
    jd_files = glob.glob("data/eval_jd/*.yaml")
    if not jd_files:
        print("No evaluation JDs found in data/eval_jd/")
        return

    print(f"--- Starting Deterministic Evaluation against {len(jd_files)} JDs ---")
    
    orchestrator = Orchestrator()
    llm_client = LLMClient()
    
    results = []
    total_hallucinations = 0
    jds_with_hallucinations = 0

    for jd_file in jd_files:
        print(f"\n>> Evaluating JD: {os.path.basename(jd_file)}")
        
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
            "personalization_instructions": "Do not add any skills or tools that are not explicitly present in my master CV.",
            "final_ats_cv": None
        }
        
        try:
            final_state = orchestrator.run(initial_state)
            tailored_cv = final_state.get("final_ats_cv")
            
            if not tailored_cv:
                print(f"   [!] Failed to generate CV for {jd_file}")
                continue

            # STEP 1: Extract keywords from Tailored CV that also appear in the JD
            # (Identifying terms the LLM likely "borrowed" or "mapped")
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
            
            # STEP 2: Programmatic Exact Match against Master CV
            hallucinations = []
            for kw in borrowed_keywords:
                # Check if keyword (case-insensitive) exists in the master CV text
                if kw.lower() not in master_cv_text:
                    hallucinations.append(kw)

            h_count = len(hallucinations)
            if h_count > 0:
                jds_with_hallucinations += 1
                total_hallucinations += h_count
                print(f"   [!] Found {h_count} hallucinations (keywords in JD/Tailored but NOT in Master):")
                print(f"       {', '.join(hallucinations)}")
            else:
                print("   [+] No hallucinations detected. All borrowed JD keywords found in Master CV.")

            results.append({
                "jd": os.path.basename(jd_file),
                "borrowed_keywords_count": len(borrowed_keywords),
                "hallucinations": hallucinations,
                "count": h_count
            })
        except Exception as e:
            print(f"   [X] Error during evaluation of {jd_file}: {e}")

    # 4. Summary & Reporting
    summary = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "total_jds_evaluated": len(jd_files),
            "total_hallucination_cases": total_hallucinations,
            "jds_with_hallucinations_count": jds_with_hallucinations,
            "hallucination_rate": jds_with_hallucinations / len(jd_files) if jd_files else 0
        },
        "details": results
    }

    print("\n" + "="*40)
    print("REFINED EVALUATION SUMMARY")
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
