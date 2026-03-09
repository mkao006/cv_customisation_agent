import unittest
from unittest.mock import MagicMock, patch
from agent.orchestrator import Orchestrator
from agent.models import AgentState

class TestAgent(unittest.TestCase):
    def setUp(self):
        # Patch LLMClient to avoid actual API calls
        with patch('agent.orchestrator.LLMClient') as mock_client:
            self.orchestrator = Orchestrator()
            self.mock_llm_client = self.orchestrator.llm_client

        self.state: AgentState = {
            "original_cv": "Skills: Python",
            "jd_source": "JD Source",
            "jd_text": "Looking for a Senior Python Developer with 10+ years of experience in AI, Machine Learning, and Large Scale Distributed Systems. Must be proficient in Python, SQL, and Go. Experience with Cloud platforms is a plus.",
            "jd_validation_error": None,
            "company_research": "",
            "best_practices_research": "",
            "competing_candidates_research": "",
            "research_iteration": 0,
            "max_research_iterations": 3,
            "research_evaluation": "satisfactory",
            "research_gaps": "",
            "application_strategy": "",
            "personalization_instructions": "",
            "final_ats_cv": None
        }

    def test_validate_jd_success(self):
        self.mock_llm_client.invoke_llm.return_value = "YES, looks like a JD"
        result = self.orchestrator.validate_jd(self.state)
        self.assertIsNone(result.get("jd_validation_error"))

    def test_validate_jd_failure(self):
        self.mock_llm_client.invoke_llm.return_value = "NO, this is a recipe"
        result = self.orchestrator.validate_jd(self.state)
        self.assertIsNotNone(result.get("jd_validation_error"))

    def test_research_hub_passthrough(self):
        result = self.orchestrator.research_hub(self.state)
        self.assertEqual(result, self.state)

    def test_route_jd_validation_valid(self):
        self.state["jd_validation_error"] = None
        route = self.orchestrator.route_jd_validation(self.state)
        self.assertEqual(route, "valid")

    def test_route_jd_validation_invalid(self):
        self.state["jd_validation_error"] = "Error"
        route = self.orchestrator.route_jd_validation(self.state)
        self.assertEqual(route, "invalid")

if __name__ == "__main__":
    unittest.main()
