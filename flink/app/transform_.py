# -*- coding: utf-8 -*-
# 데이터 전치리/정제 

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Optional

SILVER_SCHEMA_VERSION = "1.0"

def clean_event_payload(payload: Any) -> Optional[str]:
    # 1. 데이터에 문제가 있으면 => none 처리
    # 1-1. 입력 데이터 자체가 없으면 none               
    if payload is None:
        return None
    # 1-2. 데이터의 타입이 bytes 라면 utf-8 인코딩 처리 -> 문제발생 -> none
    if isinstance(payload, bytes):              
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    # 1-3. 데이터가 문자열 아니면 문자열 강제 변환
    if not isinstance(payload, str):
        payload = str(payload)

    # 문자열 => json 객체로 파싱
    # 2. 파싱
    try:
        event = json.loads(payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        # 실패하면 None
        return None
    # 3. 파싱 결과 검사, dict 타입이 아니면 none
    if not isinstance(event, dict):
        return None

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