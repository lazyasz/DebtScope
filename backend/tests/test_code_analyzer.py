"""
Tests for Multi-Language AST Code Analyzer & Test Coverage Ingestion.
"""

import os
import tempfile
import pytest
from backend.services.code_analyzer import (
    analyze_single_file,
    scan_repository_tree,
    is_test_file,
    classify_file,
    detect_coverage_artifacts,
)


class TestCodeAnalyzer:
    def test_python_ast_smell_detection(self):
        """Verify AST detection of god methods and nested loops."""
        code = """
def sample_function():
    for i in range(10):
        for j in range(10):
            for k in range(10):
                print(i, j, k)

def god_method_with_lots_of_params(a, b, c, d, e, f, g):
    pass
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "service.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            result = analyze_single_file(tmpdir, "service.py")
            assert result["language"] == "Python"
            assert result["loc"] > 0
            assert result["code_smells_count"] >= 2
            categories = [d["category"] for d in result["debt_items"]]
            assert "COMPLEXITY" in categories
            assert "MAINTENANCE" in categories

    def test_lizard_javascript_analysis(self):
        """Verify multi-language lizard analysis on JavaScript code."""
        js_code = """
function calculateDiscount(price, userType) {
    if (price > 100) {
        if (userType === 'vip') {
            return price * 0.8;
        } else if (userType === 'member') {
            return price * 0.9;
        }
    }
    return price;
}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "pricing.js")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(js_code)

            result = analyze_single_file(tmpdir, "pricing.js")
            assert result["language"] == "JavaScript"
            assert result["loc"] >= 8
            assert result["cyclomatic_complexity"] >= 3.0

    def test_is_test_file_patterns(self):
        assert is_test_file("tests/test_service.py") is True
        assert is_test_file("src/service.spec.ts") is True
        assert is_test_file("src/components/Button.test.jsx") is True
        assert is_test_file("src/main/OrderServiceTest.java") is True
        assert is_test_file("services/payment_service.py") is False
        assert is_test_file("components/Header.jsx") is False
        assert is_test_file("src/main/java/com/squareup/javapoet/MethodSpec.java") is False
        assert is_test_file("services/inspection.py") is False
        assert classify_file("src/main/java/com/squareup/javapoet/MethodSpec.java") == "source"
        assert classify_file("services/inspection.py") == "source"

    def test_coverage_artifact_detection(self):
        """Verify Cobertura XML coverage parsing."""
        cobertura_xml = """<?xml version="1.0" ?>
<coverage line-rate="0.845" branch-rate="0.75" version="1.0">
</coverage>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Without coverage file
            cov, prov = detect_coverage_artifacts(tmpdir)
            assert cov is None
            assert prov == "ESTIMATED"

            # With coverage.xml
            cov_file = os.path.join(tmpdir, "coverage.xml")
            with open(cov_file, "w", encoding="utf-8") as f:
                f.write(cobertura_xml)

            cov, prov = detect_coverage_artifacts(tmpdir)
            assert cov == 84.5
            assert prov == "MEASURED"

    def test_classify_file_categories(self):
        """Verify robust file classification across source/test/docs/config/generated/vendored/build."""
        assert classify_file("src/flask/app.py") == "source"
        assert classify_file("lib/router/index.js") == "source"
        assert classify_file("backend/services/priority.py") == "source"

        assert classify_file("tests/test_auth.py") == "test"
        assert classify_file("test/app.router.js") == "test"
        assert classify_file("src/components/Header.spec.tsx") == "test"
        assert classify_file("tests/fixtures/mock_payload.json") == "test"

        assert classify_file("docs/index.md") == "docs"
        assert classify_file("README.md") == "docs"
        assert classify_file("LICENSE") == "docs"
        assert classify_file("CHANGELOG.rst") == "docs"

        assert classify_file(".eslintrc.json") == "config"
        assert classify_file("tsconfig.json") == "config"
        assert classify_file("tox.ini") == "config"
        assert classify_file("pytest.ini") == "config"

        assert classify_file("dist/bundle.min.js") == "generated"
        assert classify_file("assets/app.min.css") == "generated"
        assert classify_file("proto/service_pb2.py") == "generated"

        assert classify_file("vendor/cache/gems.rb") == "vendored"
        assert classify_file("node_modules/lodash/index.js") == "vendored"

        assert classify_file("Dockerfile") == "build"
        assert classify_file("docker-compose.yml") == "build"
        assert classify_file("package.json") == "build"
        assert classify_file("pyproject.toml") == "build"
        assert classify_file("Makefile") == "build"
        assert classify_file(".github/workflows/ci.yml") == "build"

    def test_multi_language_path_conventions(self):
        """Verify explicit Python, JS/TS, Go, Java, and C# path conventions across test, docs, generated, vendored."""
        # 1. Python
        assert classify_file("tests/test_auth.py") == "test"
        assert classify_file("backend/service_test.py") == "test"
        assert classify_file("tests/conftest.py") == "test"
        assert classify_file("docs/architecture.md") == "docs"
        assert classify_file("proto/auth_pb2.py") == "generated"
        assert classify_file("proto/auth_pb2_grpc.py") == "generated"
        assert classify_file(".venv/lib/python3.11/site-packages/requests/api.py") == "vendored"
        assert classify_file("src/pipeline/worker.py") == "source"

        # 2. JavaScript / TypeScript
        assert classify_file("src/__tests__/App.test.tsx") == "test"
        assert classify_file("components/Modal.spec.ts") == "test"
        assert classify_file("test/unit/router.test.js") == "test"
        assert classify_file("docs/guide.md") == "docs"
        assert classify_file("dist/bundle.min.js") == "generated"
        assert classify_file("build/app.bundle.js") == "generated"
        assert classify_file("node_modules/axios/index.js") == "vendored"
        assert classify_file("bower_components/jquery/jquery.js") == "vendored"
        assert classify_file("src/hooks/useAuth.ts") == "source"

        # 3. Go
        assert classify_file("pkg/server/handler_test.go") == "test"
        assert classify_file("testing/mock_client.go") == "test"
        assert classify_file("godoc/overview.md") == "docs"
        assert classify_file("proto/service.pb.go") == "generated"
        assert classify_file("internal/api/client_generated.go") == "generated"
        assert classify_file("gen/models/user.go") == "generated"
        assert classify_file("vendor/golang.org/x/net/context.go") == "vendored"
        assert classify_file("cmd/server/main.go") == "source"

        # 4. Java
        assert classify_file("src/test/java/com/example/UserServiceTest.java") == "test"
        assert classify_file("src/test/java/com/example/OrderTestCase.java") == "test"
        assert classify_file("javadoc/index.md") == "docs"
        assert classify_file("target/generated-sources/annotations/AutoValue_Foo.java") == "generated"
        assert classify_file("build/generated/source/proto/Message.java") == "generated"
        assert classify_file("third_party/antlr/Parser.java") == "vendored"
        assert classify_file("src/main/java/com/example/PaymentProcessor.java") == "source"

        # 5. C# (.NET)
        assert classify_file("Services.Tests/AuthServiceTest.cs") == "test"
        assert classify_file("MyApp.UnitTests/CalculatorTests.cs") == "test"
        assert classify_file("Specs/LoginSpec.cs") == "test"
        assert classify_file("docfx/api/index.md") == "docs"
        assert classify_file("obj/Debug/net8.0/GeneratedInternalTypeHelper.g.cs") == "generated"
        assert classify_file("Properties/Resources.Designer.cs") == "generated"
        assert classify_file("packages/Newtonsoft.Json/lib/net45/Newtonsoft.Json.cs") == "vendored"
        assert classify_file("src/Core/Controllers/ApiController.cs") == "source"
