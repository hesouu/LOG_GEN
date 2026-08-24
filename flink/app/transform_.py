# -*- coding: utf-8 -*-
# 데이터 전치리/정제 

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Optional

SILVER_SCHEMA_VERSION = "1.0"
# [REJECT] reject 데이터 관리 버전
REJECT_SCHEMA_VERSION = "1.0"

# 데이터 사전 체크 -> 오류 사유를 추가 반환
def _parse_payload(payload: Any):
    # 1. 데이터에 문제가 있으면 => none 처리
        # 1-1. 입력 데이터 자체가 없으면 none               
        if payload is None:
            return None, "payload_null"
        # 1-2. 데이터의 타입이 bytes 라면 utf-8 인코딩 처리 -> 문제발생 -> none
        if isinstance(payload, bytes):              
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError:
                return None, "invalid_utf8"
        # 1-3. 데이터가 문자열 아니면 문자열 강제 변환
        if not isinstance(payload, str):
            payload = str(payload)
    
        # 문자열 => json 객체로 파싱
        # 2. 파싱
        try:
            event = json.loads(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            # 실패하면 None
            return None, "invalid_json"
        # 3. 파싱 결과 검사, dict 타입이 아니면 none
        if not isinstance(event, dict):
            return None, "no_json_object"

        # 4. 정상 파싱
        return event, None

# 실버 kinesis로 전송되는 루틴이므로, 오염 데이터는 누락
def clean_event_payload(payload: Any) -> Optional[str]:
    # 데이터 검수
    event, reject_reason = _parse_payload( payload )
    # 오염데이터인 경우
    if reject_reason is not None:
        return None # 데이터 누락시키기 

    # 클린 작업
    # 딕셔너리 컴프리핸션
    # 값이 없는 컬럼을 배제, 키:값 형태로 1차원 배치
    cleaned = {key: value for key, value in event.items() if value is not None}

    # 전처리 작업 -> 파생변수 추가
    # 딕셔너리에 _silver 키를 추가, 값으로 dict를 배치
    cleaned["_silver"] = {
        "layer": "silver",
        "processor": "apache-flink",
        "schema_version": SILVER_SCHEMA_VERSION,
        "processed_at": datetime.now(timezone.utc).isoformat(), # 처리시간
    }

    # 실버에 저장하기 위해 json 덤프 => 문자열 (객체 직렬화)
    return json.dumps(
        cleaned,                    # 최종 정제/전처리 된 데이터
        ensure_ascii=False,         # 한글, 빈 ascii 문자 -> 원문 그대로
        separators=(",", ":"),      # 간결하게 표현 -> 저용량 처리
        default=str,                # 객체 직렬화가 않되는 값은 강제로 문자열 처리
    )

# reject kinesis로 전송되는 루틴이므로, 정상 데이터는 누락
def reject_event_payload(payload: Any) -> Optional[str]:
    # 데이터 검수
    _, reject_reason = _parse_payload( payload )
    # 오염데이터인 경우
    if reject_reason is not None:
        return None # 데이터 누락시키기 (왜? 오염만 저장하므로 정상데이터는 누락) 

    # 오염 데이터 원형 보존
    if isinstance(payload, bytes):              
        try:
            oir_payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            # 객체의 공식적인 문자열 처리 내용 -> 내용 보존
            oir_payload = repr(payload)
    else:
        oir_payload = payload    


    rejected = {
        "_reject" : {
        "layer": "rejected",
        "processor": "apache-flink",
        "schema_version": SILVER_SCHEMA_VERSION,
        # 오염 데이터의 이유
        "reason": reject_reason,
        "processed_at": datetime.now(timezone.utc).isoformat(), # 처리시간
        },
        # 오류가 난 상태 그대로 보관
        "original_payload":oir_payload
    }

    # 실버에 저장하기 위해 json 덤프 => 문자열 (객체 직렬화)
    return json.dumps(
        rejected,                    # 최종 오염된 데이터
        ensure_ascii=False,         # 한글, 빈 ascii 문자 -> 원문 그대로
        separators=(",", ":"),      # 간결하게 표현 -> 저용량 처리
        default=str,                # 객체 직렬화가 않되는 값은 강제로 문자열 처리
    )