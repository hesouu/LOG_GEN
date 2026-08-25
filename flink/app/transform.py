# -*- coding: utf-8 -*-
# 데이터 전처리/정제

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional


SILVER_SCHEMA_VERSION = "1.0"

# [REJECT] Reject 데이터 관리 버전
REJECT_SCHEMA_VERSION = "1.0"


# =========================================================
# 1. JSON 자체에 대한 기본 검사
# =========================================================

# [REJECT]
# 데이터 사전 체크
# JSON 파싱 자체가 불가능한 데이터인지 먼저 검사
def _parse_payload(payload: Any):

    # 1. 입력 데이터 자체가 없으면 Reject
    if payload is None:
        return None, "payload_null"

    # 2. bytes 타입이면 UTF-8 문자열로 변환
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None, "invalid_utf8"

    # 3. 문자열이 아니면 문자열로 변환
    if not isinstance(payload, str):
        payload = str(payload)

    # 4. JSON 문자열 -> Python 객체로 파싱
    try:
        event = json.loads(payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, "invalid_json"

    # 5. JSON이더라도 최상위 구조가 객체(dict)가 아니면 Reject
    if not isinstance(event, dict):
        return None, "no_json_object"

    # 정상적으로 JSON 객체가 만들어짐
    return event, None


# =========================================================
# 2. [추가] JSON 내부 데이터 품질 검사
# =========================================================

# [추가]
# JSON 문법은 정상이지만 내부 데이터가 오염되었는지 검사
#
# 예:
#   event_id 누락
#   event_id = null
#   occurred_at = "INVALID"
#   latency_ms = "120ms"
#   latency_ms = [120]
#   latency_ms = -500
#
# 이런 데이터는 json.loads()에는 성공하기 때문에
# 별도의 데이터 품질 검사가 필요함

def _validate_event(event: dict) -> Optional[str]:
    # -----------------------------------------------------
    # [추가] 필수 필드 검사
    # -----------------------------------------------------
    # 모든 도메인에서 공통적으로 존재해야 하는 필드
    required_fields = [
        "event_id",
        "domain",
        "occurred_at",
    ]

    for field in required_fields:

        # 필수 필드 자체가 없는 경우
        if field not in event:
            return f"missing_required_field:{field}"

        # 필드는 있지만 값이 null인 경우
        if event[field] is None:
            return f"null_required_field:{field}"

    # -----------------------------------------------------
    # [추가] 필수 필드 타입 검사
    # -----------------------------------------------------

    # event_id는 문자열이어야 함
    if not isinstance(event["event_id"], str):
        return "wrong_type:event_id"

    # domain도 문자열이어야 함
    if not isinstance(event["domain"], str):
        return "wrong_type:domain"

    # occurred_at도 문자열이어야 함
    if not isinstance(event["occurred_at"], str):
        return "wrong_type:occurred_at"

    # -----------------------------------------------------
    # [추가] Timestamp 유효성 검사
    # -----------------------------------------------------

    try:
        # Z 형식도 Python datetime에서 처리할 수 있도록 +00:00으로 변경
        datetime.fromisoformat(
            event["occurred_at"].replace("Z", "+00:00")
        )

    except (ValueError, TypeError, AttributeError):
        return "invalid_timestamp"

    # -----------------------------------------------------
    # [추가] latency_ms 타입 및 음수 검사
    # -----------------------------------------------------

    # latency_ms가 있는 이벤트에 대해서만 검사
    if "latency_ms" in event:

        latency = event["latency_ms"]

        # latency 값이 null인 경우
        if latency is None:
            return "null_latency"

        # bool은 Python에서 int의 하위 타입이므로 별도 제외
        if isinstance(latency, bool):
            return "wrong_type:latency_ms"

        # int 또는 float가 아니면 Reject
        #
        # 예:
        # "120ms"
        # "fast"
        # [120]
        if not isinstance(latency, (int, float)):
            return "wrong_type:latency_ms"

        # latency는 음수가 될 수 없으므로 Reject
        if latency < 0:
            return "negative_latency"

    # 모든 검사 통과
    return None


# =========================================================
# 3. Silver 데이터 생성
# =========================================================

# Silver Kinesis로 전송되는 루틴
# 오염 데이터인 경우 None을 반환하여 Silver로 보내지 않음
def clean_event_payload(payload: Any) -> Optional[str]:

    # -----------------------------------------------------
    # 1차 검사 : JSON 자체 검사
    # -----------------------------------------------------

    event, reject_reason = _parse_payload(payload)

    if reject_reason is not None:
        return None

    # -----------------------------------------------------
    # [추가]
    # 2차 검사 : JSON 내부 데이터 품질 검사
    # -----------------------------------------------------

    reject_reason = _validate_event(event)

    # 데이터 품질 검사에서 문제가 발견되면
    # Silver로 보내지 않는다.
    if reject_reason is not None:
        return None

    # -----------------------------------------------------
    # 정상 데이터만 여기까지 도달
    # -----------------------------------------------------

    # 값이 None인 선택 필드는 Silver에서 제거
    #
    # [변경]
    # 중요한 점:
    # 필수 필드 null 검사는 이미 _validate_event()에서 끝났기 때문에
    # 검증되지 않은 필수값을 실수로 삭제하고 Silver로 보내지 않음
    cleaned = {
        key: value
        for key, value in event.items()
        if value is not None
    }

    # Silver 처리 정보 추가
    cleaned["_silver"] = {
        "layer": "silver",
        "processor": "apache-flink",
        "schema_version": SILVER_SCHEMA_VERSION,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Python dict -> JSON 문자열
    return json.dumps(
        cleaned,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


# =========================================================
# 4. Reject 데이터 생성
# =========================================================

# Reject Kinesis로 전송되는 루틴
# 정상 데이터는 None을 반환하여 Reject Stream으로 보내지 않음
def reject_event_payload(payload: Any) -> Optional[str]:

    # -----------------------------------------------------
    # 1차 검사 : JSON 자체 검사
    # -----------------------------------------------------

    event, reject_reason = _parse_payload(payload)

    # -----------------------------------------------------
    # [추가]
    # JSON 자체는 정상이면 데이터 품질 검사를 추가 수행
    # -----------------------------------------------------

    if reject_reason is None:
        reject_reason = _validate_event(event)

    # -----------------------------------------------------
    # 모든 검사를 통과한 정상 데이터
    # -----------------------------------------------------

    # 정상 데이터이므로 Reject Stream으로 보내지 않는다.
    if reject_reason is None:
        return None

    # -----------------------------------------------------
    # 오염 데이터 원형 보존
    # -----------------------------------------------------

    if isinstance(payload, bytes):
        try:
            original_payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            original_payload = repr(payload)
    else:
        original_payload = payload

    # -----------------------------------------------------
    # Reject 저장 데이터 구성
    # -----------------------------------------------------

    rejected = {

        # Reject 처리 정보
        "_reject": {
            "layer": "rejected",
            "processor": "apache-flink",
            "schema_version": REJECT_SCHEMA_VERSION,

            # [추가]
            # 어떤 이유로 Reject 되었는지 저장
            #
            # 예:
            # missing_required_field:event_id
            # null_required_field:event_id
            # wrong_type:latency_ms
            # invalid_timestamp
            # negative_latency
            "reason": reject_reason,

            "processed_at": datetime.now(timezone.utc).isoformat(),
        },

        # 오염된 원본 데이터 보존
        "original_payload": original_payload,
    }

    # Python dict -> JSON 문자열
    return json.dumps(
        rejected,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )