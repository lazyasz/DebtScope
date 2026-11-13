"""
Multi-Language AST & Code Quality Analysis Service.

Uses `lizard` for multi-language complexity analysis across Python, JavaScript,
TypeScript, Java, Go, C++, C#, etc. Uses standard library `ast` for Python-specific
deep smell detection.

Detects and parses test coverage artifacts (coverage.xml, lcov.info, jacoco.xml)
or calculates estimated coverage from test-to-source file ratios with explicit
provenance labeling.
"""

import os
import ast
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
import lizard

# Supported extensions mapped to language labels
EXT_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".php": "PHP",
    ".scala": "Scala",
    ".kt": "Kotlin",
}

# Directories to skip during code inspection
EXCLUDED_DIRS = {
    ".git", ".github", ".venv", "venv", "node_modules", "dist", "build",
    "target", ".idea", ".vscode", "__pycache__", ".pytest_cache", ".next",
    "vendor", "coverage", ".coverage",
}


def is_test_file(rel_path: str) -> bool:
    """Detects whether a file path represents a test file."""
    lower = rel_path.lower().replace("\\", "/")
    filename = os.path.basename(lower)
    parts = lower.split("/")
    
    # Check directory components
    if any(p in ("tests", "test", "__tests__", "spec", "specs", "fixtures", "mock", "mocks", "testing", "test_cases") for p in parts[:-1]):
        return True
    
    # Filename prefix/suffix patterns
    name_no_ext, _ = os.path.splitext(filename)
    if filename.startswith("test_") or filename.startswith("test-") or name_no_ext in ("test", "tests", "conftest"):
        return True
    if (
        filename.endswith("_test.py") or filename.endswith("-test.py") or
        filename.endswith(".test.js") or filename.endswith(".spec.js") or
        filename.endswith(".test.jsx") or filename.endswith(".spec.jsx") or
        filename.endswith(".test.ts") or filename.endswith(".spec.ts") or
        filename.endswith(".test.tsx") or filename.endswith(".spec.tsx") or
        filename.endswith("test.java") or filename.endswith("tests.java") or
        filename.endswith("testcase.java") or filename.endswith("testcases.java") or
        filename.endswith("_test.go") or filename.endswith("_spec.rb")
    ):
        return True
    return False


def classify_file(rel_path: str) -> str:
    """
    Classifies a file path into exactly one of:
    - 'source': Production source code (default for code files)
    - 'test': Unit, integration, or e2e tests, fixtures, specs
    - 'docs': Documentation, markdown, reStructuredText, guides
    - 'config': Configuration, linters, tsconfig, env files
    - 'generated': Generated bundles, minified assets, protobuf/grpc stubs
    - 'vendored': Third-party dependencies or vendored packages
    - 'build': Build automation, Dockerfiles, package manifests, CI/CD
    """
    clean = rel_path.lower().replace("\\", "/")
    filename = os.path.basename(clean)
    parts = clean.split("/")

    # 1. Vendored
    if any(p in ("vendor", "node_modules", "third_party", "extern", "bower_components") for p in parts[:-1]):
        return "vendored"

    # 2. Generated
    if (
        filename.endswith(".min.js") or filename.endswith(".min.css") or
        filename.endswith(".map") or filename.endswith(".bundle.js") or
        filename.endswith("_pb2.py") or filename.endswith("_pb2_grpc.py") or
        ".generated." in filename or ".min." in filename
    ):
        return "generated"

    # 3. Build & CI/CD
    build_files = {
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "makefile", "rakefile", "cmakelists.txt", "gemfile",
        "setup.py", "setup.cfg", "pyproject.toml",
        "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
        "pom.xml", "build.gradle", "build.gradle.kts", "gradlew",
        "requirements.txt", "cargo.toml", "cargo.lock", "go.mod", "go.sum",
    }
    if filename in build_files or filename.startswith("dockerfile"):
        return "build"
    if any(p in (".github", ".gitlab", ".circleci", "jenkins", "build", "ci") for p in parts[:-1]):
        return "build"

    # 4. Config Names (e.g. pytest.ini, tox.ini, tsconfig.json, dotfiles)
    config_names = {
        "tsconfig.json", "jsconfig.json", "webpack.config.js", "vite.config.js", "vite.config.ts",
        "rollup.config.js", "babel.config.js", "jest.config.js", "tailwind.config.js",
        "postcss.config.js", "eslint.config.js", "prettier.config.js", "tox.ini",
        "pytest.ini", ".flake8", ".editorconfig", ".gitignore", ".gitattributes"
    }
    if filename in config_names or filename.startswith("."):
        return "config"

    # 5. Tests
    if (
        is_test_file(clean) or
        any(p in ("tests", "test", "__tests__", "spec", "specs", "fixtures", "mock", "mocks") for p in parts[:-1])
    ):
        return "test"

    # 6. Docs
    docs_exts = (".md", ".rst", ".txt", ".adoc", ".pdf")
    docs_names = {"readme", "license", "changelog", "contributing", "authors", "notice", "copying", "history"}
    name_no_ext, ext = os.path.splitext(filename)
    if any(p in ("docs", "doc", "documentation", "site", "guide") for p in parts[:-1]):
        return "docs"
    if ext in docs_exts or name_no_ext in docs_names:
        return "docs"

    # 7. Other Config Extensions
    config_exts = (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".env")
    if ext in config_exts:
        return "config"

    # 8. Default to Source
    return "source"


