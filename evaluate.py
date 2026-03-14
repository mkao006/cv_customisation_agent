import os
import yaml
import json
import glob
import re
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from opentelemetry import trace
from agent.orchestrator import Orchestrator
from agent.llm_client import LLMClient
from tools.cv_builder import CVBuilder
from config.settings import Settings

tracer = trace.get_tracer(__name__)
OPENINFERENCE_SPAN_KIND = "openinference.span.kind"

def get_git_revision_hash() -> str:
    try: return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
    except Exception: return "no-git"

def clean_text(text):
    return re.sub(r'\s+', ' ', str(text).lower()).strip()

def is_exact_match(keyword, master_text):
    kw = clean_text(keyword)
    pattern = rf"\b{re.escape(kw)}\b"
    return re.search(pattern, master_text) is not None

def check_yoe_hallucination(cv_text, start_year=2010):
    current_year = datetime.now().year
    ground_truth_yoe = current_year - start_year
    yoe_patterns = [r"(\d+)\+?\s*(?:years?|yrs)(?:\s+of)?\s+(?:experience|exp)", r"(?:with|over)\s+(\d+)\+?\s*(?:years?|yrs)"]
    mentions = []
    for pattern in yoe_patterns:
        found = re.findall(pattern, cv_text, re.IGNORECASE)
        mentions.extend([int(m) for m in found])
    if not mentions: return {"status": "pass", "message": "No YoE mentions found.", "ground_truth": ground_truth_yoe}
    max_mentioned = max(mentions)
    if max_mentioned > ground_truth_yoe:
        return {"status": "fail", "message": f"YoE Hallucination: Claims {max_mentioned}, truth {ground_truth_yoe}.", "ground_truth": ground_truth_yoe, "claimed": max_mentioned}
    return {"status": "pass", "message": "YoE within bounds.", "ground_truth": ground_truth_yoe}

def check_metric_hallucination(cv_text, master_text):
    metric_pattern = r"(\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?[MBKk]?|\d+\s*(?:hour|min|sec|day)s?)"
    cv_metrics = set(re.findall(metric_pattern, cv_text, re.IGNORECASE))
    master_metrics = set(re.findall(metric_pattern, master_text, re.IGNORECASE))
    hallucinated_metrics = [m for m in cv_metrics if m not in master_metrics]
    if hallucinated_metrics:
        return {"status": "fail", "message": f"Metric Hallucination: {hallucinated_metrics}", "hallucinations": hallucinated_metrics}
    return {"status": "pass", "message": "No invented metrics found."}

def check_quality_audit(cv_text, jd_text, llm_client, config):
    """Performs a qualitative scoring of the CV on a 1-5 scale."""
    quality_prompt = f"""
    You are an elite technical recruiter. Score the following CV against the JD on a scale of 1 to 5.
    
    JD:
    {jd_text[:1000]}
    
    CV:
    {cv_text}
    
    SCORING CRITERIA:
    1. **Impact & Keywords**: (1-5) 5 = Highly quantified impact using action verbs and matching key JD terms.
    2. **Layout & Hierarchy**: (1-5) 5 = Logical hierarchy, standard headers, 100% professional tone.
    3. **Technical Context**: (1-5) 5 = Skills are clearly connected to infrastructure, scale, and business value.
    
    Return your answer ONLY as a JSON object:
    {{
        "impact_score": int,
        "layout_score": int,
        "context_score": int,
        "total_avg": float,
        "justification": "short 1-sentence critique"
    }}
    """
    response = llm_client.invoke_llm(quality_prompt, config=config, use_strong=True)
    try:
        # Clean JSON and return
        data = json.loads(re.sub(r"```json|```", "", response).strip())
        return data
    except Exception:
        return {"impact_score": 0, "layout_score": 0, "context_score": 0, "total_avg": 0, "justification": "Audit failed"}

