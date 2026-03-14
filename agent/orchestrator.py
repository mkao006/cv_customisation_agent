import json
import yaml
import os
from typing import Literal
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from agent.models import AgentState, OptimizedCV
from agent.llm_client import LLMClient
from tools.job_search import JobSearch
from prompts.templates import CV_GENERATION_TEMPLATE

class Orchestrator:
    def __init__(self, model_name=None):
        self.llm_client = LLMClient(model_name)
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("ingest_inputs", self.ingest_inputs)
        workflow.add_node("validate_jd", self.validate_jd)
        workflow.add_node("research_hub", self.research_hub) 
        workflow.add_node("research_company", self.research_company)
        workflow.add_node("research_best_practices", self.research_best_practices)
        workflow.add_node("research_competing_candidates", self.research_competing_candidates)
        workflow.add_node("evaluate_research", self.evaluate_research)
        workflow.add_node("synthesize_strategy", self.synthesize_strategy)
        workflow.add_node("generate_cv", self.generate_cv)
        workflow.add_node("sanitize_cv", self.sanitize_cv)
        
        workflow.set_entry_point("ingest_inputs")
        workflow.add_edge("ingest_inputs", "validate_jd")
        
        workflow.add_conditional_edges(
            "validate_jd",
            self.route_jd_validation,
            {"valid": "research_hub", "invalid": END}
        )
        
        workflow.add_edge("research_hub", "research_company")
        workflow.add_edge("research_hub", "research_best_practices")
        workflow.add_edge("research_hub", "research_competing_candidates")
        
        workflow.add_edge("research_company", "evaluate_research")
        workflow.add_edge("research_best_practices", "evaluate_research")
        workflow.add_edge("research_competing_candidates", "evaluate_research")
        
        workflow.add_conditional_edges(
            "evaluate_research",
            self.route_after_evaluation,
            {
                "loop_to_research": "research_hub",
                "satisfactory": "synthesize_strategy",
                "max_iterations_reached": "synthesize_strategy"
            }
        )
        
        workflow.add_edge("synthesize_strategy", "generate_cv")
        workflow.add_edge("generate_cv", "sanitize_cv")
        workflow.add_edge("sanitize_cv", END)
        
        return workflow.compile()

    def ingest_inputs(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print("--- Ingesting Inputs ---")
        try:
            jd_text = JobSearch.get_text_from_jd(state["jd_source"])
            cv_source = state["original_cv"]
            if os.path.exists(cv_source) and (cv_source.endswith(".yaml") or cv_source.endswith(".yml")):
                with open(cv_source, "r") as f:
                    data = yaml.safe_load(f)
                    cv_text = yaml.dump(data, default_flow_style=False)
            else:
                cv_text = cv_source
                
            return {
                "jd_text": jd_text, "original_cv": cv_text, "jd_validation_error": None,
                "research_iteration": 0, "max_research_iterations": 3, "research_gaps": "",
                "company_research": "", "best_practices_research": "", "competing_candidates_research": ""
            }
        except Exception as e:
            return {"jd_text": "", "jd_validation_error": f"Failed to reach source: {str(e)}"}

    def validate_jd(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print("--- Validating Job Description ---")
        if state.get("jd_validation_error"): return state
        jd_text = state["jd_text"]
        if len(jd_text.strip()) < 100: return {"jd_validation_error": "JD too short."}
        prompt = f"Is this a job description? Respond YES/NO:\n\n{jd_text[:1000]}"
        response = self.llm_client.invoke_llm(prompt, config=config)
        if "YES" not in response.upper(): return {"jd_validation_error": f"Invalid JD: {response}"}
        print("JD Validation Successful.")
        return {"jd_validation_error": None}

    def research_hub(self, state: AgentState, config: RunnableConfig) -> AgentState:
        return state

    def route_jd_validation(self, state: AgentState) -> Literal["valid", "invalid"]:
        return "invalid" if state.get("jd_validation_error") else "valid"

    def research_company(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print(f"--- [Iter {state['research_iteration']}] Researching Company ---")
        query = f"company culture and goals 2026. Gaps: {state.get('research_gaps', '')}"
        return {"company_research": self.llm_client.search(query, config=config)}

    def research_best_practices(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print(f"--- [Iter {state['research_iteration']}] Researching Trends ---")
        query = f"2026 resume trends for tech. Gaps: {state.get('research_gaps', '')}"
        return {"best_practices_research": self.llm_client.search(query, config=config)}

    def research_competing_candidates(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print(f"--- [Iter {state['research_iteration']}] X-Ray Sourcing ---")
        query = f"LinkedIn profiles for similar roles. Gaps: {state.get('research_gaps', '')}"
        return {"competing_candidates_research": self.llm_client.search(query, config=config)}

    def evaluate_research(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print("--- Evaluating Research (Strong Model) ---")
        prompt = f"Evaluate research against JD. Return JSON {{'evaluation': 'satisfactory'|'needs_refinement', 'gaps': 'string'}}. Data: {state['company_research'][:500]}"
        response = self.llm_client.invoke_llm(prompt, use_strong=True, config=config)
        try:
            if "```json" in response: response = response.split("```json")[1].split("```")[0].strip()
            data = json.loads(response)
            return {"research_evaluation": data["evaluation"], "research_gaps": data.get("gaps", ""), "research_iteration": state["research_iteration"] + 1}
        except Exception:
            return {"research_evaluation": "satisfactory", "research_iteration": state["research_iteration"] + 1}

    def route_after_evaluation(self, state: AgentState) -> Literal["loop_to_research", "satisfactory", "max_iterations_reached"]:
        if state["research_evaluation"] == "satisfactory": return "satisfactory"
        if state["research_iteration"] >= state["max_research_iterations"]: return "max_iterations_reached"
        return "loop_to_research"

    def synthesize_strategy(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print("--- Synthesizing Strategy (Strong Model) ---")
        prompt = f"Create resume strategy. JD: {state['jd_text'][:1000]} CV: {state['original_cv'][:1000]}"
        return {"application_strategy": self.llm_client.invoke_llm(prompt, use_strong=True, config=config)}

    def generate_cv(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print("--- Generating ATS-Optimized CV ---")
        structured_llm = self.llm_client.with_structured_output(OptimizedCV)
        prompt = CV_GENERATION_TEMPLATE.format(
            strategy=state['application_strategy'], original_cv=state['original_cv'],
            jd_text=state['jd_text'], personalization_instructions=state.get('personalization_instructions', '')
        )
        # For structured output, we pass config to invoke()
        final_cv = structured_llm.invoke(prompt, config=config)
        return {"final_ats_cv": final_cv}

    def sanitize_cv(self, state: AgentState, config: RunnableConfig) -> AgentState:
        print("--- Auditing CV for Hallucinations (Strong Model) ---")
        cv = state["final_ats_cv"]
        if not cv: return state

        structured_llm = self.llm_client.with_structured_output(OptimizedCV, use_strong=True)
        
        audit_prompt = f"""
        You are a strict integrity auditor. Compare the 'Tailored CV' against the 'Master CV'.
        MASTER CV: {state['original_cv']}
        TAILORED CV TO AUDIT: {cv.model_dump_json()}
        REMOVE any tool/skill not in Master CV. Return valid JSON.
        """
        sanitized_cv = structured_llm.invoke(audit_prompt, config=config)
        return {
            "final_ats_cv": sanitized_cv,
            "cv_audit_log": "CV was audited and sanitized against Master CV using the Strong Model."
        }

    def run(self, initial_state: AgentState):
        return self.workflow.invoke(initial_state)

    def save_graph_image(self, output_path: str = "workflow.png"):
        try:
            img_data = self.workflow.get_graph().draw_mermaid_png(
                max_retries=5,
                retry_delay=2.0
            )
            with open(output_path, "wb") as f: f.write(img_data)
            print(f"--- Workflow visualization saved to {output_path} ---")
        except Exception as e: print(f"Could not generate graph image: {e}")
