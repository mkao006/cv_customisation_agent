import os
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader

class JobSearch:
    @staticmethod
    def get_text_from_jd(jd_source: str) -> str:
        """Extract text from a JD URL or local file."""
        if jd_source.startswith("http"):
            loader = WebBaseLoader(jd_source, requests_kwargs={"verify": False})
            data = loader.load()
            return "\n".join([doc.page_content for doc in data])
        elif jd_source.endswith(".pdf"):
            loader = PyPDFLoader(jd_source)
            data = loader.load()
            return "\n".join([doc.page_content for doc in data])
        else:
            if os.path.exists(jd_source):
                with open(jd_source, "r") as f:
                    return f.read()
            return jd_source
