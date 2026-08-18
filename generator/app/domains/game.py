# 로그인·세션·매치·아이템 구매·퀘스트 등 게임 도메인 로그를 생성

# 타입 힌트 평가를 지연해 최신 타입 문법을 안정적으로 사용
from __future__ import annotations

# 이벤트 종류·값·상태 등을 확률적으로 생성
import random
# 이벤트·세션·거래 등 고유 식별자 생성
import uuid

# 이름·IP 등 현실적인 가짜 데이터 생성
from faker import Faker

# 공통 HTTP 상태·지연시간·기본 로그 생성 함수 가져오기
from app.common import http_status, latency_ms, make_base_event


# 해당 도메인에서 발생 가능한 이벤트 종류 정의
EVENTS = ["login", "session_heartbeat", "match_started", "match_finished", "item_purchase", "quest_completed"]
# 각 이벤트가 선택될 상대적 발생 확률 정의
WEIGHTS = [8, 35, 14, 14, 9, 20]
# 게임 서버 지역 후보 정의
REGIONS = ["kr", "jp", "sea", "na", "eu"]
# 게임 매치 모드 후보 정의
MODES = ["ranked", "normal", "arena", "coop"]


# 도메인 특성에 맞는 이벤트 한 건을 생성
def generate(fake: Faker, *, timezone_name: str, environment: str, run_id: str) -> dict:
    # 가중치에 따라 게임 이벤트 종류 하나를 선택
    event_type = random.choices(EVENTS, weights=WEIGHTS, k=1)[0]
    # 임의의 플레이어 ID 생성
    player_id = f"ply_{random.randint(1000000, 9999999)}"
    # 게임 접속 세션 ID 생성
    session_id = uuid.uuid4().hex[:20]

    # 이벤트별 HTTP 메서드·API 경로·기준 지연시간 정의
    routes = {
        "login": ("POST", "/game/auth/login", 120),
        "session_heartbeat": ("POST", "/game/session/heartbeat", 38),
        "match_started": ("POST", "/game/matches/start", 95),
        "match_finished": ("POST", "/game/matches/finish", 125),
        "item_purchase": ("POST", "/game/store/purchase", 180),
        "quest_completed": ("POST", "/game/quests/complete", 75),
    }
    # 선택된 이벤트의 요청 정보와 기준 지연시간 추출
    method, path, median_latency = routes[event_type]
    # 게임 API의 성공/오류 비율을 반영해 상태코드 생성
    status = http_status(method, success=0.976, client_error=0.019)

    # 게임 도메인 공통 플레이어/세션 데이터를 구성
    data = {
        "player_id": player_id,
        "session_id": session_id,
        "server_region": random.choices(REGIONS, weights=[55, 10, 12, 13, 10], k=1)[0],
        "player_level": random.randint(1, 100),
        "ping_ms": max(4, int(random.gauss(42, 18))),
        "platform": random.choice(["pc", "mobile", "console"]),
    }

    # 매치 이벤트에는 매치 ID·모드·파티 인원 추가
    if event_type in {"match_started", "match_finished"}:
        data.update({
            "match_id": f"match_{uuid.uuid4().hex[:16]}",
            "mode": random.choice(MODES),
            "party_size": random.randint(1, 5),
        })
    # 매치 종료에는 승패·점수·플레이 시간 추가
    if event_type == "match_finished":
        data.update({
            "result": random.choice(["win", "lose", "draw"]),
            "score": random.randint(0, 50000),
            "duration_seconds": random.randint(180, 2400),
        })
    # 아이템 구매에는 아이템·재화·구매 결과 추가
    if event_type == "item_purchase":
        data.update({
            "item_id": f"item_{random.randint(1000, 9999)}",
            "currency_type": random.choice(["gold", "gem", "cash"]),
            "amount": random.randint(1, 5000),
            "purchase_result": "completed" if status < 400 else "failed",
        })
    # 퀘스트 완료에는 보상 경험치와 골드 추가
    if event_type == "quest_completed":
        data.update({
            "quest_id": f"quest_{random.randint(100, 999)}",
            "reward_xp": random.randint(100, 5000),
            "reward_gold": random.randint(10, 1000),
        })
    # 로그인 이벤트에는 로그인 성공 여부 추가
    if event_type == "login":
        data["login_result"] = "success" if status < 400 else "failed"

    # 공통 로그 스키마와 게임 데이터를 합쳐 최종 이벤트 반환
    return make_base_event(
        fake=fake,
        domain="game",
        event_type=event_type,
        service_name="game-api",
        method=method,
        path=path,
        status_code=status,
        latency=latency_ms(median_latency),
        timezone_name=timezone_name,
        environment=environment,
        run_id=run_id,
        data=data,
    )