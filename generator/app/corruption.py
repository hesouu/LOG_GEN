# 정상 로그에 결측치·이상값·중복·깨진 JSON 등 의도적인 오염 데이터를 생성

# 타입 힌트 평가를 지연해 최신 타입 문법을 안정적으로 사용
from __future__ import annotations

# 원본 이벤트를 보존한 채 깊은 복사본 생성
import copy
# 이벤트 종류·값·상태 등을 확률적으로 생성
import random
# 값의 타입이 다양한 딕셔너리 타입 힌트에 사용
from typing import Any


# 구조화된 JSON 내부에 적용할 오염 유형 목록
STRUCTURED_CORRUPTIONS = [
    "missing_field",      # 필수 또는 주요 필드를 아예 삭제
    "null_required",      # 필수 필드의 값을 None(null)으로 변경
    "wrong_type",         # 숫자 필드에 문자열/리스트 등 잘못된 자료형 삽입
    "invalid_timestamp",  # 날짜·시간 형식이 잘못된 값으로 변경
    "numeric_outlier",    # 정상 범위를 크게 벗어난 극단적인 숫자값 생성
    "invalid_enum",       # 허용된 값 목록에 없는 잘못된 카테고리 값 삽입
    "negative_latency",   # 응답 지연시간을 음수로 만들어 비정상 데이터 생성
]


# 오염 라벨을 포함하도록 설정된 경우 오염 정보를 이벤트에 추가
def _mark(event: dict[str, Any], corruption_type: str, include_label: bool) -> None:
    # 오염 라벨 출력 옵션이 켜져 있을 때만 실행
    if include_label:
        event["_simulation"] = {
            "is_corrupted": True,
            "corruption_type": corruption_type,
        }


# 선택된 오염 유형에 따라 JSON 구조나 값을 의도적으로 변경
def corrupt_structured(event: dict[str, Any], corruption_type: str, include_label: bool) -> dict[str, Any]:
    # 원본 이벤트를 변경하지 않기 위해 깊은 복사 수행
    result = copy.deepcopy(event)

    # 선택된 오염 유형에 해당하는 처리 수행
    if corruption_type == "missing_field":
        candidates = [
            (result, "event_id"),
            (result, "occurred_at"),
            (result.get("response", {}), "status_code"),
            (result.get("data", {}), next(iter(result.get("data", {"x": 1})), "x")),
        ]
        # 삭제할 필드를 후보 중 무작위로 선택
        parent, key = random.choice(candidates)
        # 선택한 필드를 제거해 missing_field 오류 생성
        parent.pop(key, None)

    # 앞 조건이 아니면 다음 오염 유형을 검사
    elif corruption_type == "null_required":
        # 필수값을 null로 만들 필드를 무작위 선택
        target = random.choice(["event_type", "domain", "occurred_at"])
        # 선택한 필수 필드 값을 None으로 변경
        result[target] = None

    # 앞 조건이 아니면 다음 오염 유형을 검사
    elif corruption_type == "wrong_type":
        # 숫자여야 할 latency_ms에 잘못된 타입 삽입
        result.setdefault("response", {})["latency_ms"] = random.choice(["fast", "120ms", [120]])

    # 앞 조건이 아니면 다음 오염 유형을 검사
    elif corruption_type == "invalid_timestamp":
        # 파싱할 수 없는 잘못된 timestamp 생성
        result["occurred_at"] = random.choice(["2026-99-99T25:61:00", "not-a-timestamp", "08/12/26 4PM"])

    # 앞 조건이 아니면 다음 오염 유형을 검사
    elif corruption_type == "numeric_outlier":
        data = result.setdefault("data", {})
        if result.get("domain") == "smartfactory":
            data["temperature_c"] = random.choice([9999.0, -273.5, 1.0e9])
        elif result.get("domain") == "finance":
            data["amount"] = random.choice([-500000, 10**15])
        elif result.get("domain") == "ecommerce":
            data["quantity"] = random.choice([-2, 1000000])
        else:
            data["ping_ms"] = random.choice([-50, 999999])

    # 앞 조건이 아니면 다음 오염 유형을 검사
    elif corruption_type == "invalid_enum":
        if result.get("domain") == "smartfactory":
            result.setdefault("data", {})["state"] = "UNKNOWN_BROKEN_STATE"
        elif result.get("domain") == "finance":
            result.setdefault("data", {})["channel"] = "carrier_pigeon"
        elif result.get("domain") == "ecommerce":
            result.setdefault("data", {})["currency"] = "KRWW"
        else:
            result.setdefault("data", {})["platform"] = "toaster"

    # 앞 조건이 아니면 다음 오염 유형을 검사
    elif corruption_type == "negative_latency":
        result.setdefault("response", {})["latency_ms"] = -random.randint(1, 5000)

    # 필요하면 어떤 오염을 적용했는지 라벨 추가
    _mark(result, corruption_type, include_label)
    return result


# 설정된 확률에 따라 정상 이벤트를 그대로 두거나 오염 이벤트로 변경
def maybe_corrupt(
    event: dict[str, Any],
    *,
    corruption_rate: float,
    include_label: bool,
    previous_event: dict[str, Any] | None,
) -> tuple[dict[str, Any], str | None, bool]:

    """Return (event, corruption_type, malformed_json_flag)."""
    # 난수가 오염률 이상이면 정상 이벤트 유지
    if random.random() >= corruption_rate:
        return event, None, False

    # 선택 가능한 오염 유형에 깨진 JSON 유형 추가
    available = STRUCTURED_CORRUPTIONS + ["malformed_json"]
    # 직전 이벤트가 있을 때만 중복 이벤트 생성 가능
    if previous_event is not None:
        # 이전 이벤트가 있으면 중복 이벤트도 오염 후보에 추가
        available.append("duplicate")

    # 실제 적용할 오염 유형을 무작위 선택
    corruption_type = random.choice(available)

    # 선택된 오염 유형에 해당하는 처리 수행
    if corruption_type == "duplicate":
        duplicate = copy.deepcopy(previous_event)
        _mark(duplicate, "duplicate", include_label)
        return duplicate, "duplicate", False

    # 선택된 오염 유형에 해당하는 처리 수행
    if corruption_type == "malformed_json":
        marked = copy.deepcopy(event)
        _mark(marked, "malformed_json", include_label)
        return marked, "malformed_json", True

    return (
        corrupt_structured(event, corruption_type, include_label),
        corruption_type,
        False,
    )