"""Tests for Radar database query functions (app/radar/db.py)."""

import pytest

from app.system.radar.db import (
    _extract_business_code_and_msg,
    _percentile,
    query_all_queries,
    query_exceptions,
    query_request_detail,
    query_request_timeline,
    query_requests,
    query_stats,
    query_user_logs,
    update_exception_resolved,
)
from app.system.radar.models import RadarQuery, RadarRequest, RadarUserLog


def _extract_business_code(body: str | None) -> str | None:
    """Test shim: return only the code portion from the new (code, msg) tuple."""
    return _extract_business_code_and_msg(body)[0]


@pytest.fixture(scope="session")
async def seed_radar_data(app):
    """Seed radar data for DB function tests. Session-scoped to avoid UNIQUE collisions."""
    req1 = await RadarRequest.create(
        x_request_id="db-req-001",
        method="GET",
        path="/api/v1/users",
        client_ip="127.0.0.1",
        response_status=200,
        response_body='{"code":"0000","msg":"OK","data":[]}',
        duration_ms=30.0,
    )
    req2 = await RadarRequest.create(
        x_request_id="db-req-002",
        method="POST",
        path="/api/v1/auth/login",
        client_ip="10.0.0.1",
        response_status=200,
        response_body='{"code":"0000","msg":"OK","data":{"token":"abc"}}',
        duration_ms=80.0,
    )
    req3 = await RadarRequest.create(
        x_request_id="db-req-003",
        method="GET",
        path="/api/v1/users",
        client_ip="192.168.1.1",
        response_status=200,
        response_body='{"code":"0000","msg":"OK","data":[]}',
        duration_ms=500.0,
    )
    req_err = await RadarRequest.create(
        x_request_id="db-req-err-001",
        method="POST",
        path="/api/v1/system/crash",
        client_ip="10.0.0.2",
        response_status=500,
        response_body='{"code":"5000","msg":"Server Error"}',
        duration_ms=200.0,
        error_type="RuntimeError",
        error_message="something broke",
        error_traceback="Traceback (most recent call last):\n  ...",
    )

    await RadarQuery.create(request=req1, sql_text="SELECT * FROM users", operation="SELECT", duration_ms=5.0, start_offset_ms=2.0)
    await RadarQuery.create(request=req1, sql_text="SELECT count(*) FROM users", operation="SELECT", duration_ms=3.0, start_offset_ms=8.0)
    await RadarQuery.create(request=req3, sql_text="SELECT * FROM users ORDER BY id", operation="SELECT", duration_ms=150.0, start_offset_ms=5.0)

    await RadarUserLog.create(request=req1, level="INFO", message="Fetching users", offset_ms=1.0)
    await RadarUserLog.create(request=req1, level="DEBUG", message="Cache miss", offset_ms=1.5)
    await RadarUserLog.create(request=req_err, level="ERROR", message="Crash detected", offset_ms=50.0)

    return {"req1": req1, "req2": req2, "req3": req3, "req_err": req_err}


_async_mark = pytest.mark.asyncio(loop_scope="session")


class TestQueryRequests:
    pytestmark = _async_mark
    async def test_list_all(self, seed_radar_data):
        total, records = await query_requests(page=1, page_size=50)
        assert total >= 4
        assert len(records) >= 4

    async def test_filter_by_path(self, seed_radar_data):
        total, records = await query_requests(path_filter="/api/v1/users")
        assert total >= 2
        assert all("/api/v1/users" in r["path"] for r in records)

    async def test_filter_by_business_code(self, seed_radar_data):
        total, records = await query_requests(code_filter="5000")
        assert total >= 1
        assert all(r.get("businessCode") == "5000" for r in records)

    async def test_filter_by_min_duration(self, seed_radar_data):
        total, records = await query_requests(min_duration=100.0)
        assert total >= 2
        assert all(r["durationMs"] >= 100.0 for r in records)

    async def test_filter_has_error(self, seed_radar_data):
        total, records = await query_requests(has_error=True)
        assert total >= 1
        assert all(r.get("errorType") is not None for r in records)

    async def test_filter_no_error(self, seed_radar_data):
        total, records = await query_requests(has_error=False)
        assert total >= 3
        assert all(r.get("errorType") is None for r in records)

    async def test_pagination(self, seed_radar_data):
        total, page1 = await query_requests(page=1, page_size=2)
        _, page2 = await query_requests(page=2, page_size=2)
        assert len(page1) == 2
        ids1 = {r["id"] for r in page1}
        ids2 = {r["id"] for r in page2}
        assert ids1.isdisjoint(ids2)

    async def test_records_contain_business_code(self, seed_radar_data):
        _, records = await query_requests(page=1, page_size=50)
        for r in records:
            assert "businessCode" in r


class TestQueryRequestDetail:
    pytestmark = _async_mark
    async def test_detail_found(self, seed_radar_data):
        detail = await query_request_detail("db-req-001")
        assert detail is not None
        assert detail["xRequestId"] == "db-req-001"
        assert "queries" in detail
        assert "user_logs" in detail
        assert len(detail["queries"]) >= 2
        assert len(detail["user_logs"]) >= 2

    async def test_detail_not_found(self, seed_radar_data):
        detail = await query_request_detail("nonexistent-id")
        assert detail is None


class TestQueryRequestTimeline:
    pytestmark = _async_mark
    async def test_timeline(self, seed_radar_data):
        timeline = await query_request_timeline("db-req-001")
        assert len(timeline) >= 4  # 2 queries + 2 user logs
        types = {item["type"] for item in timeline}
        assert "query" in types
        assert "user_log" in types

    async def test_timeline_sorted_by_offset(self, seed_radar_data):
        timeline = await query_request_timeline("db-req-001")
        offsets = [item.get("start_offset_ms") or 0 for item in timeline]
        assert offsets == sorted(offsets)

    async def test_timeline_with_exception(self, seed_radar_data):
        timeline = await query_request_timeline("db-req-err-001")
        types = {item["type"] for item in timeline}
        assert "exception" in types

    async def test_timeline_not_found(self, seed_radar_data):
        timeline = await query_request_timeline("nonexistent-id")
        assert timeline == []


