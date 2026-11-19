"""Fills the college's Final_Project_Presentation_format template with DebtScope content."""
import copy, os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.oxml.ns import qn
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RB = os.path.join(HERE, "..", "report_build")
FIG = lambda n: os.path.join(RB, "figs", n)
SHOT = lambda n: os.path.join(RB, "shots", n)
prs = Presentation(os.path.join(HERE, "template.pptx"))
S = list(prs.slides)
DEPT = "Department of Computer Science & Engineering, MITSoC, Loni Kalbhor"


def shape(slide, key):
    return next(sh for sh in slide.shapes if sh.name.startswith(f"Google Shape;{key};"))


def first_rpr(sh):
    for p in sh.text_frame.paragraphs:
        for r in p.runs:
            rpr = r._r.find(qn("a:rPr"))
            if rpr is not None:
                return copy.deepcopy(rpr)
    return None


def fill(sh, items, size=None, font=None, color=None, align=None, space_after=4):
    """items: list of str or (text, {bold, bullet, size, color, level}). Rebuilds paragraphs, keeping the first run's look."""
    tf = sh.text_frame
    base = first_rpr(sh)
    txBody = tf._txBody
    for p in list(txBody.findall(qn("a:p"))):
        txBody.remove(p)
    for it in items:
        text, o = (it, {}) if isinstance(it, str) else it
        p = txBody.makeelement(qn("a:p"), {})
        txBody.append(p)
        ppr = p.makeelement(qn("a:pPr"), {})
        p.append(ppr)
        if align:
            ppr.set("algn", align)
        lvl = o.get("level", 0)
        if o.get("bullet"):
            ppr.set("marL", str(int(Inches(0.3 + 0.3 * lvl))))
            ppr.set("indent", str(int(-Inches(0.25))))
            bu = ppr.makeelement(qn("a:buChar"), {"char": "•" if lvl == 0 else "–"})
            ppr.append(bu)
        else:
            ppr.append(ppr.makeelement(qn("a:buNone"), {}))
        sa = ppr.makeelement(qn("a:spcAft"), {})
        sa.append(sa.makeelement(qn("a:spcPts"), {"val": str(space_after * 100)}))
        ppr.insert(0, sa)
        r = p.makeelement(qn("a:r"), {})
        p.append(r)
        rpr = copy.deepcopy(base) if base is not None else r.makeelement(qn("a:rPr"), {})
        r.append(rpr)
        t = r.makeelement(qn("a:t"), {})
        t.text = text
        r.append(t)
        run = None
        from pptx.text.text import _Run
        run = _Run(r, None)
        if size or o.get("size"):
            run.font.size = Pt(o.get("size", size))
        if font:
            run.font.name = font
        run.font.bold = bool(o.get("bold", False))
        c = o.get("color", color)
        if c:
            from pptx.dml.color import RGBColor
            run.font.color.rgb = RGBColor.from_string(c)


def set_title(sh, text):
    fill(sh, [(text, {"bold": True})])


def drop(slide, key):
    sh = shape(slide, key)
    sh._element.getparent().remove(sh._element)


