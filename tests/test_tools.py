import unittest
import os
from tools.job_search import JobSearch
from tools.cv_builder import CVBuilder
from agent.models import OptimizedCV, Experience, Education

class TestTools(unittest.TestCase):
    def test_job_search_get_text_raw(self):
        # Should return the input if it's not a path or URL
        text = "Role: Software Engineer"
        self.assertEqual(JobSearch.get_text_from_jd(text), text)

    def test_job_search_yaml(self):
        # Create a temporary yaml JD
        yaml_path = "test_jd.yaml"
        with open(yaml_path, "w") as f:
            f.write("job_title: Test Engineer\ncompany: TestCo")
        
        try:
            text = JobSearch.get_text_from_jd(yaml_path)
            self.assertIn("job_title: Test Engineer", text)
            self.assertIn("company: TestCo", text)
        finally:
            if os.path.exists(yaml_path):
                os.remove(yaml_path)

    def test_cv_builder_markdown_generation(self):
        cv = OptimizedCV(
            summary="Test Summary",
            skills=["Python", "SQL"],
            experience=[
                Experience(
                    job_title="Dev",
                    company="Tech",
                    dates="2020-2021",
                    responsibilities=["Code"]
                )
            ],
            education=[
                Education(
                    degree="BSc",
                    institution="Uni",
                    completion_year="2020"
                )
            ]
        )
        md = CVBuilder.generate_cv_markdown(cv)
        self.assertIn("Test Summary", md)
        self.assertIn("Python", md)
        self.assertIn("Tech", md)

if __name__ == "__main__":
    unittest.main()
