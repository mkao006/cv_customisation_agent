from markdown import markdown
from xhtml2pdf import pisa
from agent.models import OptimizedCV

class CVBuilder:
    @staticmethod
    def render_pdf(md_content: str, output_path: str, is_cv: bool = True):
        """Converts Markdown to a styled PDF following strict ATS guidelines."""
        html_body = markdown(md_content)
        
        # ATS-Optimized Styles
        # - Single column layout
        # - Standard sans-serif fonts (Arial/Helvetica)
        # - Header sizes: 14-16pt, Body: 10-12pt
        # - No complex tables, graphics, or icons
        styled_html = f"""
        <html>
        <head>
            <style>
                @page {{ 
                    size: a4 portrait; 
                    margin: 1.27cm; /* Standard 0.5 inch margins */
                }}
                body {{ 
                    font-family: Arial, Helvetica, sans-serif; 
                    font-size: 10.5pt; 
                    line-height: 1.2; 
                    color: #000000; 
                    padding: 0; 
                    margin: 0; 
                }}
                .banner {{ 
                    margin-bottom: 10px; 
                    border-bottom: 0.5px solid #eee; 
                    padding-bottom: 2px; 
                    font-size: 8pt; 
                    color: #666; 
                    text-align: center; 
                    font-style: italic; 
                }}
                /* Name Header */
                h1 {{ 
                    text-align: center; 
                    font-size: 18pt; 
                    font-weight: bold; 
                    margin-top: 0; 
                    margin-bottom: 5px;
                    text-transform: uppercase;
                }}
                /* Section Headers */
                h2 {{ 
                    font-size: 14pt; 
                    font-weight: bold; 
                    text-transform: uppercase; 
                    border-bottom: 1px solid #000; 
                    margin-top: 12px; 
                    margin-bottom: 6px; 
                    padding-bottom: 1px; 
                }}
                /* Job Titles / Subheaders */
                h3 {{ 
                    font-size: 11pt; 
                    font-weight: bold; 
                    margin-top: 6px; 
                    margin-bottom: 2px; 
                }}
                p, li {{ 
                    text-align: left; 
                    margin-top: 0; 
                    margin-bottom: 2pt; 
                }}
                ul {{ 
                    margin-top: 0; 
                    margin-bottom: 4pt; 
                    padding-left: 18pt; 
                }}
                li {{ 
                    margin-bottom: 1pt; 
                }}
                .contact-info {{
                    text-align: center;
                    font-size: 10pt;
                    margin-bottom: 10px;
                }}
                a {{
                    color: #000;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="banner">
                This document was generated and tailored by a <a href="https://github.com/mkao006/cv_customisation_agent" style="color: #666;">custom AI Research Agent</a>.
            </div>
            {html_body}
        </body>
        </html>
        """
        with open(output_path, "wb") as f:
            pisa.CreatePDF(styled_html, dest=f)

    @staticmethod
    def generate_cv_markdown(cv: OptimizedCV) -> str:
        # Note: We now assume the LLM includes contact info in the summary or we handle it here
        md = f"# Michael C. J. Kao\n\n"
        
        # Summary
        md += f"## Professional Summary\n{cv.summary}\n\n"
        
        # Skills
        md += "## Skills\n"
        for s in cv.skills:
            md += f"- {s}\n"
        
        # Experience
        md += "\n## Work Experience\n"
        for exp in cv.experience:
            # Clean single line for ATS readability: Title | Company | Dates
            md += f"### {exp.job_title} | {exp.company} | {exp.dates}\n"
            for b in exp.responsibilities:
                md += f"- {b}\n"
            md += "\n"
            
        # Education
        md += "## Education\n"
        for edu in cv.education:
            md += f"- **{edu.degree}**, {edu.institution} ({edu.completion_year})\n"
            
        return md
