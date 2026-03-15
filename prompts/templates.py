CV_GENERATION_TEMPLATE = """
Rewrite the CV based on the Strategy, Job Description, and Personalization Instructions.

### OBJECTIVE
Transform the Original CV into a project-centric, high-impact document that aligns with the JD.

### MANDATORY RULES
1. **Reverse Chronological Order**: Sorted with the most recent role first (e.g., April 2024 role before June 2021).
2. **Project Highlight Format**:
   - If a project exists, provide 2-3 bullet points of achievements.
   - Immediately following the last bullet point, add a line: "Tech Stack: [tool1], [tool2], ..."
3. **No Standalone Tech Stack**: Do NOT create a separate section or bullet for the project's tech stack. It must be a single line following the project bullets.
4. **Skills Section**: Maintain categorical skills (e.g., "LANGUAGES: Python").
5. **No Hallucination**: Do NOT invent projects, metrics, or roles. Use only those in the Master CV.

### SECTION CONSTRAINTS
- **Experience**: Use the following for EACH role:
   a. **Role Summary**: One-liner scope.
   b. **Project Highlight**: Bulleted achievements from Master CV.
   c. **Technical Stack**: A single string starting with "Tech Stack: ..."

### INPUTS
1. **APPLICATION STRATEGY**: 
{strategy}

2. **ORIGINAL CV (Source of Truth)**: 
{original_cv}

3. **JOB DESCRIPTION**: 
{jd_text}

4. **USER PERSONALIZATION INSTRUCTIONS**: 
{personalization_instructions}

### OUTPUT
Return a valid JSON object matching the requested schema.
"""