def pic(slide, path, x, y, w=None, h=None):
    """Place an image inside the box (x, y, w, h), keeping its aspect ratio, centred."""
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    return slide.shapes.add_picture(path, Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


def box(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.text_frame.word_wrap = True
    tb.text_frame.text = " "
    r = tb.text_frame.paragraphs[0].runs[0]
    r.font.name = "Calibri"
    return tb


# footers: one consistent department line
for s in S:
    for sh in s.shapes:
        if sh.has_text_frame and sh.text_frame.text.startswith("Department of Computer Science"):
            sh.text_frame.paragraphs[0].runs[0].text = DEPT
            for r in sh.text_frame.paragraphs[0].runs[1:]:
                r.text = ""

BLUE, RED, ORANGE, INK = "1F4E79", "C00000", "BF9000", "000000"

# 1. Title
s = S[0]
fill(shape(s, 48), ["DebtScope: Predictive Engineering Intelligence for Technical Debt Prioritization"], size=30)
t = shape(s, 49)
t.top, t.height = Inches(3.55), Inches(2.6)
fill(t, [("ADT24SOCB0049 :- Adesh Patankar", {"bold": True}), ("ADT24SOCB0369 :- Dhruv Sakhare", {"bold": True}),
         ("ADT24SOCB1349 :- Vaishnavi Pulaparthi", {"bold": True}), ("ADT24SOCB0518 :- Jiya Bhavsar", {"bold": True}),
         ("Guided by", {"bold": True}), ("", {}),
         ("Prof. Sushma Mehetre (Project Guide)", {"bold": True}),
         ("Dr. Rajani Sajjan (HOD, Computer Science & Engineering)", {"bold": True})], size=14, align="ctr", space_after=0)
drop(s, 47)

# 2. Outline
fill(shape(S[1], 60), [(x, {"bullet": True}) for x in [
    "Introduction", "Problem Statement", "Objectives", "Concepts & Methods", "Literature Review",
    "Identification of gaps & scope of work", "Tools and Languages", "Process and Architecture", "Implementation",
    "Results", "Conclusion and Future Work", "References", "Q&A"]], size=18, space_after=2)

# 3. Introduction
s = S[2]
fill(shape(s, 69), [
    "Technical debt is code that works today but makes future changes slower and riskier. Every team has it, but teams "
    "rarely agree on which part to fix first, so the decision is left to intuition.",
    "DebtScope is a web platform that scans a team's GitHub repository, measures every source file, predicts which "
    "files are likely to cause bugs using a model trained on real project history, weighs that risk against business "
    "importance and effort, and returns a ranked, explained list of what to fix first."], size=14, font="Calibri", space_after=6)
shape(s, 69).height = Inches(1.9)
drop(s, 70)
pic(s, SHOT("dashboard_top.jpg"), 1.2, 2.95, 7.6, 3.1)

# 4. Problem statement + objectives
s = S[3]
fill(shape(s, 79), [(x, {"bullet": True}) for x in [
    "Static analysers list thousands of issues but do not say which ones matter most.",
    "Prioritisation needs code metrics, change history, likely future defects and business importance together; "
    "these live in different tools (code, Git, Jira, Notion).",
    "Teams cannot see why a file is risky, so rankings are not trusted or acted upon."]], size=14, font="Calibri")
fill(shape(s, 80), [(x, {"bullet": True}) for x in [
    "Train a defect-prediction model on real, SZZ-labelled project history and measure its accuracy.",
    "Combine five dimensions (risk, business impact, urgency, maintenance cost, debt age) and effort into one "
    "explainable priority score.",
    "Let any user connect their own GitHub, Notion and Jira, with a grounded AI assistant, and validate the ranking "
    "with a temporal backtest."]], size=14, font="Calibri")
shape(s, 81).top = Inches(2.75)
shape(s, 80).top, shape(s, 80).height = Inches(3.4), Inches(2.4)

# 5. Concepts and methods (template numbering: 4.)
s = S[4]
set_title(shape(s, 87), "4. Concepts and Methods")
fill(shape(s, 90), [("1. DEFECT PREDICTION MODEL", {"bold": True}),
                    ("Technical Debt Dataset: 31 Apache projects, SZZ-labelled faults", {"bullet": True}),
                    ("Bronze–Silver–Gold pipeline: 1,037,222 file rows, 12/12 quality checks", {"bullet": True}),
                    ("Random Forest regressor, 100 trees, 14 features", {"bullet": True})], size=13, font="Calibri")
fill(shape(s, 91), [("2. FIVE-DIMENSION PRIORITY SCORE", {"bold": True}),
                    ("TR = 0.5·TR_static + 0.5·TR_ml", {"bullet": True}),
                    ("PS_base = 0.35·TR + 0.30·BI + 0.15·U + 0.10·M + 0.10·Age", {"bullet": True}),
                    ("PS_final = 0.85·PS_base + 0.15·(100 − Effort)", {"bullet": True})], size=13, font="Calibri")
fill(shape(s, 92), [("3. VALIDATION", {"bold": True}),
                    ("Temporal backtest: 6 repositories, features at a past cutoff, bug fixes in the next 12 months",
                     {"bullet": True}),
                    ("Paired bootstrap comparison with size and churn baselines", {"bullet": True})], size=13, font="Calibri")
for k, top, h in [(90, 0.75, 1.75), (91, 2.6, 1.75), (92, 4.45, 1.6)]:
    sh = shape(s, k); sh.left, sh.top, sh.width, sh.height = Inches(0.45), Inches(top), Inches(5.3), Inches(h)
drop(s, 93); drop(s, 94)
pic(s, FIG("quadrant.png"), 5.9, 0.9, 3.9, 5.2)

# 6. Literature survey (template numbering: 5.)
s = S[5]
tbl = shape(s, 103).table
rows = [
    ("1.", "Use of relative code churn measures to predict system defect density (ICSE 2005)", "N. Nagappan, T. Ball",
     "Code churn is a strong predictor of defect density."),
    ("2.", "Data mining static code attributes to learn defect predictors (IEEE TSE 2007)", "T. Menzies et al.",
     "Simple learners on static metrics predict defects on NASA data."),
    ("3.", "A systematic mapping study on technical debt and its management (JSS 2015)", "Z. Li, P. Avgeriou, P. Liang",
     "Prioritisation is among the least supported debt-management activities."),
    ("4.", "The Technical Debt Dataset (PROMISE 2019)", "V. Lenarduzzi et al.",
     "31 Apache projects with SonarQube, Jira and SZZ links; our training data."),
    ("5.", "Your Code as a Crime Scene (2015)", "A. Tornhill",
     "Complexity combined with change frequency finds hotspots."),
]
tr_xml = tbl._tbl.findall(qn("a:tr"))
while len(tbl._tbl.findall(qn("a:tr"))) < len(rows) + 1:
    tbl._tbl.append(copy.deepcopy(tr_xml[-1]))
for ri, row in enumerate(rows, start=1):
    for ci, val in enumerate(row):
        cell = tbl.cell(ri, ci)
        tf = cell.text_frame
        rpr = first_rpr(type("x", (), {"text_frame": tf})) if tf.paragraphs[0].runs else None
        for p in tf.paragraphs[1:]:
            p._p.getparent().remove(p._p)
        p = tf.paragraphs[0]
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
        if p.runs:
            p.runs[0].text = val
        else:
            p.add_run().text = val
        p.runs[0].font.size = Pt(11)
        bu = p._p.find(qn("a:pPr"))
        if bu is not None:
            for b in list(bu):
                if b.tag in (qn("a:buChar"), qn("a:buAutoNum")):
                    bu.remove(b)
            bu.set("marL", "0"); bu.set("indent", "0")
gf = shape(s, 103)
gf.left, gf.top, gf.width = Inches(0.35), Inches(1.0), Inches(9.3)
for ci, w in enumerate([0.6, 3.6, 1.9, 3.2]):
    tbl.columns[ci].width = Inches(w)
for ri, r in enumerate(tbl.rows):
    r.height = Inches(0.4 if ri == 0 else 0.85)

# 7. Identification of gaps & scope of work
s = S[6]
sh = shape(s, 111)
sh.top, sh.height = Inches(1.0), Inches(5.3)
fill(sh, [("Identification of Gaps", {"bold": True, "color": ORANGE, "size": 18}),
          ("Static analysis tools list issues and remediation time, but do not predict where defects will appear.", {"bullet": True}),
          ("Defect-prediction research gives models, but not a ranked, explained to-do list for a team.", {"bullet": True}),
          ("Business importance and effort are ignored by most tools.", {"bullet": True}),
          ("Tools rarely show their accuracy against simple baselines on future defects.", {"bullet": True}),
          ("Scope of Work", {"bold": True, "color": ORANGE, "size": 18}),
          ("Scan any public or private GitHub repository with the user's own account.", {"bullet": True}),
          ("Predict relative defect risk with a model trained on real history.", {"bullet": True}),
          ("Rank files by a five-dimension score with effort, and explain every score.", {"bullet": True}),
          ("Grounded AI assistant, and export to the user's own Jira and Notion.", {"bullet": True}),
          ("Out of scope: automatic code rewriting and calibrated absolute bug probabilities.", {"bullet": True})],
     size=14, font="Calibri", color=INK, space_after=3)

# 15 -> 6. Tools and languages
s = S[14]
fill(shape(s, 181), [(x, {"bullet": True}) for x in [
    "Frontend: React 19, Vite, Tailwind CSS, Recharts",
    "Backend: Python 3.12, FastAPI, SQLAlchemy, Uvicorn",
    "Database: PostgreSQL (production), SQLite (development)",
    "Machine learning: scikit-learn (Random Forest), pandas, NumPy",
    "Data engineering: PySpark, Apache Parquet (Bronze–Silver–Gold)",
    "Code measurement: lizard, Git history via the GitHub REST API",
    "AI assistant: Google Gemini with function calling",
    "Integrations: GitHub, Notion and Jira (OAuth 2.0), Google sign-in",
    "Security: signed session cookies, Fernet-encrypted tokens",
    "Deployment: Docker on Render; VS Code, Git and GitHub"]], size=16, font="Calibri")
sh = shape(s, 181); sh.left, sh.top, sh.width, sh.height = Inches(0.6), Inches(1.1), Inches(8.9), Inches(5.2)

# 14 -> 7. Process and architecture
s = S[13]
sh = shape(s, 172)
fill(sh, [("Scan the user's repository → measure each file → predict defect risk → combine five dimensions and effort → "
           "rank, explain, and export to Jira / Notion.", {})], size=13, font="Calibri")
sh.left, sh.top, sh.width, sh.height = Inches(0.5), Inches(0.95), Inches(9.0), Inches(0.7)
pic(s, FIG("architecture.png"), 0.5, 1.7, 9.0, 4.4)

# 8. Implementation
s = S[7]
for i, (n, cap) in enumerate([("dashboard_top.jpg", "Dashboard"), ("priorities_top.jpg", "Priorities and score"),
                              ("hotspots.jpg", "Code hotspots"), ("copilot.jpg", "AI Copilot")]):
    x, y = 0.4 + (i % 2) * 4.7, 0.95 + (i // 2) * 2.6
    pic(s, SHOT(n), x, y, 4.5, 2.2)
    c = box(s, x, y + 2.2, 4.5, 0.3)
    fill(c, [cap], size=11, font="Calibri", align="ctr")

# 9. Results
s = S[8]
fill(shape(s, 128), [(x, {"bullet": True}) for x in [
    "Defect model: R² = 0.413 (5-fold CV 0.398 ± 0.011); average error 4.74 vs 7.31 faults, 35.2% lower than the baseline.",
    "Temporal backtest (6 repos, 372 files, 108 future bug fixes): AUC 0.791, Spearman ρ 0.365.",
    "Clearly better than random (ΔAUC +0.300, 95% CI [0.198, 0.395]); on par with size and churn rankings.",
    "AI Copilot: 58 / 58 test scenarios passed; 201 automated backend tests pass.",
    "Deployed live: debtscope.onrender.com",
    "Research paper accepted in IJRTI (ISSN 2456-3315), Paper ID IJRTI_303251, Vol. 11, Issue 11, Nov. 2026."]], size=14, font="Calibri", space_after=4)
sh = shape(s, 128); sh.left, sh.top, sh.width, sh.height = Inches(0.4), Inches(0.95), Inches(5.0), Inches(5.3)
pic(s, FIG("backtest.png"), 5.5, 1.1, 4.3, 2.4)
pic(s, FIG("model_vs_baseline.png"), 5.5, 3.7, 4.3, 2.5)

# 10. Conclusion and future work
s = S[9]
fill(shape(s, 138), [("Conclusion", {"bold": True, "color": BLUE}),
                     ("DebtScope turns code metrics, history, a trained defect model and business context into a ranked, "
                      "explained list of what to fix first.", {"bullet": True}),
                     ("Any user can sign in, scan their own repositories and send work to their own Jira and Notion.", {"bullet": True}),
                     ("Its ranking matches strong simple baselines while explaining every score.", {"bullet": True}),
                     ("Research paper accepted for publication in IJRTI (Paper ID IJRTI_303251).", {"bullet": True}),
                     ("Future Work", {"bold": True, "color": BLUE}),
                     ("Retrain on Python, JavaScript and TypeScript projects and calibrate probabilities.", {"bullet": True}),
                     ("Larger backtest with verified bug labels.", {"bullet": True}),
                     ("Team workspaces, trend tracking and pull-request suggestions.", {"bullet": True})],
     size=16, font="Calibri", space_after=5)
sh = shape(s, 138); sh.left, sh.top, sh.width, sh.height = Inches(0.6), Inches(1.0), Inches(8.8), Inches(5.3)

# 11. References
fill(shape(S[10], 143), [
    "[1] V. Lenarduzzi, N. Saarimäki, and D. Taibi, “The Technical Debt Dataset,” in Proc. PROMISE, 2019, pp. 2–11.",
    "[2] N. Nagappan and T. Ball, “Use of relative code churn measures to predict system defect density,” in Proc. ICSE, 2005, pp. 284–292.",
    "[3] T. Menzies, J. Greenwald, and A. Frank, “Data mining static code attributes to learn defect predictors,” IEEE Trans. Softw. Eng., vol. 33, no. 1, pp. 2–13, 2007.",
    "[4] Z. Li, P. Avgeriou, and P. Liang, “A systematic mapping study on technical debt and its management,” J. Syst. Softw., vol. 101, pp. 193–220, 2015.",
    "[5] J. Śliwerski, T. Zimmermann, and A. Zeller, “When do changes induce fixes?,” in Proc. MSR, 2005, pp. 1–5.",
    "[6] L. Breiman, “Random forests,” Machine Learning, vol. 45, no. 1, pp. 5–32, 2001.",
    "[7] S. Lessmann et al., “Benchmarking classification models for software defect prediction,” IEEE Trans. Softw. Eng., vol. 34, no. 4, pp. 485–496, 2008."],
    size=13, space_after=6)

# order: follow the template's numbering (6. Tools, 7. Process before 8. Implementation)
ids = prs.slides._sldIdLst
items = list(ids)
order = [0, 1, 2, 3, 4, 5, 6, 14, 13, 7, 8, 9, 10, 11, 12]
for el in items:
    ids.remove(el)
for i in order:
    ids.append(items[i])
out = os.path.join(HERE, "DebtScope_Final_Presentation.pptx")
prs.save(out)
print("saved", out)
