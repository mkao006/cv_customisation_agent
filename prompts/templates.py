CV_GENERATION_TEMPLATE = """
Rewrite the CV based on the Strategy, Job Description, and specific Personalization Instructions.

### OBJECTIVE
Transform the Original CV into a highly optimized, ATS-friendly document that aligns with the JD while adhering to the Research Strategy.

### MANDATORY GUIDELINES: STRUCTURAL INTEGRITY & ATS COMPATIBILITY
1. **Format & Layout**: Use a clean, single-column layout. Do not suggest or include any tables, graphics, or icons.
2. **Contact Professionalism**: Start the CV with a concise contact line including:
   - Professional Email
   - Customized LinkedIn URL
   - Technical Portfolio links (GitHub, Kaggle, or Google Scholar)
   These should be clearly visible at the top.
3. **Brevity**: Ensure the total length is appropriate for a Senior Engineer (maximum 2 pages). Be concise but impactful.
4. **Reverse Chronological Order**: The **Work Experience** section MUST be sorted with the most recent role first.
5. **No Metric Hallucination**: DO NOT invent, hallucinate, or estimate any numerical metrics (%, $, time) not in the Original CV.

### INPUTS
1. **APPLICATION STRATEGY**:
{strategy}

2. **ORIGINAL CV**:
{original_cv}

3. **JOB DESCRIPTION**:
{jd_text}

4. **USER PERSONALIZATION INSTRUCTIONS**:
{personalization_instructions}

### SECTION CONSTRAINTS
- **Headers**: Use standard headers only: "Professional Summary", "Work Experience", "Education", "Skills".
- **Summary**: 3-4 sentence professional summary tailored to this specific role.
- **Experience**: Rewrite bullet points to be achievement-oriented (Action Verb + Task + Result).
- **Skills**: Group technical skills into logical categories (e.g., "LANGUAGES: Python, R"). 

### OUTPUT
Return a valid JSON object matching the requested schema (Summary, Experience, Skills, Education). 
Ensure the contact info is included at the very beginning of the 'Summary' string if not handled elsewhere.
"""
