CV_GENERATION_TEMPLATE = """
Rewrite the CV based on the Strategy, Job Description, and specific Personalization Instructions.

### OBJECTIVE
Your goal is to transform the Original CV into a highly optimized, ATS-friendly document that perfectly aligns with the Job Description while adhering to the Research Strategy.

### INPUTS
1. **APPLICATION STRATEGY**:
{strategy}

2. **ORIGINAL CV**:
{original_cv}

3. **JOB DESCRIPTION**:
{jd_text}

4. **USER PERSONALIZATION INSTRUCTIONS**:
{personalization_instructions}

### CONSTRAINTS & FORMATTING
- **Summary**: Create a punchy, 3-4 sentence professional summary tailored to this specific role.
- **Experience**: Rewrite bullet points to be achievement-oriented (Action Verb + Task + Result). Use keywords from the JD.
- **Skills**: Group technical skills into logical categories (e.g., "LANGUAGES: Python, R", "ML ENGINEERING: Spark, Airflow"). 
- **Structure**: Each category string (e.g. "LANGUAGES: ...") MUST be a separate element in the 'skills' list.
- **Tone**: Professional, confident, and data-driven.

### OUTPUT
You must return a valid JSON object matching the requested schema (Summary, Experience, Skills, Education).
"""
