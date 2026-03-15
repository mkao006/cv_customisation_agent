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
from agent.models import JudgeAudit, FaithfulnessAudit
from tools.cv_builder import CVBuilder
from tools.cv_analyzer import CVAnalyzer
from tools.faithfulness_evaluator import FaithfulnessEvaluator
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
        return {"status": "fail", "message": f"Metric Hallucination: {hallucinated_metrics}"}
    return {"status": "pass", "message": "No invented metrics found."}

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
                "application_strategy": "", "personalization_instructions": "STRICT ADHERENCE TO MASTER CV RECORDS.",
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
            ats_audit = CVAnalyzer.run_full_audit(tailored_cv, cv_md, jd_text, master_cv_text, llm_client, trace_config)

            # Context-Aware Judge Pass
            judge_prompt = f"Audit keywords against Master Records. Flag tech NOT mentioned in Master. MASTER: {master_cv_text} CV: {cv_md}"
            structured_judge = llm_client.with_structured_output(JudgeAudit, use_strong=True)
            llm_judge_data = structured_judge.invoke(judge_prompt, config=trace_config)

            # Faithfulness Evaluation (using Gemini to avoid same-model bias)
            faithfulness_evaluator = FaithfulnessEvaluator()
            faithfulness_audit = faithfulness_evaluator.evaluate(
                source_text=master_cv_text,
                generated_cv=cv_md,
                config=trace_config
            )

            return {
                "jd": jd_filename,
                "yoe_audit": yoe_audit,
                "metric_audit": metric_audit,
                "ats_audit": ats_audit.model_dump(),
                "llm_judge_audit": {"hallucinations": llm_judge_data.hallucinations, "count": llm_judge_data.count},
                "faithfulness_audit": faithfulness_audit.model_dump(),
                "overall_status": ats_audit.overall_recommendation
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

    # Calculate faithfulness metrics
    faithfulness_scores = [r["faithfulness_audit"]["faithfulness_score"] for r in results if "faithfulness_audit" in r]
    avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0
    faithfulness_failures = sum(1 for r in results if "faithfulness_audit" in r and r["faithfulness_audit"]["faithfulness_score"] < 98.0)

    summary = {
        "experiment_id": experiment_id,
        "metrics": {
            "total_jds": len(results),
            "yoe_hallucinations": sum(1 for r in results if r["yoe_audit"]["status"] == "fail"),
            "metric_hallucinations": sum(1 for r in results if r["metric_audit"]["status"] == "fail"),
            "faithfulness_failures": faithfulness_failures,
            "avg_evidence_score": sum(r["ats_audit"]["evidence_score"] for r in results) / len(results) if results else 0,
            "avg_alignment_score": sum(r["ats_audit"]["alignment_score"] for r in results) / len(results) if results else 0,
            "avg_faithfulness_score": avg_faithfulness
        },
        "details": results
    }

    # PRINT SUMMARY TABLE
    print("\n" + "="*100)
    print(f"HYBRID ATS EVALUATION SUMMARY: {experiment_id}")
    print("="*100)
    print(f"{'JD Filename':<20} | {'YoE':<5} | {'Metric':<6} | {'Faith':<6} | {'Evidence':<8} | {'Align':<7} | {'Status'}")
    print("-" * 100)
    for r in results:
        yoe = "FAIL" if r["yoe_audit"]["status"] == "fail" else "PASS"
        metric = "FAIL" if r["metric_audit"]["status"] == "fail" else "PASS"
        a = r["ats_audit"]
        faith_score = r.get("faithfulness_audit", {}).get("faithfulness_score", 0.0)
        faith_str = f"{faith_score:.0f}" if faith_score >= 0 else "N/A"
        print(f"{r['jd']:<20} | {yoe:<5} | {metric:<6} | {faith_str:<6} | {a['evidence_score']:<8.0f} | {a['alignment_score']:<7} | {r['overall_status']}")
    print("-" * 100)
    print(f"AVG EVIDENCE: {summary['metrics']['avg_evidence_score']:.1f}%  |  AVG ALIGNMENT: {summary['metrics']['avg_alignment_score']:.1f}%  |  AVG FAITHFULNESS: {summary['metrics']['avg_faithfulness_score']:.1f}%")
    print("="*100)

    with open(os.path.join(experiment_dir, "experiment_results.json"), "w") as f: json.dump(summary, f, indent=4)
    print(f"Artifacts: {experiment_dir}\n")

if __name__ == "__main__":
    run_evaluation()
