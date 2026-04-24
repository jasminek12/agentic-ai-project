import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.config import OUTPUTS_DIR


def _escape_latex(text: str) -> str:
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = text
    for original, latex_safe in replacements.items():
        escaped = escaped.replace(original, latex_safe)
    return escaped


def json_to_latex(resume_data: Dict[str, Any]) -> str:
    print("[DEBUG] Converting tailored resume JSON to LaTeX")
    summary = _escape_latex(resume_data.get("summary", ""))
    experiences: List[Dict[str, Any]] = resume_data.get("experience", [])
    skills = [_escape_latex(skill) for skill in resume_data.get("skills", [])]

    experience_blocks: List[str] = []
    for exp in experiences:
        company = _escape_latex(exp.get("company", ""))
        points = exp.get("points", [])
        point_lines = "\n".join(f"\\item {_escape_latex(str(point))}" for point in points)
        experience_blocks.append(
            f"\\subsection*{{{company}}}\n\\begin{{itemize}}\n{point_lines}\n\\end{{itemize}}"
        )

    skills_line = ", ".join(skills)
    experience_text = "\n\n".join(experience_blocks) if experience_blocks else "No experience provided."

    return rf"""
\documentclass[11pt]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage[T1]{{fontenc}}
\usepackage{{lmodern}}
\begin{{document}}

\section*{{Summary}}
{summary}

\section*{{Experience}}
{experience_text}

\section*{{Skills}}
{skills_line}

\end{{document}}
""".strip()


def compile_pdf(latex_content: str) -> str:
    print("[DEBUG] Compiling LaTeX content to PDF with pdflatex")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tex_path = OUTPUTS_DIR / f"resume_{stamp}.tex"
    pdf_path = OUTPUTS_DIR / f"resume_{stamp}.pdf"

    tex_path.write_text(latex_content, encoding="utf-8")

    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(OUTPUTS_DIR), str(tex_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        print(f"[DEBUG] pdflatex not found: {exc}")
        raise RuntimeError("pdflatex is not installed or not available in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        print(f"[DEBUG] pdflatex compilation failed: {exc.stderr}")
        raise RuntimeError("Failed to compile LaTeX into PDF.") from exc

    if not pdf_path.exists():
        raise RuntimeError("PDF was not generated.")

    print(f"[DEBUG] PDF generated at: {pdf_path}")
    return str(Path("storage") / "outputs" / pdf_path.name)


def save_latex(latex_content: str) -> str:
    print("[DEBUG] Saving LaTeX content to .tex file")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tex_path = OUTPUTS_DIR / f"resume_{stamp}.tex"
    tex_path.write_text(latex_content, encoding="utf-8")
    return str(Path("storage") / "outputs" / tex_path.name)