class TestQueryAllQueries:
    pytestmark = _async_mark
    async def test_list_all_queries(self, seed_radar_data):
        total, records = await query_all_queries(page=1, page_size=50)
        assert total >= 3
        assert all("sqlText" in r for r in records)

    async def test_slow_only(self, seed_radar_data):
        total, records = await query_all_queries(slow_only=True, threshold_ms=100.0)
        assert total >= 1
        assert all(r["durationMs"] >= 100.0 for r in records)

    async def test_records_include_request_info(self, seed_radar_data):
        _, records = await query_all_queries(page=1, page_size=50)
        for r in records:
            assert "xRequestId" in r
            assert "requestPath" in r
            assert "requestMethod" in r

    async def test_sorted_by_duration_desc(self, seed_radar_data):
        _, records = await query_all_queries(page=1, page_size=50)
        durations = [r["durationMs"] for r in records]
        assert durations == sorted(durations, reverse=True)


class TestQueryExceptions:
    pytestmark = _async_mark
    async def test_list_exceptions(self, seed_radar_data):
        total, records = await query_exceptions(page=1, page_size=50)
        assert total >= 1
        for r in records:
            assert r.get("errorType") is not None

    async def test_filter_by_path(self, seed_radar_data):
        total, _ = await query_exceptions(path_filter="crash")
        assert total >= 1

    async def test_filter_by_error_type(self, seed_radar_data):
        total, _ = await query_exceptions(error_type="RuntimeError")
        assert total >= 1

    async def test_filter_by_resolved(self, seed_radar_data):
        total, _ = await query_exceptions(resolved=False)
        assert total >= 1

    async def test_no_match(self, seed_radar_data):
        total, records = await query_exceptions(error_type="NonExistentError")
        assert total == 0
        assert records == []


class TestUpdateExceptionResolved:
    pytestmark = _async_mark
    async def test_resolve_exception(self, seed_radar_data):
        success = await update_exception_resolved("db-req-err-001", True)
        assert success is True
        req = await RadarRequest.get(x_request_id="db-req-err-001")
        assert req.resolved is True

    async def test_unresolve_exception(self, seed_radar_data):
        await update_exception_resolved("db-req-err-001", True)
        success = await update_exception_resolved("db-req-err-001", False)
        assert success is True
        req = await RadarRequest.get(x_request_id="db-req-err-001")
        assert req.resolved is False

    async def test_resolve_nonexistent(self, seed_radar_data):
        success = await update_exception_resolved("nonexistent-id", True)
        assert success is False

    async def test_resolve_non_error_request(self, seed_radar_data):
        success = await update_exception_resolved("db-req-001", True)
        assert success is False


class TestQueryUserLogs:
    pytestmark = _async_mark
    async def test_list_all_logs(self, seed_radar_data):
        total, _ = await query_user_logs(page=1, page_size=50)
        assert total >= 3

    async def test_filter_by_level(self, seed_radar_data):
        total, records = await query_user_logs(level="ERROR")
        assert total >= 1
        assert all(r["level"] == "ERROR" for r in records)

    async def test_filter_by_level_case_insensitive(self, seed_radar_data):
        total, _ = await query_user_logs(level="error")
        assert total >= 1

    async def test_pagination(self, seed_radar_data):
        total, records = await query_user_logs(page=1, page_size=1)
        assert len(records) == 1
        assert total >= 3


class TestQueryStats:
    pytestmark = _async_mark
    async def test_stats_all(self, seed_radar_data):
        stats = await query_stats()
        assert stats["request_count"] >= 4
        assert stats["error_count"] >= 1
        assert stats["query_count"] >= 3
        assert stats["avg_duration_ms"] > 0
        assert 0 <= stats["error_rate"] <= 100

    async def test_stats_with_hours(self, seed_radar_data):
        stats = await query_stats(hours=1)
        assert stats["request_count"] >= 4
        assert isinstance(stats["slow_query_count"], int)
        assert isinstance(stats["user_log_count"], int)


class TestPercentile:
    def test_empty(self):
        assert _percentile([], 50) == 0

    def test_single_value(self):
        assert _percentile([10.0], 50) == 10.0
        assert _percentile([10.0], 99) == 10.0

    def test_sorted_values(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(values, 0) == 1.0
        assert _percentile(values, 50) == 3.0
        assert _percentile(values, 100) == 5.0

    def test_p95(self):
        values = list(range(1, 101))
        result = _percentile([float(v) for v in values], 95)
        assert 95 <= result <= 96

    def test_interpolation(self):
        values = [10.0, 20.0]
        result = _percentile(values, 50)
        assert result == 15.0


class TestExtractBusinessCode:
    def test_valid_json(self):
        assert _extract_business_code('{"code":"0000","msg":"OK"}') == "0000"

    def test_code_5000(self):
        assert _extract_business_code('{"code":"5000","msg":"Error"}') == "5000"

    def test_no_code_field(self):
        assert _extract_business_code('{"msg":"OK"}') is None

    def test_invalid_json(self):
        assert _extract_business_code("not json") is None

    def test_none_body(self):
        assert _extract_business_code(None) is None

    def test_empty_body(self):
        assert _extract_business_code("") is None

    def test_numeric_code(self):
        assert _extract_business_code('{"code":200}') == "200"
