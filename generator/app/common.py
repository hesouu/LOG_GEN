from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from faker import Faker

# 응답 코드 처리하는 함수
def http_status(method: str, success: float = 0.965, client_error: float = 0.027) -> int:

    r = random.random()
    # 정상
    if r < success:

        method = method.upper()
        if method == "GET":
            return 200
        if method == "POST":
            return random.choices([200, 201, 202, 204], weights=[48, 32, 15, 5], k=1)[0]
        if method in {"PUT", "PATCH"}:
            return random.choices([200, 204], weights=[80, 20], k=1)[0]
        if method == "DELETE":
            return random.choices([200, 204], weights=[25, 75], k=1)[0]
        return 200
    if r < success + client_error:
        # 클라이언트 오류
        return random.choices([400, 401, 403, 404, 409, 429], weights=[18, 14, 12, 24, 14, 18], k=1)[0]
    # 서버측 오류
    return random.choices([500, 502, 503, 504], weights=[45, 18, 27, 10], k=1)[0]


# 기준 지연시간(median) 주변으로 로그정규분포를 따르는 응답 지연시간(ms) 생성
def latency_ms(median_ms: float, sigma: float = 0.4) -> int:
    value = median_ms * random.lognormvariate(0, sigma)
    return max(1, round(value))


# datetime을 밀리초 단위까지 포함한 ISO 8601 문자열로 변환
def _iso_millis(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


# 도메인별 데이터를 공통 로그 스키마(schema_version, event_id, request/response 등)로 감싸서 반환
def make_base_event(
    *,
    fake: Faker,
    domain: str,
    event_type: str,
    service_name: str,
    method: str,
    path: str,
    status_code: int,
    latency: float,
    timezone_name: str,
    environment: str,
    run_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    # 실제 발생 시각(UTC)을 기준으로 잡고, 이벤트에 필요한 지역 시간대로 변환
    now_utc = datetime.now(timezone.utc)
    occurred_at = now_utc.astimezone(ZoneInfo(timezone_name))

    # 메서드/상태코드에 따라 대략적인 요청·응답 바이트 크기 생성
    request_bytes = random.randint(120, 420) if method == "GET" else random.randint(200, 4000)
    response_bytes = random.randint(300, 6000) if status_code < 400 else random.randint(80, 600)

    return {
        "schema_version": "1.0",
        "record_type": "application_log",
        "event_id": f"evt_{uuid.uuid4().hex}",
        "trace_id": uuid.uuid4().hex,
        "run_id": run_id,
        "occurred_at": _iso_millis(occurred_at),
        "generated_at_utc": _iso_millis(now_utc),
        "domain": domain,
        "event_type": event_type,
        "service": {
            "name": service_name,
            "environment": environment,
        },
        "client": {
            "ip": fake.ipv4(),
            "user_agent": fake.user_agent(),
        },
        "request": {
            "method": method,
            "path": path,
            "request_bytes": request_bytes,
        },
        "response": {
            "status_code": status_code,
            "latency_ms": latency,
            "response_bytes": response_bytes,
        },
        "data": data,
    }