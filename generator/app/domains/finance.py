# 로그인·잔액조회·결제·이체·입출금 등 금융 도메인 로그를 생성

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
EVENTS = ["account_login", "balance_inquiry", "card_payment", "transfer", "deposit", "withdrawal"]
# 각 이벤트가 선택될 상대적 발생 확률 정의
WEIGHTS = [12, 28, 25, 17, 10, 8]
# 금융 서비스 접근 채널 후보 정의
CHANNELS = ["mobile", "web", "atm", "open_api"]
# 카드 결제 가맹점 업종 후보 정의
MERCHANT_CATEGORIES = ["grocery", "restaurant", "transport", "shopping", "subscription", "travel"]


# 도메인 특성에 맞는 이벤트 한 건을 생성
def generate(fake: Faker, *, timezone_name: str, environment: str, run_id: str) -> dict:
    # 가중치에 따라 금융 이벤트 종류 하나를 선택
    event_type = random.choices(EVENTS, weights=WEIGHTS, k=1)[0]
    # 임의의 계좌 ID 생성
    account_id = f"acc_{random.randint(10000000, 99999999)}"
    # 임의의 고객 ID 생성
    customer_id = f"cus_{random.randint(100000, 999999)}"
    # 1천~150만원 범위의 거래금액 생성
    amount = random.randrange(1000, 1500000, 1000)

    # 이벤트별 HTTP 메서드·API 경로·기준 지연시간 정의
    routes = {
        "account_login": ("POST", "/api/auth/login", 130),
        "balance_inquiry": ("GET", "/api/accounts/balance", 85),
        "card_payment": ("POST", "/api/cards/payments", 190),
        "transfer": ("POST", "/api/transfers", 250),
        "deposit": ("POST", "/api/deposits", 150),
        "withdrawal": ("POST", "/api/withdrawals", 180),
    }
    # 선택된 이벤트의 요청 정보와 기준 지연시간 추출
    method, path, median_latency = routes[event_type]
    # 금융 서비스 특성에 맞춘 성공/오류 비율로 상태코드 생성
    status = http_status(method, success=0.978, client_error=0.018)

    # 금융 도메인 공통 거래 데이터를 구성
    data = {
        "transaction_id": f"txn_{uuid.uuid4().hex[:18]}",
        "customer_id": customer_id,
        "account_id": account_id,
        "channel": random.choice(CHANNELS),
        "currency": "KRW",
        "risk_score": round(random.betavariate(2, 12) * 100, 2),
    }

    # 로그인 외 이벤트에는 거래금액 필드 추가
    if event_type != "account_login":
        data["amount"] = amount
    # 카드 결제에는 가맹점과 승인 결과 정보 추가
    if event_type == "card_payment":
        data.update({
            "merchant_id": f"mrc_{random.randint(10000, 99999)}",
            "merchant_category": random.choice(MERCHANT_CATEGORIES),
            "authorization_result": "approved" if status < 400 else random.choice(["declined", "review", "timeout"]),
        })
    # 이체에는 수취은행·계좌토큰·처리결과 추가
    if event_type == "transfer":
        data.update({
            "destination_bank": random.choice(["BANK-A", "BANK-B", "BANK-C", "BANK-D"]),
            "destination_account_token": uuid.uuid4().hex[:14],
            "transfer_result": "completed" if status < 400 else random.choice(["rejected", "pending", "timeout"]),
        })
    # 잔액조회 이벤트에는 현재 잔액 값 추가
    if event_type == "balance_inquiry":
        data["balance"] = random.randrange(0, 50000000, 1000)
    # 로그인 이벤트에는 인증수단과 로그인 결과 추가
    if event_type == "account_login":
        data.update({
            "auth_method": random.choice(["password", "biometric", "certificate", "otp"]),
            "login_result": "success" if status < 400 else "failed",
        })

    # 공통 로그 스키마와 금융 데이터를 합쳐 최종 이벤트 반환
    return make_base_event(
        fake=fake,
        domain="finance",
        event_type=event_type,
        service_name="finance-api",
        method=method,
        path=path,
        status_code=status,
        latency=latency_ms(median_latency),
        timezone_name=timezone_name,
        environment=environment,
        run_id=run_id,
        data=data,
    )