def detect_coverage_artifacts(repo_dir: str) -> Tuple[Optional[float], str]:
    """
    Scans repository directory for test coverage reports.
    Returns (coverage_pct, provenance).
    - If found and parsed: (pct, "MEASURED")
    - If not found: (None, "ESTIMATED")
    """
    candidates = [
        ("coverage.xml", "cobertura"),
        ("cobertura.xml", "cobertura"),
        ("lcov.info", "lcov"),
        ("jacoco.xml", "jacoco"),
    ]

    for fname, fmt in candidates:
        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            if fname in files:
                full_path = os.path.join(root, fname)
                try:
                    if fmt == "cobertura":
                        tree = ET.parse(full_path)
                        rate = tree.getroot().attrib.get("line-rate")
                        if rate is not None:
                            return round(float(rate) * 100.0, 1), "MEASURED"
                    elif fmt == "jacoco":
                        tree = ET.parse(full_path)
                        for counter in tree.getroot().findall(".//counter[@type='LINE']"):
                            covered = float(counter.attrib.get("covered", 0))
                            missed = float(counter.attrib.get("missed", 0))
                            total = covered + missed
                            if total > 0:
                                return round((covered / total) * 100.0, 1), "MEASURED"
                    elif fmt == "lcov":
                        lines_found = 0
                        lines_hit = 0
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                if line.startswith("LF:"):
                                    lines_found += int(line[3:].strip())
                                elif line.startswith("LH:"):
                                    lines_hit += int(line[3:].strip())
                        if lines_found > 0:
                            return round((lines_hit / lines_found) * 100.0, 1), "MEASURED"
                except Exception:
                    pass

    return None, "ESTIMATED"


class PythonSmellDetector(ast.NodeVisitor):
    """AST visitor to detect specific architectural and maintenance code smells in Python."""

    def __init__(self):
        self.smells = []
        self.loop_depth = 0

    def visit_For(self, node):
        self.loop_depth += 1
        if self.loop_depth >= 3:
            self.smells.append({
                "category": "COMPLEXITY",
                "severity": "HIGH",
                "line": node.lineno,
                "description": f"Deeply nested loop (depth {self.loop_depth}). Significant performance and cognitive burden.",
                "remediation": "Refactor nested iteration using generator expressions, vectorized operations, or helper functions.",
            })
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_While(self, node):
        self.loop_depth += 1
        if self.loop_depth >= 3:
            self.smells.append({
                "category": "COMPLEXITY",
                "severity": "HIGH",
                "line": node.lineno,
                "description": f"Deeply nested while-loop (depth {self.loop_depth}). High risk of unhandled termination conditions.",
                "remediation": "Simplify loop flow control or extract inner body into a pure method.",
            })
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_FunctionDef(self, node):
        # Large parameter count smell
        arg_count = len(node.args.args)
        if arg_count >= 6:
            self.smells.append({
                "category": "MAINTENANCE",
                "severity": "MEDIUM",
                "line": node.lineno,
                "description": f"Function '{node.name}' has {arg_count} parameters, exceeding clean code thresholds (max 5).",
                "remediation": "Introduce a parameter object or dataclass/Pydantic model to encapsulate arguments.",
            })
        # God method smell: long function
        end_lineno = getattr(node, "end_lineno", node.lineno + 1)
        length = end_lineno - node.lineno
        if length > 75:
            self.smells.append({
                "category": "COMPLEXITY",
                "severity": "CRITICAL",
                "line": node.lineno,
                "description": f"God-method '{node.name}' contains {length} lines of code. Exceeds single-responsibility design.",
                "remediation": "Decompose method into cohesive, focused private subroutines.",
            })
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


