import os
import yaml
from tools.job_search import JobSearch
from agent.llm_client import LLMClient
from config.settings import Settings

def parse_jd_to_yaml(url: str, output_path: str):
    print(f"--- Fetching JD from {url} ---")
    jd_text = JobSearch.get_text_from_jd(url)
    
    print("--- Parsing JD into structured YAML ---")
    llm = LLMClient()
    prompt = f"""
    Parse the following Job Description text into a structured YAML format.
    Include fields for:
    - job_title
    - company
    - location
    - summary (brief)
    - key_responsibilities (list)
    - required_qualifications (list)
    - preferred_qualifications (list)
    - technical_skills (nested categories if possible)
    
    TEXT:
    {jd_text}
    
    Return ONLY the raw YAML. Do not include markdown blocks or any other text.
    """
    
    yaml_content = llm.invoke_llm(prompt)
    
    # Clean up LLM output if it included markdown backticks
    if "```yaml" in yaml_content:
        yaml_content = yaml_content.split("```yaml")[1].split("```")[0].strip()
    elif "```" in yaml_content:
        yaml_content = yaml_content.split("```")[1].split("```")[0].strip()

    # Validate by parsing and dumping back
    try:
        data = yaml.safe_load(yaml_content)
        with open(output_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        print(f"--- Successfully saved JD to {output_path} ---")
    except Exception as e:
        print(f"Error parsing YAML: {e}")
        # Fallback to saving raw output if parsing fails
        with open(output_path, "w") as f:
            f.write(yaml_content)

if __name__ == "__main__":
    apple_jd_url = "https://jobs.apple.com/en-us/details/200638600-3278/machine-learning-engineer-data-solutions-initiatives"
    output_file = "data/eval_jd/apple_mle.yaml"
    parse_jd_to_yaml(apple_jd_url, output_file)
