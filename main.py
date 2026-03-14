import os
import argparse
import json
from datetime import datetime
from config.settings import Settings
from agent.orchestrator import Orchestrator
from tools.cv_builder import CVBuilder

def main():
    parser = argparse.ArgumentParser(description="AI Job Research & CV Tailoring Agent")
    parser.add_argument("--cv", default="data/base_cv/master_cv.yaml", help="Path to original CV")
    parser.add_argument("--jd", default="data/eval_jd/apple_mle.yaml", help="JD URL or path")
    parser.add_argument("--model", help="Gemini model version")
    parser.add_argument("--pdf", help="Render an existing Markdown file to PDF")
    parser.add_argument("--personalize", help="Additional custom instruction to personalize the CV")
    parser.add_argument("--visualize", action="store_true", help="Save the agent's workflow as an image (workflow.png)")
    args = parser.parse_args()

    # Case 1: Just Render PDF from Markdown
    if args.pdf:
        CVBuilder.render_pdf(args.pdf, args.pdf.replace(".md", ".pdf"))
        return

    # Case 2: Visualize the Graph
    if args.visualize:
        orchestrator = Orchestrator(model_name=args.model)
        orchestrator.save_graph_image("workflow.png")
        return

    # Case 2: Run the full Agent
    Settings.init_tracing()
    orchestrator = Orchestrator(model_name=args.model)
    initial_state = {
        "original_cv": args.cv,
        "jd_source": args.jd,
        "jd_text": "",
        "company_research": "",
        "best_practices_research": "",
        "application_strategy": "",
        "personalization_instructions": args.personalize if args.personalize else "",
        "final_ats_cv": None
    }
    
    final_state = orchestrator.run(initial_state)
    
    # Check for JD validation errors
    if final_state.get("jd_validation_error"):
        print(f"\n--- Process Aborted: {final_state['jd_validation_error']} ---")
        return

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(Settings.OUTPUT_DIR, timestamp)
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Export Strategy Report
    strategy_md = f"# Strategy Report\n\n## Strategy\n{final_state['application_strategy']}\n\n## Research\n{final_state['company_research']}"
    strategy_md_path = os.path.join(output_dir, "STRATEGY_REPORT.md")
    with open(strategy_md_path, "w") as f:
        f.write(strategy_md)
    CVBuilder.render_pdf(strategy_md, os.path.join(output_dir, "STRATEGY_REPORT.pdf"), is_cv=False)
    
    # 2. Export Tailored CV
    cv_obj = final_state["final_ats_cv"]
    if cv_obj:
        cv_md = CVBuilder.generate_cv_markdown(cv_obj)
        cv_md_path = os.path.join(output_dir, "TAILORED_CV.md")
        with open(cv_md_path, "w") as f:
            f.write(cv_md)
        CVBuilder.render_pdf(cv_md, os.path.join(output_dir, "TAILORED_CV.pdf"), is_cv=True)
        
    # 3. Save Metadata
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump({
            "cv": args.cv, 
            "jd": args.jd, 
            "standard_model": orchestrator.llm_client.standard_model_name, 
            "strong_model": orchestrator.llm_client.strong_model_name,
            "personalize": args.personalize, 
            "timestamp": timestamp
        }, f, indent=4)
    
    print(f"\n--- Run complete. All files saved to {output_dir} ---")

if __name__ == "__main__":
    main()
