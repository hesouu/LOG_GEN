# 센서·설비상태·품질검사·알람·정비 등 스마트팩토리 도메인 로그를 생성

# 타입 힌트 평가를 지연해 최신 타입 문법을 안정적으로 사용
from __future__ import annotations

# 이벤트 종류·값·상태 등을 확률적으로 생성
import random
# 이벤트·세션·거래 등 고유 식별자 생성
import uuid

# 이름·IP 등 현실적인 가짜 데이터 생성
from faker import Faker

# 스마트팩토리용 공통 지연시간·기본 로그 생성 함수 가져오기
from app.common import latency_ms, make_base_event


# 해당 도메인에서 발생 가능한 이벤트 종류 정의
EVENTS = ["sensor_reading", "equipment_state", "quality_inspection", "alarm", "maintenance_event"]
# 각 이벤트가 선택될 상대적 발생 확률 정의
WEIGHTS = [62, 18, 10, 6, 4]
# 스마트팩토리 생산 라인 후보 정의
LINES = ["LINE-A", "LINE-B", "LINE-C", "LINE-D"]
# 스마트팩토리 설비 종류 후보 정의
EQUIPMENT_TYPES = ["mixer", "conveyor", "press", "oven", "robot_arm", "packager"]


# 도메인 특성에 맞는 이벤트 한 건을 생성
def generate(fake: Faker, *, timezone_name: str, environment: str, run_id: str) -> dict:
    # 가중치에 따라 스마트팩토리 이벤트 종류 하나를 선택
    event_type = random.choices(EVENTS, weights=WEIGHTS, k=1)[0]
    # 이벤트가 발생한 생산 라인을 무작위 선택
    line_id = random.choice(LINES)
    # 이벤트가 발생한 설비 종류를 무작위 선택
    equipment_type = random.choice(EQUIPMENT_TYPES)
    # 라인·설비종류·번호를 조합해 설비 ID 생성
    equipment_id = f"{line_id}-{equipment_type.upper()}-{random.randint(1, 12):02d}"

    # 이벤트별 HTTP 메서드·수집 API 경로·기준 지연시간 정의
    routes = {
        "sensor_reading": ("POST", "/iot/telemetry", 24),
        "equipment_state": ("POST", "/iot/equipment/state", 28),
        "quality_inspection": ("POST", "/mes/quality", 55),
        "alarm": ("POST", "/iot/alarms", 18),
        "maintenance_event": ("POST", "/mes/maintenance", 70),
    }
    # 선택된 이벤트의 요청 정보와 기준 지연시간 추출
    method, path, median_latency = routes[event_type]
    # IoT 수집 특성을 반영한 가중치로 응답 상태코드 생성
    status = random.choices([200, 202, 400, 500, 503], weights=[82, 15, 1.5, 1, 0.5], k=1)[0]

    # 공장·라인·설비에 대한 공통 도메인 데이터 구성
    data = {
        "plant_id": "PLANT-SEOUL-01",
        "line_id": line_id,
        "equipment_id": equipment_id,
        "equipment_type": equipment_type,
        "message_id": f"msg_{uuid.uuid4().hex[:16]}",
    }

    # 센서 이벤트에는 온도·진동·압력·RPM 값 추가
    if event_type == "sensor_reading":
        data.update({
            "temperature_c": round(random.gauss(72, 5.5), 2),
            "vibration_mm_s": round(max(0.0, random.gauss(2.8, 0.8)), 3),
            "pressure_bar": round(max(0.1, random.gauss(5.2, 0.55)), 3),
            "rpm": max(0, int(random.gauss(1450, 120))),
        })
    # 설비상태 이벤트에는 상태와 누적 가동시간 추가
    elif event_type == "equipment_state":
        data.update({
            "state": random.choices(["RUNNING", "IDLE", "STOPPED", "CHANGEOVER"], weights=[72, 12, 8, 8], k=1)[0],
            "runtime_seconds": random.randint(0, 86400),
        })
    # 품질검사 이벤트에는 샘플·불량수·합격여부 추가
    elif event_type == "quality_inspection":
        # 대부분 불량이 없도록 검사 불량 개수를 가중 랜덤 생성
        defect_count = random.choices([0, 1, 2, 3, 4], weights=[86, 9, 3, 1.5, 0.5], k=1)[0]
        data.update({
            "lot_id": f"LOT-{random.randint(100000, 999999)}",
            "sample_size": 20,
            "defect_count": defect_count,
            "quality_result": "PASS" if defect_count <= 1 else "FAIL",
        })
    # 알람 이벤트에는 알람코드·심각도·확인여부 추가
    elif event_type == "alarm":
        data.update({
            "alarm_code": random.choice(["TEMP_HIGH", "VIBRATION_HIGH", "PRESSURE_LOW", "JAM", "SENSOR_TIMEOUT"]),
            "severity": random.choices(["INFO", "WARN", "CRITICAL"], weights=[20, 60, 20], k=1)[0],
            "acknowledged": random.choice([True, False]),
        })
    # 나머지 maintenance_event에는 정비 관련 데이터 추가
    else:
        data.update({
            "maintenance_type": random.choice(["inspection", "cleaning", "part_replace", "calibration"]),
            "technician_id": f"tech_{random.randint(101, 180)}",
            "downtime_minutes": random.randint(5, 180),
        })

    # 공통 로그 스키마에 스마트팩토리 데이터를 결합
    event = make_base_event(
        fake=fake,
        domain="smartfactory",
        event_type=event_type,
        service_name="factory-ingestion-api",
        method=method,
        path=path,
        status_code=status,
        latency=latency_ms(median_latency, sigma=0.35),
        timezone_name=timezone_name,
        environment=environment,
        run_id=run_id,
        data=data,
    )
    # 일반 사용자 대신 공장 Edge Gateway 정보로 client 필드를 교체
    event["client"] = {
        "ip": fake.ipv4_private(),
        "user_agent": f"edge-gateway/{random.randint(2, 5)}.{random.randint(0, 9)}",
        "device_id": f"gw-{line_id.lower()}-{random.randint(1, 8):02d}",
    }
    # 완성된 스마트팩토리 이벤트 반환
    return event