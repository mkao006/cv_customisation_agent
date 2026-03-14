import os
import ssl
import urllib3
from dotenv import load_dotenv

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
    BASE_CV_DIR = "data/base_cv"
    JOBS_DIR = "data/jobs"
    OUTPUT_DIR = "data/output"
    
    @staticmethod
    def validate():
        if not Settings.OPENROUTER_API_KEY or not Settings.TAVILY_API_KEY:
            raise ValueError("OPENROUTER_API_KEY and TAVILY_API_KEY must be set in .env")
