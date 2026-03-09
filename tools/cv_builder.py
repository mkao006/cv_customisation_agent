from markdown import markdown
from xhtml2pdf import pisa
from agent.models import OptimizedCV

class CVBuilder:
    @staticmethod
    def render_pdf(md_content: str, output_path: str, is_cv: bool = True):
        """Converts Markdown to a styled PDF."""
        html_body = markdown(md_content)
        
        # Professional Styles (Tight Layout as requested)
        styled_html = f"""
        <html>
        <head>
            <style>
                @page {{ size: a4 portrait; margin: 1cm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt; line-height: 1.1; color: #333; }}
                .banner {{ margin-bottom: 8px; border-bottom: 0.5px solid #eee; padding-bottom: 2px; font-size: 7pt; color: #999; text-align: center; font-style: italic; }}
                h1 {{ text-align: center; font-size: 20pt; font-weight: bold; color: #2c3e50; border-bottom: 1.5px solid #2c3e50; padding-bottom: 2px; margin-top: 0; margin-bottom: 8px; }}
                h2 {{ font-size: 12pt; font-weight: bold; color: #2980b9; text-transform: uppercase; border-bottom: 0.5px solid #bdc3c7; margin-top: 8px; margin-bottom: 3px; padding-bottom: 1px; }}
                h3 {{ font-size: 10pt; font-weight: bold; color: #2c3e50; margin-top: 4px; margin-bottom: 1px; }}
                p, li {{ text-align: justify; margin-top: 0; margin-bottom: 0.5pt; }}
                ul {{ margin-top: 0; margin-bottom: 0; padding-left: 15pt; }}
            </style>
        </head>
        <body>
            <div class="banner">
                This document was generated and tailored by a custom AI Research Agent.
            </div>
            {html_body}
        </body>
        </html>
        """
        with open(output_path, "wb") as f:
            pisa.CreatePDF(styled_html, dest=f)

    @staticmethod
    def generate_cv_markdown(cv: OptimizedCV) -> str:
        md = f"# Michael C. J. Kao\n\n## Professional Summary\n{cv.summary}\n\n## Technical Skills\n"
        for s in cv.skills: md += f"- {s}\n"
        md += "\n## Work Experience\n"
        for exp in cv.experience:
            md += f"### {exp.job_title} | {exp.company} | {exp.dates}\n"
            for b in exp.responsibilities: md += f"- {b}\n"
            md += "\n"
        md += "## Education\n"
        for edu in cv.education: md += f"- **{edu.degree}** | {edu.institution} | {edu.completion_year}\n"
        return md