def evaluate_jd(jd_file, experiment_id, experiment_dir, master_cv_path, master_cv_text, normalized_master, orchestrator, llm_client):
    jd_filename = os.path.basename(jd_file)
    jd_base = jd_filename.replace(".yaml", "").replace(".yml", "")
    with tracer.start_as_current_span(f"Evaluate JD: {jd_filename}") as span:
        span.set_attribute(OPENINFERENCE_SPAN_KIND, "CHAIN")
        print(f">> Evaluating JD: {jd_filename}")
        trace_config = {"callbacks": []}
        
        with open(jd_file, "r") as f:
            jd_data = yaml.safe_load(f)
            jd_text = yaml.dump(jd_data, default_flow_style=False)

        try:
            final_state = orchestrator.run({
                "original_cv": master_cv_path, "jd_source": jd_file, "jd_text": "", "jd_validation_error": None,
                "research_iteration": 0, "max_research_iterations": 1, "research_gaps": "",
                "company_research": "", "best_practices_research": "", "competing_candidates_research": "",
                "application_strategy": "", "personalization_instructions": "STRICT ADHERENCE TO MASTER CV METRICS.",
                "final_ats_cv": None
            })
            tailored_cv = final_state.get("final_ats_cv")
            if not tailored_cv: return None

            jd_output_dir = os.path.join(experiment_dir, "artifacts", jd_base)
            os.makedirs(jd_output_dir, exist_ok=True)
            cv_md = CVBuilder.generate_cv_markdown(tailored_cv)
            with open(os.path.join(jd_output_dir, "TAILORED_CV.md"), "w") as f: f.write(cv_md)
            CVBuilder.render_pdf(cv_md, os.path.join(jd_output_dir, "TAILORED_CV.pdf"))

            # Audits
            yoe_audit = check_yoe_hallucination(cv_md)
            metric_audit = check_metric_hallucination(cv_md, master_cv_text)
            quality_audit = check_quality_audit(cv_md, jd_text, llm_client, trace_config)

            extract_prompt = f"Extract technical skills from this CV: {tailored_cv.skills}. Return JSON list of strings only."
            extraction_response = llm_client.invoke_llm(extract_prompt, config=trace_config)
            extracted_keywords = json.loads(re.sub(r"```json|```", "", extraction_response).strip())
            exact_match_hallucinations = [kw for kw in extracted_keywords if not is_exact_match(kw, normalized_master)]

            judge_prompt = f"Audit keywords against Master CV. Identify true hallucinations. Master CV: {master_cv_text} Keywords: {extracted_keywords}. Return JSON: {{'hallucinations': [], 'explanation': ''}}"
            judge_response = llm_client.invoke_llm(judge_prompt, config=trace_config)
            llm_judge_data = json.loads(re.sub(r"```json|```", "", judge_response).strip())

            return {
                "jd": jd_filename,
                "yoe_audit": yoe_audit,
                "metric_audit": metric_audit,
                "quality_audit": quality_audit,
                "exact_match_audit": {"hallucinations": exact_match_hallucinations, "count": len(exact_match_hallucinations)},
                "llm_judge_audit": {"hallucinations": llm_judge_data.get("hallucinations", []), "count": len(llm_judge_data.get("hallucinations", []))}
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
    with open(master_cv_path, "r") as f: master_cv_data = yaml.safe_load(f)
    master_cv_text = yaml.dump(master_cv_data, default_flow_style=False)
    normalized_master = clean_text(master_cv_text)
    jd_files = glob.glob("data/eval_jd/*.yaml")
    Settings.init_tracing()
    orchestrator = Orchestrator()
    llm_client = LLMClient()
    results = []
    print(f"\n--- Starting Experiment: {experiment_id} ---")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(evaluate_jd, f, experiment_id, experiment_dir, master_cv_path, master_cv_text, normalized_master, orchestrator, llm_client) for f in jd_files]
        for future in as_completed(futures):
            res = future.result()
            if res: results.append(res)

    summary = {
        "experiment_id": experiment_id,
        "metrics": {
            "total_jds": len(results),
            "yoe_hallucinations": sum(1 for r in results if r["yoe_audit"]["status"] == "fail"),
            "metric_hallucinations": sum(1 for r in results if r["metric_audit"]["status"] == "fail"),
            "avg_quality_score": sum(r["quality_audit"]["total_avg"] for r in results) / len(results) if results else 0
        },
        "details": results
    }

    # PRINT SUMMARY TABLE
    print("\n" + "="*80)
    print(f"EXPERIMENT SUMMARY: {experiment_id}")
    print("="*80)
    print(f"{'JD Filename':<25} | {'YoE':<5} | {'Metric':<6} | {'Qual Score':<10} | {'Justification'}")
    print("-" * 80)
    for r in results:
        yoe = "FAIL" if r["yoe_audit"]["status"] == "fail" else "PASS"
        metric = "FAIL" if r["metric_audit"]["status"] == "fail" else "PASS"
        score = f"{r['quality_audit']['total_avg']:.1f}/5"
        just = r['quality_audit']['justification'][:30] + "..."
        print(f"{r['jd']:<25} | {yoe:<5} | {metric:<6} | {score:<10} | {just}")
    print("-" * 80)
    print(f"OVERALL AVG QUALITY: {summary['metrics']['avg_quality_score']:.2f} / 5.0")
    print("="*80)

    with open(os.path.join(experiment_dir, "experiment_results.json"), "w") as f: json.dump(summary, f, indent=4)
    print(f"Artifacts: {experiment_dir}\n")

if __name__ == "__main__":
    run_evaluation()