def analyze_single_file(repo_root: str, rel_path: str) -> Dict[str, Any]:
    """
    Analyzes an individual source code file using lizard and Python AST.
    Returns extracted metrics, detected smells, and language metadata.
    """
    full_path = os.path.join(repo_root, rel_path)
    _, ext = os.path.splitext(rel_path)
    language = EXT_TO_LANGUAGE.get(ext.lower(), "Unknown")

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            code_content = f.read()
    except Exception as e:
        return {
            "rel_path": rel_path,
            "language": language,
            "loc": 0,
            "cyclomatic_complexity": 1.0,
            "cognitive_complexity": 1.0,
            "code_smells_count": 0,
            "debt_items": [],
            "error": str(e),
        }

    # 1. Multi-language lizard analysis
    file_info = lizard.analyze_file(full_path)
    loc = file_info.nloc or 0
    num_funcs = len(file_info.function_list)
    avg_ccn = file_info.average_cyclomatic_complexity or 1.0
    max_ccn = max([f.cyclomatic_complexity for f in file_info.function_list], default=1.0)
    
    # Composite cyclomatic complexity: weighted average favoring peak hotspots
    cyclomatic = round(0.6 * avg_ccn + 0.4 * max_ccn, 2)
    # Cognitive complexity proxy from lizard token count / branching
    cognitive = round(cyclomatic * 1.15, 2)

    debt_items = []

    # 2. Python-specific AST smell detection
    if ext.lower() == ".py":
        try:
            tree = ast.parse(code_content, filename=rel_path)
            detector = PythonSmellDetector()
            detector.visit(tree)
            debt_items.extend(detector.smells)
        except SyntaxError:
            pass
    else:
        # Generic multi-language threshold smells from lizard function metrics
        for fn in file_info.function_list:
            if fn.cyclomatic_complexity >= 15:
                debt_items.append({
                    "category": "COMPLEXITY",
                    "severity": "CRITICAL" if fn.cyclomatic_complexity >= 25 else "HIGH",
                    "line": fn.start_line,
                    "description": f"Function '{fn.name}' has high cyclomatic complexity ({fn.cyclomatic_complexity}).",
                    "remediation": "Extract helper functions or employ polymorphic dispatch to reduce branching.",
                })

    return {
        "rel_path": rel_path,
        "language": language,
        "loc": loc,
        "cyclomatic_complexity": cyclomatic,
        "cognitive_complexity": cognitive,
        "code_smells_count": len(debt_items),
        "debt_items": debt_items,
        "function_count": num_funcs,
        "file_category": classify_file(rel_path),
    }


def scan_repository_tree(repo_root: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Performs full repository code analysis:
    1. Collects all supported source files.
    2. Runs AST/lizard complexity analysis on each file.
    3. Ingests or estimates test coverage with provenance.
    4. Computes composite technical risk and confidence scores.
    """
    source_files = []
    test_files_count = 0
    total_files_count = 0

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext.lower() in EXT_TO_LANGUAGE:
                rel_path = os.path.relpath(os.path.join(root, f), repo_root).replace("\\", "/")
                total_files_count += 1
                if is_test_file(rel_path):
                    test_files_count += 1
                source_files.append(rel_path)

    # Detect coverage
    measured_cov, cov_provenance = detect_coverage_artifacts(repo_root)
    if measured_cov is not None:
        default_coverage = measured_cov
    else:
        # Estimate coverage based on test-to-source ratio
        test_ratio = (test_files_count / max(1, total_files_count)) * 100.0
        # Scaled heuristic: 1:1 test-to-code ratio ≈ 80% coverage
        default_coverage = round(min(90.0, test_ratio * 1.6), 1)

    analyzed_results = []
    for rel_path in source_files:
        analysis = analyze_single_file(repo_root, rel_path)
        analysis["is_test"] = is_test_file(rel_path)
        analysis["coverage_pct"] = default_coverage
        analysis["coverage_provenance"] = cov_provenance
        analyzed_results.append(analysis)

    summary = {
        "total_source_files": len(source_files),
        "test_files_count": test_files_count,
        "coverage_pct": default_coverage,
        "coverage_provenance": cov_provenance,
    }

    return analyzed_results, summary
