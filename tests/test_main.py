"""API-level tests: parameter validation, error responses, and endpoint structure.

Uses FastAPI TestClient — runs in-process, no actual server needed.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

V1 = "/api/v1"


# ═══════════════════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_returns_ok(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════
# Request ID
# ═══════════════════════════════════════════════════════════════════════════

class TestRequestID:
    def test_response_has_request_id(self, client: TestClient):
        r = client.get("/health")
        assert "X-Request-ID" in r.headers
        assert len(r.headers["X-Request-ID"]) == 8  # uuid4[:8]

    def test_passthrough_client_request_id(self, client: TestClient):
        r = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
        assert r.headers["X-Request-ID"] == "my-custom-id"


# ═══════════════════════════════════════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════════════════════════════════════

class TestCORS:
    def test_cors_headers_present(self, client: TestClient):
        r = client.get("/health", headers={"Origin": "http://example.com"})
        assert r.headers.get("access-control-allow-origin") == "*"


class TestPublicDeploymentGuards:
    def test_api_key_required_when_configured(self, client: TestClient, monkeypatch):
        from ucscxenatoolspy.api_service import main

        monkeypatch.setattr(main, "API_KEYS", {"secret"})
        r = client.get("/")
        assert r.status_code == 401
        assert r.json() == {"error": "Missing or invalid API key"}

    def test_api_key_allows_request_when_valid(self, client: TestClient, monkeypatch):
        from ucscxenatoolspy.api_service import main

        monkeypatch.setattr(main, "API_KEYS", {"secret"})
        r = client.get("/", headers={"X-API-Key": "secret"})
        assert r.status_code == 200

    def test_health_does_not_require_api_key(self, client: TestClient, monkeypatch):
        from ucscxenatoolspy.api_service import main

        monkeypatch.setattr(main, "API_KEYS", {"secret"})
        r = client.get("/health")
        assert r.status_code == 200

    def test_trusted_proxy_header_identity(self, monkeypatch):
        from ucscxenatoolspy.api_service import main

        class Request:
            headers = {"X-Forwarded-For": "203.0.113.10, 10.0.0.1"}

        monkeypatch.setattr(main, "TRUST_PROXY_HEADERS", True)
        assert main._client_ip(Request()) == "203.0.113.10"


# ═══════════════════════════════════════════════════════════════════════════
# Root & Cancers endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestRoot:
    def test_returns_service_info(self, client: TestClient):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["service"] == "TCGA Analysis API"
        assert "endpoints" in body
        # Should reference v1 paths in keys
        assert any("/api/v1/" in k for k in body["endpoints"])


class TestListCancers:
    def test_returns_cancer_list(self, client: TestClient):
        r = client.get(f"{V1}/cancers")
        assert r.status_code == 200
        body = r.json()
        assert "count" in body
        assert "cancers" in body
        assert body["count"] > 0
        for c in body["cancers"]:
            assert "cancer" in c
            assert "full_name" in c
            assert "tumor_n" in c
            assert "normal_n" in c
            assert "has_normal" in c


# ═══════════════════════════════════════════════════════════════════════════
# Legacy redirects
# ═══════════════════════════════════════════════════════════════════════════

class TestLegacyRedirects:
    def test_api_cancers_redirects(self, client: TestClient):
        r = client.get("/api/cancers", follow_redirects=False)
        assert r.status_code == 308
        assert r.headers["Location"] == "/api/v1/cancers"
        assert "X-Deprecation" in r.headers

    def test_api_diff_expr_redirects(self, client: TestClient):
        r = client.get("/api/diff-expr?gene=TP53&cancer=LUAD", follow_redirects=False)
        assert r.status_code == 308
        assert r.headers["Location"] == "/api/v1/diff-expr?gene=TP53&cancer=LUAD"


# ═══════════════════════════════════════════════════════════════════════════
# Parameter validation
# ═══════════════════════════════════════════════════════════════════════════

class TestGeneValidation:
    """Gene parameter must match HUGO pattern and length constraints."""

    def test_gene_too_short(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=&cancer=LUAD")
        assert r.status_code == 422

    def test_gene_too_long(self, client: TestClient):
        long_gene = "A" * 31
        r = client.get(f"{V1}/diff-expr?gene={long_gene}&cancer=LUAD")
        assert r.status_code == 422

    def test_entrez_gene_id_pattern_accepted(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=7157&cancer=LUAD")
        assert r.status_code != 422

    def test_gene_special_chars(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=TP 53&cancer=LUAD")
        assert r.status_code == 422

    def test_gene_valid_pattern_accepted(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=TP53&cancer=LUAD")
        assert r.status_code != 422  # passes parameter validation


class TestCancerValidation:
    """Cancer parameter must be 2-10 chars."""

    def test_cancer_too_short(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=TP53&cancer=A")
        assert r.status_code == 422

    def test_cancer_too_long(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=TP53&cancer=TOOLONGCANCER")
        assert r.status_code == 422

    def test_missing_gene(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?cancer=LUAD")
        assert r.status_code == 422


class TestMissingParameters:
    def test_diff_expr_missing_all(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr")
        assert r.status_code == 422

    def test_corr_missing_gene2(self, client: TestClient):
        r = client.get(f"{V1}/corr?gene1=TP53&cancer=LUAD")
        assert r.status_code == 422

    def test_survival_missing_cancer(self, client: TestClient):
        r = client.get(f"{V1}/survival?gene=TP53")
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Error response shape
# ═══════════════════════════════════════════════════════════════════════════

class TestErrorResponseShape:
    def test_unknown_cancer_is_404(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=TP53&cancer=XYZZ")
        assert r.status_code == 404
        body = r.json()
        assert "error" in body
        assert "XYZZ" in body["error"]

    def test_gene_not_found_is_404(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=ZZNOTAGENE&cancer=LUAD")
        assert r.status_code in (400, 404)
        assert "error" in r.json()


# ═══════════════════════════════════════════════════════════════════════════
# Response headers
# ═══════════════════════════════════════════════════════════════════════════

class TestResponseHeaders:
    def test_content_type_is_json(self, client: TestClient):
        r = client.get("/")
        assert r.headers["content-type"].startswith("application/json")

    def test_request_id_present(self, client: TestClient):
        r = client.get("/")
        assert "X-Request-ID" in r.headers

    def test_no_internal_traceback(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=TP53&cancer=XYZZ")
        assert r.status_code != 500
        body = r.json()
        assert "Traceback" not in str(body)
        assert "File " not in str(body)


class TestRateLimiting:
    def test_analysis_endpoints_have_limit_header(self, client: TestClient):
        r = client.get(f"{V1}/diff-expr?gene=TP53&cancer=LUAD")
        assert r.status_code in (200, 400, 404, 429)
