# 상품 조회·검색·장바구니·주문·결제 등 이커머스 도메인 로그를 생성

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
EVENTS     = ["product_view", "search", "add_to_cart", "checkout", "order_created", "payment_completed"]
# 각 이벤트가 선택될 상대적 발생 확률 정의
WEIGHTS    = [34, 20, 17, 9, 11, 9]
# 상품 카테고리 후보 정의
CATEGORIES = ["food", "fashion", "beauty", "electronics", "home", "sports"]
# 결제수단 후보 정의
PAYMENTS   = ["card", "bank_transfer", "easy_pay", "points"]


# 도메인 특성에 맞는 이벤트 한 건을 생성
def generate(fake: Faker, *, timezone_name: str, environment: str, run_id: str) -> dict:
    # 가중치에 따라 이커머스 이벤트 종류 하나를 선택
    event_type  = random.choices(EVENTS, weights=WEIGHTS, k=1)[0]
    # 임의의 사용자 ID 생성
    user_id     = f"usr_{random.randint(100000, 999999)}"
    # 요청 흐름을 구분할 세션 ID 생성
    session_id  = uuid.uuid4().hex[:20]
    # 임의의 상품 ID 생성
    product_id  = f"prd_{random.randint(10000, 99999)}"
    # 대부분 1개 구매가 되도록 수량을 가중 랜덤 생성
    quantity    = random.choices([1, 2, 3, 4], weights=[70, 20, 7, 3], k=1)[0]
    # 5천~30만원 범위에서 상품 단가 생성
    unit_price  = random.randrange(5000, 300000, 100)

    # 이벤트별 HTTP 메서드·API 경로·기준 지연시간 정의
    routes = {
        "product_view":         ("GET", f"/api/products/{product_id}", 70),
        "search":               ("GET", "/api/search", 95),
        "add_to_cart":          ("POST", "/api/cart/items", 110),
        "checkout":             ("POST", "/api/checkout", 240),
        "order_created":        ("POST", "/api/orders", 310),
        "payment_completed":    ("POST", "/api/payments", 420),
    }
    # 선택된 이벤트의 요청 정보와 기준 지연시간 추출
    method, path, median_latency = routes[event_type]
    # 지정 확률에 따라 HTTP 응답 상태코드 생성
    status = http_status(method, success=0.972, client_error=0.022)

    # 이커머스 도메인 고유 데이터를 구성
    data = {
        "user_id": user_id,
        "session_id": session_id,
        "product_id": product_id,
        "category": random.choice(CATEGORIES),
        "quantity": quantity,
        "unit_price": unit_price,
        "currency": "KRW",
        "campaign": random.choice([None, None, None, "summer_sale", "retargeting", "member_coupon"]),
    }

    # 검색 이벤트일 때 검색어와 검색 결과 수 추가
    if event_type == "search":
        data.update({"keyword": fake.word(), "result_count": random.randint(0, 240)})
    # 주문 흐름 이벤트에는 주문·금액·결제 정보를 추가
    if event_type in {"checkout", "order_created", "payment_completed"}:
        data.update({
            "order_id": f"ord_{uuid.uuid4().hex[:16]}",
            "total_amount": unit_price * quantity,
            "payment_method": random.choice(PAYMENTS),
        })
    # 결제 완료 이벤트에는 성공/실패 결과 추가
    if event_type == "payment_completed":
        # 응답 상태코드가 400 미만이면 승인, 400 이상이면 실패 중 하나를 무작위 선택
        data["payment_result"] = "approved" if status < 400 else random.choice(["declined", "timeout", "cancelled"])

    # 공통 로그 스키마와 이커머스 데이터를 합쳐 최종 이벤트 반환
    return make_base_event(
        fake=fake,
        domain="ecommerce",
        event_type=event_type,
        service_name="commerce-api",
        method=method,
        path=path,
        status_code=status,
        latency=latency_ms(median_latency),
        timezone_name=timezone_name,
        environment=environment,
        run_id=run_id,
        data=data,
    )