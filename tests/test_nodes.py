import unittest
from unittest.mock import MagicMock, patch
from main import ingest_inputs, research_company, research_best_practices, synthesize_strategy, generate_cv, create_workflow, init_tools
from agent.models import AgentState, OptimizedCV

class TestAgentNodes(unittest.TestCase):

    def setUp(self):
        # Create mocks for LLM and Tavily
        self.mock_llm = MagicMock()
        self.mock_tavily = MagicMock()
        
        # Initialize the tools in main module with our mocks
        init_tools(llm_instance=self.mock_llm, tavily_instance=self.mock_tavily)

        self.state: AgentState = {
            "original_cv": "Junior Dev at TechCorp",
            "jd_source": "https://example.com/job",
            "jd_text": "Looking for Senior Python Developer",
            "company_research": "",
            "best_practices_research": "",
            "application_strategy": "",
            "final_ats_cv": None
        }

    @patch('main.get_text_from_jd')
    def test_ingest_inputs(self, mock_get_jd):
        mock_get_jd.return_value = "Mocked JD Text"
        result = ingest_inputs(self.state)
        self.assertEqual(result["jd_text"], "Mocked JD Text")

    def test_research_company(self):
        self.mock_llm.invoke.return_value.content = "TechCorp, Senior Python Developer"
        self.mock_tavily.run.return_value = "Tavily Results"
        result = research_company(self.state)
        self.assertEqual(result["company_research"], "Tavily Results")
        self.mock_tavily.run.assert_called_once()

    def test_research_best_practices(self):
        self.mock_tavily.run.return_value = "Best Practices Results"
        result = research_best_practices(self.state)
        self.assertEqual(result["best_practices_research"], "Best Practices Results")

    def test_synthesize_strategy(self):
        self.mock_llm.invoke.return_value.content = "Strategic Strategy"
        result = synthesize_strategy(self.state)
        self.assertEqual(result["application_strategy"], "Strategic Strategy")

    def test_generate_cv(self):
        # Create a mock return value that behaves like the OptimizedCV Pydantic model
        mock_cv = MagicMock()
        mock_cv.model_dump_json.return_value = '{"summary": "test"}'
        self.mock_llm.with_structured_output.return_value.invoke.return_value = mock_cv
        
        result = generate_cv(self.state)
        self.assertIsNotNone(result["final_ats_cv"])

    def test_workflow_compilation(self):
        app = create_workflow()
        self.assertIsNotNone(app)

if __name__ == "__main__":
    unittest.main()
