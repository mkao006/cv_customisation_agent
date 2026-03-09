import json
import yaml
import os
from typing import Literal
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

        # Add Nodes
        workflow.add_node("ingest_inputs", self.ingest_inputs)
        workflow.add_node("validate_jd", self.validate_jd)
        workflow.add_node("research_hub", self.research_hub) # Junction for parallel fan-out
        workflow.add_node("research_company", self.research_company)
        workflow.add_node("research_best_practices", self.research_best_practices)
        workflow.add_node("research_competitors", self.research_competitors)
        workflow.add_node("evaluate_research", self.evaluate_research)
        workflow.add_node("synthesize_strategy", self.synthesize_strategy)
        workflow.add_node("generate_cv", self.generate_cv)

        # Define Edges
        workflow.set_entry_point("ingest_inputs")
        workflow.add_edge("ingest_inputs", "validate_jd")

        # 1. JD Validation -> END or Hub
        workflow.add_conditional_edges(
            "validate_jd",
            self.route_jd_validation,
            {
                "valid": "research_hub",
                "invalid": END
            }
        )

        # 2. Hub -> Parallel Research (Fan-out)
        workflow.add_edge("research_hub", "research_company")
        workflow.add_edge("research_hub", "research_best_practices")
        workflow.add_edge("research_hub", "research_competitors")

        # 3. Parallel Research -> Evaluate (Fan-in)
        workflow.add_edge("research_company", "evaluate_research")
        workflow.add_edge("research_best_practices", "evaluate_research")
        workflow.add_edge("research_competitors", "evaluate_research")

        # 4. Evaluation -> END or Strategy or Hub (Loop)
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
        workflow.add_edge("generate_cv", END)

        return workflow.compile()

    # --- Node Logic ---

    def ingest_inputs(self, state: AgentState) -> AgentState:
        print("--- Ingesting Inputs ---")
        try:
            jd_text = JobSearch.get_text_from_jd(state["jd_source"])

            # Directly load YAML if it's a YAML file, else treat as raw text or path
            cv_source = state["original_cv"]
            if os.path.exists(cv_source) and (cv_source.endswith(".yaml") or cv_source.endswith(".yml")):
                with open(cv_source, "r") as f:
                    data = yaml.safe_load(f)
                    cv_text = yaml.dump(data, default_flow_style=False)
            else:
                cv_text = cv_source

            return {
                "jd_text": jd_text,
                "original_cv": cv_text,
                "jd_validation_error": None,
                "research_iteration": 0,
                "max_research_iterations": 1,
                "research_gaps": "",
                "company_research": "",
                "best_practices_research": "",
                "competitor_research": ""
            }
        except Exception as e:
            return {"jd_text": "", "jd_validation_error": f"Failed to reach or read source: {str(e)}"}

    def validate_jd(self, state: AgentState) -> AgentState:
        print("--- Validating Job Description ---")
        if state.get("jd_validation_error"):
            print(f"Aborting: {state['jd_validation_error']}")
            return state

        jd_text = state["jd_text"]
        if len(jd_text.strip()) < 100:
            return {"jd_validation_error": "Job description text is too short or empty."}

        prompt = f"Does the following text appear to be a job description? Respond with 'YES' or 'NO' and a brief reason why.\n\nTEXT:\n{jd_text[:1000]}"
        response = self.llm_client.invoke_llm(prompt)

        if "YES" not in response.upper():
            error_msg = f"Content does not appear to be a valid Job Description. Reason: {response}"
            print(f"Aborting: {error_msg}")
            return {"jd_validation_error": error_msg}

        print("JD Validation Successful.")
        return {"jd_validation_error": None}

    def research_hub(self, state: AgentState) -> AgentState:
        """Pass-through junction for parallel research."""
        return state

    def route_jd_validation(self, state: AgentState) -> Literal["valid", "invalid"]:
        if state.get("jd_validation_error"):
            return "invalid"
        return "valid"

    def research_company(self, state: AgentState) -> AgentState:
        print(f"--- [Iter {state['research_iteration']}] Researching Company & Role ---")
        gaps = state.get("research_gaps", "")
        prompt = f"Extract the company name and job title from this Job Description:\n\n{state['jd_text'][:1000]}"
        info = self.llm_client.invoke_llm(prompt)
        query = f"{info} company culture recent news and goals 2026. Focus: {gaps}"
        results = self.llm_client.search(query)
        return {"company_research": results}

    def research_best_practices(self, state: AgentState) -> AgentState:
        print(f"--- [Iter {state['research_iteration']}] Researching 2026 Best Practices ---")
        gaps = state.get("research_gaps", "")
        query = f"Latest 2026 interview and resume best practices for tech roles. Focus: {gaps}"
        results = self.llm_client.search(query)
        return {"best_practices_research": results}

    def research_competitors(self, state: AgentState) -> AgentState:
        print(f"--- [Iter {state['research_iteration']}] Researching Competitor Profiles (X-Ray) ---")
        gaps = state.get("research_gaps", "")
        prompt = f"Identify the key job title and required core skills from this JD:\n\n{state['jd_text'][:500]}"
        role_info = self.llm_client.invoke_llm(prompt)
        query = f'site:linkedin.com/in/ "{role_info}" skills profiles 2025 2026. Focus: {gaps}'
        results = self.llm_client.search(query)
        return {"competitor_research": results}

    def evaluate_research(self, state: AgentState) -> AgentState:
        print("--- Evaluating Combined Research ---")
        prompt = f"""
        Review the following combined research for the JD: {state['jd_text'][:500]}

        COMPANY: {state['company_research'][:800]}
        BEST PRACTICES: {state['best_practices_research'][:800]}
        COMPETITORS: {state['competitor_research'][:800]}

        Evaluate if this is sufficient for a tailored CV.
        Identify specific missing details (Gaps) if refinement is needed.
        Return JSON: {{"evaluation": "satisfactory" | "needs_refinement", "gaps": "string"}}
        """
        response = self.llm_client.invoke_llm(prompt)
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            data = json.loads(response)
            return {
                "research_evaluation": data["evaluation"],
                "research_gaps": data.get("gaps", ""),
                "research_iteration": state["research_iteration"] + 1
            }
        except Exception:
            return {"research_evaluation": "satisfactory", "research_iteration": state["research_iteration"] + 1}

    def route_after_evaluation(self, state: AgentState) -> Literal["loop_to_research", "satisfactory", "max_iterations_reached"]:
        if state["research_evaluation"] == "satisfactory":
            return "satisfactory"
        if state["research_iteration"] >= state["max_research_iterations"]:
            print("--- Max research iterations reached. Proceeding with current data. ---")
            return "max_iterations_reached"

        print(f"--- Gaps identified: {state['research_gaps']}. Looping back... ---")
        return "loop_to_research"

    def synthesize_strategy(self, state: AgentState) -> AgentState:
        print("--- Synthesizing Strategy ---")
        prompt = f"""
        Create a targeted resume strategy based on:
        JD: {state['jd_text'][:2000]}
        COMPANY: {state['company_research'][:1500]}
        PRACTICES: {state['best_practices_research'][:1500]}
        COMPETITORS: {state['competitor_research'][:1500]}
        CV: {state['original_cv'][:2000]}
        """
        strategy = self.llm_client.invoke_llm(prompt)
        return {"application_strategy": strategy}

    def generate_cv(self, state: AgentState) -> AgentState:
        print("--- Generating ATS-Optimized CV ---")
        structured_llm = self.llm_client.with_structured_output(OptimizedCV)
        prompt = CV_GENERATION_TEMPLATE.format(
            strategy=state['application_strategy'],
            original_cv=state['original_cv'],
            jd_text=state['jd_text'],
            personalization_instructions=state.get('personalization_instructions', 'Focus on professional clarity and impact.')
        )
        final_cv = structured_llm.invoke(prompt)
        return {"final_ats_cv": final_cv}

    def run(self, initial_state: AgentState):
        return self.workflow.invoke(initial_state)

    def save_graph_image(self, output_path: str = "workflow.png"):
        """Saves the visual representation of the LangGraph workflow."""
        try:
            img_data = self.workflow.get_graph().draw_mermaid_png()
            with open(output_path, "wb") as f:
                f.write(img_data)
            print(f"--- Workflow visualization saved to {output_path} ---")
        except Exception as e:
            print(f"Could not generate graph image: {e}")
