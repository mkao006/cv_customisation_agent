from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from config.settings import Settings

class LLMClient:
    def __init__(self, model_name=None):
        Settings.validate()
        self.standard_model_name = model_name or Settings.DEFAULT_MODEL
        self.strong_model_name = Settings.STRONG_MODEL
        
        # Standard model for general tasks
        self.standard_llm = self._init_llm(self.standard_model_name)
        
        # Strong model for critical synthesis and review tasks
        self.strong_llm = self._init_llm(self.strong_model_name)
        
        self.tavily = TavilySearch(max_results=5)

    def _init_llm(self, model_name):
        return ChatOpenAI(
            model=model_name,
            openai_api_key=Settings.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            default_headers={
                "HTTP-Referer": "https://github.com/mkao006/cv_customisation_agent",
                "X-Title": "CV Customisation Agent",
            }
        )

    def invoke_llm(self, prompt: str, use_strong=False) -> str:
        llm = self.strong_llm if use_strong else self.standard_llm
        return llm.invoke(prompt).content

    def with_structured_output(self, schema, use_strong=False):
        llm = self.strong_llm if use_strong else self.standard_llm
        return llm.with_structured_output(schema)

    def search(self, query: str) -> str:
        return str(self.tavily.invoke(query))
