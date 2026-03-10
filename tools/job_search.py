import os
import yaml
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader

class JobSearch:
    @staticmethod
    def get_text_from_jd(jd_source: str) -> str:
        """Extract text from a JD URL or local file (Supports YAML, PDF, TXT)."""
        if jd_source.startswith("http"):
            loader = WebBaseLoader(jd_source, requests_kwargs={"verify": False})
            data = loader.load()
            return "\n".join([doc.page_content for doc in data])
        
        # Check if it's a local file
        if os.path.exists(jd_source):
            # Support YAML JDs
            if jd_source.endswith(".yaml") or jd_source.endswith(".yml"):
                with open(jd_source, "r") as f:
                    data = yaml.safe_load(f)
                    # Convert to YAML string for LLM ingestion
                    return yaml.dump(data, default_flow_style=False)
            
            # Support PDF
            elif jd_source.endswith(".pdf"):
                loader = PyPDFLoader(jd_source)
                data = loader.load()
                return "\n".join([doc.page_content for doc in data])
            
            # Support TXT
            else:
                with open(jd_source, "r") as f:
                    return f.read()
        
        # If it's not a URL or existing file, treat as raw text
        return jd_source
