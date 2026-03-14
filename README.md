# Job Application Research & Tailoring Agent

An AI-powered multi-agent pipeline built with **LangGraph**, **LangChain**, and **OpenRouter (GPT-4o mini)** to research companies and tailor CVs for specific job descriptions.

## Features
- **JD Ingestion**: Supports URLs (web scraping) and local PDF/TXT files.
- **JD Validation**: Automatically verifies if the source is a valid job description before starting research.
- **Parallel Intelligence**: Simultaneously researches the Hiring Company, Role Best Practices, and LinkedIn Competing Candidate Profiles.
- **Recursive Refinement**: Evaluates research for gaps and loops back to refine data (up to 3 iterations).
- **ATS-Optimized CV**: Produces a professionally styled PDF and Markdown CV using structured YAML as the "Source of Truth".
- **Organized Outputs**: Each run is saved in a unique, timestamped directory.

## Workflow Architecture
The agent uses a parallel fan-out/fan-in pattern with a self-correcting refinement loop:

![Agent Workflow](workflow.png)

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```bash
   OPENROUTER_API_KEY=your_openrouter_api_key
   TAVILY_API_KEY=your_tavily_api_key
   USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)..." 
   ```

## Usage

### Run with Defaults
Uses the built-in sample CV and a default Apple MLE job description:
```bash
python main.py
```

### Tailor for a Specific Job
```bash
python main.py --cv data/base_cv/master_cv.yaml --jd "https://company.com/job-url"
```

### Command Line Options
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--cv` | Path to your original CV (YAML, PDF, or TXT) | `data/base_cv/master_cv.yaml` |
| `--jd` | URL or path to the Job Description | (Apple MLE Job URL) |
| `--model` | OpenRouter model to use | `openai/gpt-4o-mini` |
| `--personalize` | Custom instructions for the LLM | None |
| `--visualize` | Generate and save the workflow diagram | False |
| `--pdf` | Render an existing Markdown file to styled PDF | None |

## Outputs
Each execution creates a folder in `data/output/YYYYMMDD_HHMMSS/` containing:
- `TAILORED_CV.pdf`: The final professionally formatted resume.
- `TAILORED_CV.md`: Markdown version of the tailored resume.
- `STRATEGY_REPORT.pdf`: Detailed research and tailoring strategy.
- `STRATEGY_REPORT.md`: Markdown version of the research report.
- `metadata.json`: Logs the inputs and model used for that specific run.
