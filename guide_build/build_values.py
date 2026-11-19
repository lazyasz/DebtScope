"""How every number on the DebtScope UI is calculated, and how to justify it. Reuses the team guide's formatting."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "build_guide.py"), encoding="utf-8").read()
os.environ.setdefault("GUIDE_PT", "11.5")
exec(_src[: _src.index("# ---------------------------------------------------------------- title")])  # helpers only
OUT = os.path.join(HERE, "..", "DebtScope_UI_Values_Justification.docx")

p = d.add_paragraph(); p.alignment = A.CENTER
r = p.add_run("How DebtScope Calculates the Numbers on Screen"); r.bold = True; r.font.size = Pt(19); r.font.color.rgb = NAVY
p = d.add_paragraph(); p.alignment = A.CENTER
runs(p, "Every value on the website, where it comes from, the exact formula, and how to explain it to a reviewer. "
        "Formulas are copied from the code (backend/services/repo_scanner_service.py, priority_service.py, "
        "api/metrics_routes.py).")

# ---------------------------------------------------------------- 0
H("0. The honest summary (read this first)")
P("Every number on screen is one of three kinds. Know which kind you are talking about.")
T([["Kind", "Values", "How to describe it"],
   ["**Measured** from the real code", "Lines of code, cyclomatic complexity, cognitive complexity, code smells, duplication %",
    "“We read the file and counted it.”"],
   ["**Predicted** by the trained model", "Predicted defect risk (%), average defect risk",
    "“The Random Forest trained on real bug history estimates it. It is a relative score.”"],
   ["**Estimated** by a simple rule", "Churn, maintenance cost, effort, debt age, test coverage, business criticality, "
    "customer impact, module criticality, urgency",
    "“A transparent rule based on the file’s size, complexity or folder. Labelled as estimated, and the business ones are "
    "left out of the score.”"]],
  [1.55, 2.6, 2.52])
P("**Key point for the review:** a live scan reads the code only, not the Git commit history and not the company’s "
  "business data. So churn and history-based values are estimates, and the business dimensions are shown for "
  "information but **not counted** in the priority score. That is why every file says **“3 of 5 dimensions — "
  "technical-only”**. Say this openly; it is a design choice, not a hidden weakness.")

# ---------------------------------------------------------------- 1
H("1. Complexity (measured)")
P("**What it means:** how many different paths the code can take. More paths = harder to test and easier to break.")
B("The scanner reads every line (skipping blank lines and comments) and counts **decision points**: if, elif, else if, "
  "for, while, except/catch, case, switch, &&, ||, and, or, and the ternary ? :.")
B("**Cyclomatic complexity = 1 + 0.75 × decision points** (rounded, minimum 1). The 0.75 factor stops one long line "
  "with several conditions from being over-counted.")
B("**Cognitive complexity** = cyclomatic + 0.4 × nesting penalty, where each decision point adds its indentation depth "
  "(indent ÷ 4). Deeply nested branches are harder to read, so they count more.")
B("**On screen:** “Complex files” on the Dashboard = files with cyclomatic complexity **above 25**; the Hotspots page "
  "shows each file’s value.")
P("**Justify it:** “This is McCabe’s cyclomatic complexity (1976), the standard measure, counted directly from the "
  "source text for any language.”")

H("2. Code smells, duplication and size (measured)", 12, 4)
d.paragraphs[-1].paragraph_format.keep_with_next = True  # keep the heading with its short table
T([["Smell rule", "Points"],
   ["File longer than 300 lines", "+2"], ["Cyclomatic complexity above 15", "+2"], ["Cognitive complexity above 20", "+2"],
   ["More than 5 deeply indented lines (4+ levels)", "+2"], ["More than 10 lines longer than 120 characters", "+1"],
   ["TODO / FIXME / HACK / XXX / BUG markers", "+1 each, max 3"], ["More than 15 import lines", "+1"]],
  [5.3, 1.37])
B("A file always has at least 1 smell point. **Duplication %** = repeated non-trivial lines (over 20 characters) ÷ "
  "total lines × 100, capped at 35%. **Lines of code** = number of lines in the file.")

# ---------------------------------------------------------------- 3
H("3. Technical risk (static) and predicted risk (model)")
P("**Churn (estimated):** a live scan does not download commit history, so churn is estimated from size: "
  "**churn = 7.5% of lines of code**, **+8** if the path looks like core code (core, app, server, router, auth, handler, "
  "engine, service, model, session). The Hotspots page labels it **“Estimated (no git history scanned)”**.")
P("**Static technical risk = min(100, 1.45 × complexity + 1.8 × smells + 1.1 × churn).** Complexity carries the "
  "most weight, then smells, then change activity. It is capped at 100.")
P("**Predicted defect risk (the ML part):** the scanner builds the model’s 14 inputs for the file (size, Java/test "
  "flags, smells, debt minutes, issue counts, and churn-based values) and the **Random Forest predicts a fault "
  "count**. That count is turned into a 0–100% risk with a logistic curve: **risk = 1 ÷ (1 + e^(−0.24 × (faults − 2)))**, "
  "kept between 6% and 95%. About 2 predicted faults gives 50%.")
B("**Be honest about the inputs:** in a live scan, the history features (lines added/removed, churn, past bugs) are "
  "estimated from size, and author experience is set to a fixed 24 commits. The model’s accuracy (R² 0.413, 35% "
  "lower error) was measured on the real training data; on live scans the risk is a **relative, uncalibrated** "
  "estimate, and the screen says so.")
P("**Composite technical risk (TR) = 50% static risk + 50% predicted risk.** This is the “Risk” number on the "
  "Dashboard’s “Fix these first” list, the Hotspots page and File details.")

# ---------------------------------------------------------------- 4
H("4. Business impact and criticality (estimated, not scored)")
P("A scan cannot know how important a file is to a company, so the scanner fills these with a simple folder-based "
  "rule:")
T([["File path looks like", "Business criticality", "Customer impact", "Module criticality"],
   ["Core code (core, app, server, router, auth, handler, engine, service, model, session)", "92", "88", "92"],
   ["Test file (path contains “test”)", "35", "45", "35"],
   ["Anything else (utility code)", "65", "45", "65"]],
  [3.2, 1.2, 1.15, 1.12])
P("**Business impact (BI) = 0.50 × business criticality + 0.35 × customer impact + 0.15 × module criticality.** "
  "So core files show **90.6**, utility files **58.0** and test files **38.5**.")
P("**Why this is safe to show:** because these are guesses, the score marks business context as “not configured” and "
  "**drops business impact from the calculation**. It is displayed so the user can see what the tool assumed, and the "
  "Hotspots page uses it only to describe a file (for example “high risk, lower business exposure”). The backend can "
  "replace these guesses with real values from a Notion service-tier table or path rules (for example payment code = "
  "95, scripts = 25); the website does not yet offer a button for that, so treat it as future work if asked.")
P("**Urgency** = 0.60 × release proximity + 0.40 × sprint urgency, with default values 75 and 70, giving **73**. Like "
  "business impact, it is **not counted** in technical-only mode.")

# ---------------------------------------------------------------- 5
H("5. Maintenance cost, effort and debt age (estimated)")
T([["Value", "Formula", "Meaning"],
   ["Maintenance cost", "min(100, 0.08 × lines of code)", "Bigger files cost more to keep working (300 lines → 24)"],
   ["Remediation effort", "2.4 × smell points", "More smells = more work to clean up (8 smells → 19.2)"],
   ["Debt age", "60 days for a file flagged as debt (complexity above 16 or more than 4 smells), otherwise 30; "
    "normalised = days ÷ 365 × 100", "How long the problem is assumed to exist (60 days → 16.4)"],
   ["Test coverage (File details)", "max(12, 92 − 1.7 × complexity)", "Rough guess: complex code is usually less tested"]],
  [1.55, 2.6, 2.52])

# ---------------------------------------------------------------- 6
H("6. The final priority score")
P("The five dimensions and their weights are TR 35%, BI 30%, urgency 15%, maintenance 10%, debt age 10%. Dimensions "
  "without real data are removed and the rest are **re-scaled to add up to 100%**. In technical-only mode the score "
  "uses TR, maintenance cost and debt age:")
P("**Base score = (0.35 × TR + 0.10 × maintenance + 0.10 × debt age) ÷ 0.55**", align=A.CENTER)
P("**Final score = 0.85 × base score + 0.15 × (100 − effort)**: cheap, valuable fixes rise to the top.", align=A.CENTER)
B("**Priority level:** Critical 80+, High 60–80, Medium 40–60, Low below 40.")
B("**Quadrant** (from base score and effort): Quick Win = base 60+ and effort ≤ 40; Strategic Refactor = base 60+ and "
  "effort above 40; Opportunistic = base below 60 and effort ≤ 40; Deprioritized = the rest.")

H("Worked example (real values from the live site: src/components/ui/chart.tsx)", 12, 4)
T([["Step", "Calculation", "Result"],
   ["Technical risk (TR)", "50% static + 50% predicted", "93.6"],
   ["Maintenance cost", "0.08 × 303 lines", "24.2"],
   ["Debt age", "60 ÷ 365 × 100", "16.4"],
   ["Base score", "(0.35 × 93.6 + 0.10 × 24.2 + 0.10 × 16.4) ÷ 0.55 = 36.82 ÷ 0.55", "**66.95**"],
   ["Effort", "2.4 × 8 smells", "19.2"],
   ["Final score", "0.85 × 66.95 + 0.15 × (100 − 19.2) = 56.91 + 12.12", "**69.03 (High)**"],
   ["Quadrant", "Base 66.95 ≥ 60 and effort 19.2 ≤ 40", "**Quick Win**"]],
  [1.5, 3.9, 1.27])
P("These are exactly the numbers the AI Copilot and the Priorities page show for this file, so you can open the site "
  "and check them live in front of the reviewer.")

# ---------------------------------------------------------------- 7
H("7. Dashboard numbers")
T([["Card", "How it is calculated"],
   ["Debt health (0–100)", "100 − average static technical risk of all files (minimum 10). 70+ = Good, 50–70 = Warning"],
   ["Quick wins", "Number of files in the Quick Win quadrant"],
   ["Average defect risk", "Average of the model’s predicted defect probability across files"],
   ["Complex files", "Files with cyclomatic complexity above 25"],
   ["Fix these first", "Top 5 files by final priority score, showing their composite technical risk"],
   ["Types of debt found", "Count of flagged debt items by type (complexity or code smell)"],
   ["Hotspots page", "Files whose technical risk or business impact is 70 or more"]],
  [1.8, 4.87])

# ---------------------------------------------------------------- 8
H("8. Questions a reviewer may ask about the numbers")
QA = [
    ("Why these weights (35/30/15/10/10)?", "They are design choices: technical risk matters most, then business impact; they "
     "sum to 100% and live in one config file so a team can change them. We do not claim they are optimal."),
    ("Where does churn come from?", "In a live scan it is estimated from file size and is labelled “Estimated”. Reading "
     "the full Git history is future work; the backtest used real Git history."),
    ("Is business impact real?", "Not for a plain scan. It is a folder-based guess, shown for transparency and excluded "
     "from the score, which is why files show “3 of 5 dimensions — technical-only”."),
    ("Is the predicted risk a real bug probability?", "No. It is a relative risk for comparing files. The model was "
     "trained on Apache Java projects and some live inputs are estimated, so we call it uncalibrated."),
    ("How do you know the ranking is useful?", "The temporal backtest on 6 real repositories: AUC 0.79, clearly better "
     "than random and on par with size and churn rankings."),
    ("Why is test coverage shown if you didn’t run tests?", "It is a rough estimate from complexity, not a measured "
     "coverage. Measuring real coverage would need the project’s test suite to run."),
]
for i, (q, a) in enumerate(QA, 1):
    p = d.add_paragraph(); p.alignment = A.JUSTIFY; p.paragraph_format.space_after = Pt(2)
    runs(p, f"**Q{i}. {q}**  {a}")

d.core_properties.title = "DebtScope UI Values Justification"
d.save(OUT)
print("saved", OUT)
