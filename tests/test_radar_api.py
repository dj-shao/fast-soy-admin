"""Tests for Radar API endpoints (app/radar/api.py)."""

import pytest
from httpx import AsyncClient

from app.core.code import Code
from app.system.radar.models import RadarQuery, RadarRequest, RadarUserLog

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
async def seed_radar_api_data(app):
    """Seed radar data for API tests."""
    req1 = await RadarRequest.create(
        x_request_id="api-req-001",
        method="GET",
        path="/api/v1/users",
        client_ip="127.0.0.1",
        response_status=200,
        response_body='{"code":"0000","msg":"OK","data":[]}',
        duration_ms=25.0,
    )
    req2 = await RadarRequest.create(
        x_request_id="api-req-002",
        method="POST",
        path="/api/v1/auth/login",
        client_ip="10.0.0.1",
        response_status=200,
        response_body='{"code":"0000","msg":"OK"}',
        duration_ms=60.0,
    )
    req_err = await RadarRequest.create(
        x_request_id="api-req-err-001",
        method="DELETE",
        path="/api/v1/danger",
        client_ip="10.0.0.2",
        response_status=500,
        response_body='{"code":"5000","msg":"Error"}',
        duration_ms=300.0,
        error_type="ValueError",
        error_message="bad value",
        error_traceback="Traceback ...",
    )
    await RadarQuery.create(request=req1, sql_text="SELECT 1", operation="SELECT", duration_ms=2.0, start_offset_ms=1.0)
    await RadarQuery.create(request=req1, sql_text="SELECT * FROM big_table", operation="SELECT", duration_ms=200.0, start_offset_ms=5.0)
    await RadarUserLog.create(request=req1, level="INFO", message="Test log", offset_ms=3.0)

    return {"req1": req1, "req2": req2, "req_err": req_err}


