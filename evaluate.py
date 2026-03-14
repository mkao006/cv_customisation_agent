import os
import yaml
import json
import glob
import re
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from opentelemetry import trace
from openinference.semantic_conventions.trace import SpanAttributes
from agent.orchestrator import Orchestrator
from agent.llm_client import LLMClient
from tools.cv_builder import CVBuilder
from config.settings import Settings

tracer = trace.get_tracer(__name__)

def get_git_revision_hash() -> str:
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
    except Exception:
        return "no-git"

def clean_text(text):
    return re.sub(r'\s+', ' ', str(text).lower()).strip()

def is_exact_match(keyword, master_text):
    kw = clean_text(keyword)
    pattern = rf"\b{re.escape(kw)}\b"
    return re.search(pattern, master_text) is not None

def evaluate_jd(jd_file, experiment_id, experiment_dir, master_cv_path, master_cv_text, normalized_master, orchestrator, llm_client):
    """Evaluates a single JD, saves artifacts, and performs audits within a single trace."""
    jd_filename = os.path.basename(jd_file)
    jd_base = jd_filename.replace(".yaml", "").replace(".yml", "")
    
    with tracer.start_as_current_span(f"Evaluate JD: {jd_filename}") as span:
        # Set OpenInference span kind to 'CHAIN' for better UI categorization
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "CHAIN")
        span.set_attribute("experiment_id", experiment_id)
        span.set_attribute("jd_file", jd_filename)
        
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
                return None

            # Save Artifacts
            jd_output_dir = os.path.join(experiment_dir, "artifacts", jd_base)
            os.makedirs(jd_output_dir, exist_ok=True)
            
            cv_md = CVBuilder.generate_cv_markdown(tailored_cv)
            cv_md_path = os.path.join(jd_output_dir, "TAILORED_CV.md")
            with open(cv_md_path, "w") as f:
                f.write(cv_md)
            CVBuilder.render_pdf(cv_md, os.path.join(jd_output_dir, "TAILORED_CV.pdf"))
            
            strategy_md = f"# Strategy Report for {jd_base}\n\n{final_state['application_strategy']}"
            with open(os.path.join(jd_output_dir, "STRATEGY.md"), "w") as f:
                f.write(strategy_md)

            # Audit
            extract_prompt = f"Extract a list of technical skills and tools from this CV: {tailored_cv.skills}. Return JSON list of strings only."
            extraction_response = llm_client.invoke_llm(extract_prompt)
            if "```json" in extraction_response:
                extraction_response = extraction_response.split("```json")[1].split("```")[0].strip()
            elif "```" in extraction_response:
                extraction_response = extraction_response.split("```")[1].split("```")[0].strip()
            extracted_keywords = json.loads(extraction_response)
            
            exact_match_hallucinations = [kw for kw in extracted_keywords if not is_exact_match(kw, normalized_master)]

            judge_prompt = f"Audit keywords against Master CV. Identify true hallucinations. Master CV: {master_cv_text} Keywords: {extracted_keywords}. Return JSON: {{'hallucinations': [], 'explanation': ''}}"
            judge_response = llm_client.invoke_llm(judge_prompt)
            if "```json" in judge_response: judge_response = judge_response.split("```json")[1].split("```")[0].strip()
            elif "```" in judge_response: judge_response = judge_response.split("```")[1].split("```")[0].strip()
            llm_judge_data = json.loads(judge_response)

            return {
                "jd": jd_filename,
                "output_path": jd_output_dir,
                "total_keywords": len(extracted_keywords),
                "exact_match_audit": {"hallucinations": exact_match_hallucinations, "count": len(exact_match_hallucinations)},
                "llm_judge_audit": {"hallucinations": llm_judge_data.get("hallucinations", []), "count": len(llm_judge_data.get("hallucinations", [])), "explanation": llm_judge_data.get("explanation", "")}
            }
        except Exception as e:
            print(f"   [X] Error during evaluation of {jd_filename}: {e}")
            return None

def run_evaluation():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_hash = get_git_revision_hash()
    experiment_id = f"{timestamp}_{git_hash}"
    experiment_dir = os.path.join("data/eval_results", experiment_id)
    os.makedirs(experiment_dir, exist_ok=True)

    master_cv_path = "data/base_cv/master_cv.yaml"
    with open(master_cv_path, "r") as f:
        master_cv_data = yaml.safe_load(f)
    master_cv_text = yaml.dump(master_cv_data, default_flow_style=False)
    normalized_master = clean_text(master_cv_text)
    
    jd_files = glob.glob("data/eval_jd/*.yaml")
    Settings.init_tracing()
    
    print(f"--- Starting Experiment: {experiment_id} ({len(jd_files)} JDs) ---")
    
    orchestrator = Orchestrator()
    llm_client = LLMClient()
    
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(evaluate_jd, f, experiment_id, experiment_dir, master_cv_path, master_cv_text, normalized_master, orchestrator, llm_client) for f in jd_files]
        for future in as_completed(futures):
            res = future.result()
            if res: results.append(res)

    summary = {
        "experiment_id": experiment_id,
        "timestamp": datetime.now().isoformat(),
        "git_commit": git_hash,
        "metrics": {
            "total_jds": len(results),
            "total_exact_hallucinations": sum(r["exact_match_audit"]["count"] for r in results),
            "total_llm_judge_hallucinations": sum(r["llm_judge_audit"]["count"] for r in results)
        },
        "details": results
    }

    report_path = os.path.join(experiment_dir, "experiment_results.json")
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=4)
    
    print(f"\n--- Experiment Complete: {experiment_id} ---")
    print(f"Artifacts and report saved to: {experiment_dir}")

if __name__ == "__main__":
    run_evaluation()
