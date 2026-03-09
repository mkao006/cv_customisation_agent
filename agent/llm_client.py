from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from config.settings import Settings

class LLMClient:
    def __init__(self, model_name=None):
        Settings.validate()
        self.model_name = model_name or Settings.DEFAULT_MODEL
        self.llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=0.7)
        self.tavily = TavilySearch(max_results=5)

    def invoke_llm(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content

    def with_structured_output(self, schema):
        return self.llm.with_structured_output(schema)

    def search(self, query: str) -> str:
        return str(self.tavily.run(query))
