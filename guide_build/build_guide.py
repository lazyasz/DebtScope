"""Team presentation guide for DebtScope: simple language, 5 pages."""
import os
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH as A
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "DebtScope_Team_Presentation_Guide.docx")
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
SIZE = float(os.environ.get("GUIDE_PT", "13"))

d = docx.Document()
s = d.sections[0]
s.page_width, s.page_height = Inches(8.27), Inches(11.69)
s.top_margin = s.bottom_margin = Inches(0.7)
s.left_margin = s.right_margin = Inches(0.8)
st = d.styles["Normal"]
st.font.name = "Calibri"; st.font.size = Pt(SIZE)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after = Pt(3)
st.paragraph_format.line_spacing = 1.1


def runs(p, text, size=None, color=None):
    """**bold** spans inside text."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if part:
            r = p.add_run(part); r.bold = i % 2 == 1
            if size: r.font.size = Pt(size)
            if color: r.font.color.rgb = color


def H(text, size=14, before=8):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(3)
    # no keep-with-next: in Pages it stops the following table from splitting and leaves a gap
    r = p.add_run(text); r.bold = True; r.font.size = Pt(size); r.font.color.rgb = NAVY


def P(text, align=A.JUSTIFY):
    p = d.add_paragraph(); p.alignment = align; runs(p, text); return p


def B(text, level=0):
    p = d.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.alignment = A.JUSTIFY; p.paragraph_format.space_after = Pt(1); runs(p, text); return p


def shade(cell, fill):
    pr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), fill); pr.append(sh)


def T(rows, widths, header=True, size=None):
    t = d.add_table(rows=0, cols=len(widths)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, val in enumerate(row):
            cells[ci].width = Inches(widths[ci])
            p = cells[ci].paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            runs(p, f"**{val}**" if header and ri == 0 else val, size=size or SIZE - 0.5)
            if header and ri == 0:
                shade(cells[ci], "DCE6F1")
    pr = t._tbl.tblPr  # fixed full-width layout so every app keeps the column widths
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); pr.append(lay)
    tw = pr.find(qn("w:tblW"))
    if tw is None:
        tw = OxmlElement("w:tblW"); pr.append(tw)
    tw.set(qn("w:w"), str(int(sum(widths) * 1440))); tw.set(qn("w:type"), "dxa")
    grid = t._tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(w * 1440)))
    d.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


# ---------------------------------------------------------------- title
p = d.add_paragraph(); p.alignment = A.CENTER
r = p.add_run("DebtScope: Team Presentation Guide"); r.bold = True; r.font.size = Pt(20); r.font.color.rgb = NAVY
p = d.add_paragraph(); p.alignment = A.CENTER
runs(p, "What to say, what to show, how it works, and 20 likely questions. Read it once fully; then use the "
        "**Who says what** section as your script.", size=SIZE)
T([["Live website", "https://debtscope.onrender.com (open it 5 minutes early: the free server takes about a minute to wake up)"],
   ["Code", "github.com/lazyasz/DebtScope"],
   ["Team", "Adesh Patankar · Dhruv Sakhare · Vaishnavi Pulaparthi · Jiya Bhavsar   |   Guide: Prof. Sushma Mehetre"]],
  [1.3, 5.37], header=False)

# ---------------------------------------------------------------- 1
H("1. The project in simple words")
P("**The problem.** Every software team has “technical debt”: messy, rushed or complicated code that still works but makes "
  "future changes slow and risky. Tools can list thousands of problems, but nobody knows **which file to fix first**. "
  "Teams end up guessing.")
P("**Our solution.** DebtScope connects to a team’s GitHub repository, **measures every important file**, uses a "
  "**machine-learning model to predict which files are likely to have bugs**, mixes that with how important and urgent "
  "the code is for the business and how much effort the fix needs, and gives a **ranked “fix this first” list with "
  "the reason for every position**. With one click the work can be sent to the team’s own **Jira** or **Notion**.")
P("**One-line pitch (memorise it):** “DebtScope tells a software team which code to fix first, explains why, and puts "
  "that work straight into their own tools.”")

# ---------------------------------------------------------------- 2
H("2. How it works (the logic)")
P("Think of it as four steps: **measure → predict → score → act.**")
B("**Measure.** The scanner reads the repository through GitHub (using the user’s own GitHub login), picks the 25 most "
  "important source files, and measures each one: **complexity** (how many decision paths), **nesting** (code inside "
  "code inside code), **duplication**, **code smells** (very long files, TODO markers) and **churn** (how often the file "
  "changed in Git history). Takes about 15 seconds.")
B("**Predict.** Our **Random Forest** model (100 decision trees voting together) looks at these numbers and predicts how "
  "many bugs a file is likely to have. We turn that into a **risk score from 0 to 100**. It is a relative score: good for "
  "comparing files, not an exact bug count.")
B("**Score.** Every file gets a priority score from **five dimensions**, each 0–100:")
T([["Dimension", "Simple meaning", "Weight"],
   ["Technical Risk (TR)", "Half from measurements, half from the ML prediction", "35%"],
   ["Business Impact (BI)", "How important this code is to the company (read from the team’s Notion)", "30%"],
   ["Urgency (U)", "How soon it matters (release / sprint timing)", "15%"],
   ["Maintenance cost (M)", "How much time it keeps wasting", "10%"],
   ["Debt age", "How long the problem has existed (full at 1 year)", "10%"]],
  [1.6, 4.2, 0.87])
P("Then **effort** is added: Final score = 85% × base score + 15% × (100 − effort). So **cheap fixes with high value rise to "
  "the top**. Files are labelled Critical (80+), High, Medium or Low, and placed in a quadrant: **Quick Win** (high value, low "
  "effort), **Strategic Refactor** (high value, high effort), **Opportunistic**, or **Deprioritized**.")
B("**Act.** The user can open any file to see the reason for its score, try the **What-If Simulator**, ask the **AI "
  "Copilot**, and export the list to **Jira tickets** or a **Notion database**.")
P("**Honesty rule (say this, reviewers like it):** if some data is missing, for example Notion is not connected, we "
  "**never invent numbers**. That dimension is removed, the other weights are rescaled, and the screen says “3 of 5 "
  "dimensions — technical-only”.")

H("How the ML model was built", 12, 4)
B("**Data:** the public **Technical Debt Dataset**: 21 years of history from **31 Apache projects** (commits, code "
  "analysis, Jira issues).")
B("**Real bug labels:** the **SZZ algorithm** traces each bug-fix back to the commit that caused the bug, so we know "
  "which files really had bugs.")
B("**Data pipeline (Bronze → Silver → Gold):** Bronze = raw copy (2.9 million rows); Silver = cleaned and joined (52,428 "
  "bug links); Gold = final training table (**1,037,222 rows**). **12 out of 12** automatic quality checks pass.")
B("**Training:** 14 features per file; tested on 58,267 files the model never saw. **Top features:** author "
  "experience (42%) and number of refactorings (20%), meaning who changes the code and how it was changed matter most.")

H("Website pages (one line each)", 12, 4)
T([["Page", "What it does"],
   ["Dashboard", "Overall code health, repositories, key numbers, top files to fix"],
   ["Priorities", "Full ranked list, how the score is built, value-vs-effort chart, export buttons"],
   ["Hotspots", "Files with technical risk or business impact of 70+, with complexity, churn and smells"],
   ["Risk Predictions", "Model facts, what drives predictions, files with the highest predicted risk"],
   ["File Details", "Factor-by-factor explanation of one file’s score"],
   ["What-If Simulator", "Choose clean-up amount and test coverage; the real model predicts the change in bugs"],
   ["AI Copilot", "Chat that answers from your own data (Gemini + tools); asks before creating tickets"],
   ["Integrations", "Connect or disconnect your own GitHub, Notion and Jira"],
   ["About the model", "Data quality checks and accuracy evidence"]],
  [1.6, 5.07])


# ---------------------------------------------------------------- 3
H("3. Key numbers (cheat sheet)")
T([["What", "Number", "What it means in simple words"],
   ["Model accuracy (R²)", "0.413", "Explains about 41% of why bug counts differ: good for real-world code data"],
   ["Average error", "4.74 vs 7.31", "35.2% smaller error than just guessing the average"],
   ["Cross-validation", "0.398 ± 0.011", "Same result on 5 different splits, so it is stable"],
   ["NASA benchmark AUC", "0.733 / 0.875", "Works on standard research datasets too (0.5 = coin toss)"],
   ["Backtest", "372 files, 108 bugs", "Tested on 6 real open-source projects (Python, JavaScript, Java)"],
   ["Backtest AUC", "0.791", "79% chance a buggy file is ranked above a clean one"],
   ["vs random order", "+0.300 AUC", "Clearly and statistically better than random"],
   ["vs size / churn", "about equal", "Same accuracy as simple rules, but we add reasons, business context and actions"],
   ["Copilot tests", "58 / 58 pass", "Explanations, privacy between users, and attack resistance"],
   ["Automated tests", "201 pass", "Backend code is tested automatically"],
   ["Research paper", "Accepted, IJRTI", "Paper ID IJRTI_303251, Vol. 11, Issue 11, Nov 2026 (92% unique)"]],
  [1.55, 1.35, 3.77])

# ---------------------------------------------------------------- 4
H("4. Demo script: who says what (about 12 minutes)")
P("**Before the review:** open the site early, sign in, and scan **psf/requests** and **pallets/flask** so the pages "
  "already have data. Keep the PPT open as a backup if the internet fails.")
T([["Who", "Show (click)", "Say (simple version)"],
   ["**Adesh** (2 min)\nIntro + login",
    "Title slide → website sign-in page → Get started → Integrations page",
    "Pitch line. “Anyone signs in with Google and gets a private workspace. Each user connects their **own** GitHub, Notion "
    "and Jira; we never use our accounts. Tokens are encrypted.”"],
   ["**Dhruv** (3 min)\nScan + Dashboard",
    "“Scan a repository” → type psf/requests → Dashboard",
    "“The scanner measures 25 key files in about 15 seconds.” Point at debt health, quick wins, average risk, complex files, "
    "types of debt, ‘Fix these first’. “Wrong repo name? Clear error, nothing saved, no fake data.”"],
   ["**Vaishnavi** (3 min)\nScoring logic",
    "Priorities page → quadrant chart → coverage label → open one file",
    "Explain the 5 dimensions and effort (Section 2). “Every score shows its reasons. Missing data is never invented.” "
    "Show the factor-by-factor breakdown of one file."],
   ["**Jiya** (3 min)\nML + AI + export",
    "Risk Predictions → What-If → AI Copilot → Export to Jira / Notion",
    "Model facts (Section 3). What-If: “move the slider, the real model predicts fewer bugs.” Ask Copilot: “Why is "
    "src/requests/utils.py ranked first?” “It only answers from your data.” Export one ticket."],
   ["**Adesh / Dhruv** (1 min)\nClose",
    "Results slide",
    "Backtest result, honest comparison, IJRTI paper acceptance, future work. “Thank you, happy to take questions.”"]],
  [1.25, 1.85, 3.57])

# ---------------------------------------------------------------- 5
H("5. Twenty likely questions with simple answers")
QA = [
    ("What is technical debt?", "Code that works now but is messy or rushed, so every future change costs more time and causes more bugs. Like a loan: you pay interest until you fix it."),
    ("What problem does DebtScope solve?", "Teams don’t know which messy code to fix first. We rank the files, explain why, and send the work to their tools."),
    ("How is it different from SonarQube?", "SonarQube lists issues. We predict which files will cause bugs, add business importance and effort, and give one ranked, explained to-do list."),
    ("Why Random Forest?", "It works very well on table-style data, handles mixed features, is hard to overfit, and tells us which features matter. It is widely used in bug-prediction research."),
    ("Where does the training data come from?", "The public Technical Debt Dataset: 31 Apache projects with commits, code analysis and Jira issues."),
    ("What is SZZ?", "A method that traces each bug-fix back to the change that introduced the bug, giving us real ‘this file had bugs’ labels."),
    ("What are Bronze, Silver and Gold?", "Three cleaning stages: raw copy → cleaned and joined → final training table. 12 quality checks guard it."),
    ("How accurate is the model?", "R² 0.413 and 35% lower error than guessing the average, stable across 5-fold cross-validation, and AUC 0.73 / 0.88 on NASA benchmarks."),
    ("How do you know it predicts the future?", "Backtest: we scored 6 projects using only their code from 18 months ago, then checked which files really got bug fixes in the next 12 months. AUC 0.79."),
    ("Is it better than just picking the biggest files?", "Statistically about equal, and we say that honestly. Our value is the explanations, business context, effort and one-click action, not only the ranking."),
    ("What are the five dimensions?", "Technical risk, business impact, urgency, maintenance cost and debt age, then adjusted for effort."),
    ("What if business data is missing?", "We don’t make it up. That dimension is dropped, weights are rescaled, and the screen says how many dimensions were used."),
    ("How does the AI Copilot avoid wrong answers?", "It must call our tools to fetch the user’s real data before answering, so it cannot invent numbers. If Gemini is busy, it still answers from the data."),
    ("Can one user see another user’s data?", "No. Every request is tied to the logged-in user’s workspace on the server. 31 automated tests and 8 Copilot tests check this."),
    ("How do you keep accounts secure?", "Google sign-in, secure session cookies, encrypted tokens, OAuth state checks, blocked internal addresses, and the Copilot must ask before creating tickets."),
    ("Can it scan private repositories?", "Yes, but only if that user connected their own GitHub account. Otherwise it is refused."),
    ("What technologies did you use?", "React + Vite (frontend), FastAPI in Python (backend), PostgreSQL, scikit-learn and PySpark (ML and data), Google Gemini (AI), Docker on Render (hosting)."),
    ("What are the limitations?", "Model trained on Java projects; scans cover up to 25 files; risk is relative, not an exact bug count; small backtest; the free server sleeps when idle."),
    ("What is the future scope?", "Train on more languages, calibrate probabilities, bigger backtest, team workspaces, trends over time, and suggested fixes as pull requests."),
    ("Who did what in the team?", "Vaishnavi: data pipeline. Jiya: machine-learning model. Dhruv: backend and scoring engine. Adesh: frontend, dashboards and integrations. We all tested and documented together."),
]
for i, (q, a) in enumerate(QA, 1):
    p = d.add_paragraph(); p.alignment = A.JUSTIFY; p.paragraph_format.space_after = Pt(2)
    runs(p, f"**Q{i}. {q}**  {a}")

d.core_properties.title = "DebtScope Team Presentation Guide"
d.save(OUT)
print("saved", OUT)
