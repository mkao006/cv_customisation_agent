from markdown import markdown
from xhtml2pdf import pisa
from agent.models import OptimizedCV

class CVBuilder:
    @staticmethod
    def render_pdf(md_content: str, output_path: str, is_cv: bool = True):
        """Converts Markdown to a styled PDF."""
        html_body = markdown(md_content)
        
        styled_html = f"""
        <html>
        <head>
            <style>
                @page {{ size: a4 portrait; margin: 1cm; }}
                body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 1.2; color: #000; padding: 0; margin: 0; }}
                .banner {{ margin-bottom: 8px; border-bottom: 0.5px solid #eee; padding-bottom: 2px; font-size: 7pt; color: #999; text-align: center; font-style: italic; }}
                h1 {{ text-align: center; font-size: 20pt; font-weight: bold; color: #2c3e50; border-bottom: 1.5px solid #2c3e50; padding-bottom: 2px; margin-top: 0; margin-bottom: 8px; }}
                h2 {{ font-size: 12pt; font-weight: bold; color: #2980b9; text-transform: uppercase; border-bottom: 0.5px solid #bdc3c7; margin-top: 10px; margin-bottom: 4px; padding-bottom: 1px; }}
                h3 {{ font-size: 10.5pt; font-weight: bold; color: #2c3e50; margin-top: 6px; margin-bottom: 1px; }}
                p, li {{ text-align: justify; margin-top: 0; margin-bottom: 3pt; }}
                .role-line {{ font-style: italic; color: #555; margin-bottom: 4px; display: block; }}
                .tech-stack-line {{ font-size: 9pt; color: #555; margin-top: 2px; margin-left: 18pt; }}
                ul {{ margin-top: 2px; margin-bottom: 2px; padding-left: 18pt; }}
                li {{ margin-bottom: 1pt; }}
                a {{ color: #999; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="banner">
                This document was generated and tailored by a <a href="https://github.com/mkao006/cv_customisation_agent">custom AI Research Agent</a>.
            </div>
            {html_body}
        </body>
        </html>
        """
        with open(output_path, "wb") as f:
            pisa.CreatePDF(styled_html, dest=f)

    @staticmethod
    def generate_cv_markdown(cv: OptimizedCV) -> str:
        md = f"# Michael C. J. Kao\n\n## Professional Summary\n{cv.summary}\n\n"
        
        md += "## Technical Skills\n"
        for s in cv.skills:
            md += f"- {s}\n"
        
        md += "\n## Work Experience\n"
        for exp in cv.experience:
            md += f"### {exp.job_title} | {exp.company} | {exp.dates}\n"
            md += f"*{exp.role_summary}*\n\n"
            
            if exp.project_highlight:
                for bullet in exp.project_highlight:
                    # Clean the bullet to ensure it renders as a markdown list item
                    clean_bullet = bullet.strip().lstrip("-*•").strip()
                    md += f"- {clean_bullet}\n"
                
                if exp.technical_stack:
                    # Render tech stack as a sub-text line rather than a bullet
                    md += f"\n<div class='tech-stack-line'>{exp.technical_stack}</div>\n"
                md += "\n"
            
        md += "## Education\n"
        for edu in cv.education:
            md += f"- **{edu.degree}** | {edu.institution} | {edu.completion_year}\n"
        return md