class TestListRequests:
    async def test_default(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 3
        assert len(data["data"]["records"]) >= 3

    async def test_with_path_filter(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests", params={"path_filter": "/api/v1/users"})
        data = resp.json()
        assert data["code"] == "0000"
        assert all("/api/v1/users" in r["path"] for r in data["data"]["records"])

    async def test_with_code_filter(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests", params={"code_filter": "5000"})
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_with_min_duration(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests", params={"min_duration": 100})
        data = resp.json()
        assert data["code"] == "0000"
        assert all(r["durationMs"] >= 100 for r in data["data"]["records"])

    async def test_with_has_error(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests", params={"has_error": True})
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_pagination(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests", params={"page": 1, "page_size": 1})
        data = resp.json()
        assert len(data["data"]["records"]) == 1
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 1

    async def test_page_size_validation(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests", params={"page_size": 200})
        data = resp.json()
        # Exceeds le=100 validation — FastAPI RequestValidationError wraps into 1200
        assert resp.status_code == 200
        assert data["code"] == Code.REQUEST_VALIDATION


class TestRequestDetail:
    async def test_found(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests/api-req-001")
        data = resp.json()
        assert data["code"] == "0000"
        detail = data["data"]
        assert detail["xRequestId"] == "api-req-001"
        assert "queries" in detail
        assert "user_logs" in detail
        assert len(detail["queries"]) >= 2
        assert len(detail["user_logs"]) >= 1

    async def test_not_found(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/requests/nonexistent-id")
        data = resp.json()
        assert data["code"] == "4004"
        assert data["data"] is None


class TestListQueries:
    async def test_default(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/queries")
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 2

    async def test_slow_only(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/queries", params={"slow_only": True, "threshold_ms": 100})
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1
        assert all(r["durationMs"] >= 100 for r in data["data"]["records"])

    async def test_records_include_request_info(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/queries")
        records = resp.json()["data"]["records"]
        for r in records:
            assert "xRequestId" in r
            assert "requestPath" in r


class TestListExceptions:
    async def test_default(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/exceptions")
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1
        for r in data["data"]["records"]:
            assert r.get("errorType") is not None

    async def test_filter_by_path(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/exceptions", params={"path_filter": "danger"})
        data = resp.json()
        assert data["data"]["total"] >= 1

    async def test_filter_by_error_type(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/exceptions", params={"error_type": "ValueError"})
        data = resp.json()
        assert data["data"]["total"] >= 1

    async def test_filter_by_resolved(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/exceptions", params={"resolved": False})
        data = resp.json()
        assert data["data"]["total"] >= 1


class TestResolveException:
    async def test_resolve(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.put("/__radar/api/exceptions/api-req-err-001/resolve", json={"resolved": True})
        data = resp.json()
        assert data["code"] == "0000"

        # Verify resolved
        req = await RadarRequest.get(x_request_id="api-req-err-001")
        assert req.resolved is True

    async def test_unresolve(self, client: AsyncClient, seed_radar_api_data):
        await RadarRequest.filter(x_request_id="api-req-err-001").update(resolved=True)
        resp = await client.put("/__radar/api/exceptions/api-req-err-001/resolve", json={"resolved": False})
        data = resp.json()
        assert data["code"] == "0000"

    async def test_resolve_not_found(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.put("/__radar/api/exceptions/nonexistent/resolve", json={"resolved": True})
        data = resp.json()
        assert data["code"] == "4004"

    async def test_resolve_missing_body(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.put("/__radar/api/exceptions/api-req-err-001/resolve")
        # Missing body — app exception handler wraps validation error
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.REQUEST_VALIDATION


class TestStats:
    async def test_default(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/stats")
        data = resp.json()
        assert data["code"] == "0000"
        stats = data["data"]
        assert stats["request_count"] >= 3
        assert "avg_duration_ms" in stats
        assert "error_count" in stats
        assert "error_rate" in stats
        assert "query_count" in stats
        assert "slow_query_count" in stats
        assert "user_log_count" in stats

    async def test_with_hours(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/stats", params={"hours": 1})
        data = resp.json()
        assert data["code"] == "0000"


class TestDashboard:
    async def test_default(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/dashboard")
        data = resp.json()
        assert data["code"] == "0000"
        stats = data["data"]
        assert "total_requests" in stats
        assert "avg_response_time" in stats
        assert "total_queries" in stats
        assert "total_exceptions" in stats
        assert "success_rate" in stats
        assert "error_rate" in stats
        assert "rps" in stats
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
        assert "distribution" in stats
        assert "response_time_trend" in stats
        assert "query_activity" in stats

    async def test_with_hours(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/dashboard", params={"hours": 24})
        data = resp.json()
        assert data["code"] == "0000"
        assert isinstance(data["data"]["response_time_trend"], list)
        assert isinstance(data["data"]["query_activity"], list)

    async def test_distribution_has_codes(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.get("/__radar/api/dashboard", params={"hours": 1})
        dist = resp.json()["data"]["distribution"]
        assert isinstance(dist, list)
        if dist:
            assert "code" in dist[0]
            assert "count" in dist[0]


class TestPurge:
    async def test_purge(self, client: AsyncClient, seed_radar_api_data):
        resp = await client.delete("/__radar/api/purge", params={"retention_hours": 24})
        data = resp.json()
        assert data["code"] == "0000"
        assert "deleted_count" in data["data"]
        assert isinstance(data["data"]["deleted_count"], int)

    async def test_purge_all_old_data(self, client: AsyncClient, app):
        """Purge with short retention should not delete just-created data."""
        await RadarRequest.create(
            x_request_id="purge-test-001",
            method="GET",
            path="/purge-test",
        )
        resp = await client.delete("/__radar/api/purge", params={"retention_hours": 1})
        data = resp.json()
        assert data["code"] == "0000"
        # Just-created data should still exist
        exists = await RadarRequest.filter(x_request_id="purge-test-001").exists()
        assert exists is True
