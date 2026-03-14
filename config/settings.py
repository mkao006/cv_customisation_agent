import os
import ssl
import urllib3
import socket
from dotenv import load_dotenv
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

load_dotenv()

# Set default User-Agent to avoid warnings and blocking
if not os.getenv("USER_AGENT"):
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# SSL Fix for macOS
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Settings:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    DEFAULT_MODEL = os.getenv("MODEL_VERSION", "openai/gpt-4o-mini")
    STRONG_MODEL = os.getenv("STRONG_MODEL_VERSION", "openai/gpt-5-mini")
    BASE_CV_DIR = "data/base_cv"
    JOBS_DIR = "data/jobs"
    OUTPUT_DIR = "data/output"
    
    # Tracing Configuration
    ENABLE_TRACING = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    PHOENIX_HOST = "127.0.0.1"
    PHOENIX_PORT = 6006
    
    @staticmethod
    def validate():
        if not Settings.OPENROUTER_API_KEY or not Settings.TAVILY_API_KEY:
            raise ValueError("OPENROUTER_API_KEY and TAVILY_API_KEY must be set in .env")

    @staticmethod
    def is_phoenix_running():
        """Checks if the Phoenix server is listening on the default port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((Settings.PHOENIX_HOST, Settings.PHOENIX_PORT)) == 0

    @staticmethod
    def init_tracing():
        """Instrument the app and configure OTLP export to the background Phoenix server."""
        if not Settings.ENABLE_TRACING:
            return

        if not Settings.is_phoenix_running():
            print("\n" + "!" * 50)
            print("ERROR: Arize Phoenix server is NOT running.")
            print(f"Tracing is enabled but no server was found on {Settings.PHOENIX_HOST}:{Settings.PHOENIX_PORT}.")
            print("\nPlease start the Phoenix server in a separate terminal:")
            print(f"    uv run phoenix serve")
            print("!" * 50 + "\n")
            raise SystemExit(1)

        print(f"--- Exporting traces to Phoenix at http://{Settings.PHOENIX_HOST}:{Settings.PHOENIX_PORT} ---")
        
        # 1. Setup the OTLP Exporter pointing to Phoenix's OTLP endpoint
        endpoint = f"http://{Settings.PHOENIX_HOST}:{Settings.PHOENIX_PORT}/v1/traces"
        exporter = OTLPSpanExporter(endpoint=endpoint)
        
        # 2. Setup the Tracer Provider
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tracer_provider)
        
        # 3. Instrument LangChain ONLY (It already handles OpenAI/OpenRouter calls within its spans)
        LangChainInstrumentor().instrument()
