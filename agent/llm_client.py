from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from config.settings import Settings

class LLMClient:
    def __init__(self, model_name=None):
        Settings.validate()
        self.model_name = model_name or Settings.DEFAULT_MODEL
        self.llm = ChatOpenAI(
            model=self.model_name,
            openai_api_key=Settings.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            default_headers={
                "HTTP-Referer": "https://github.com/mkao006/cv_customisation_agent", # Optional
                "X-Title": "CV Customisation Agent", # Optional
            }
        )
        self.tavily = TavilySearch(max_results=5)

    def invoke_llm(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content

    def with_structured_output(self, schema):
        return self.llm.with_structured_output(schema)

    def search(self, query: str) -> str:
        return str(self.tavily.run(query))
