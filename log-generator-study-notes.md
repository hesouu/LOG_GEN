# 로그 생성기(Log Generator) 학습 노트

> 대상 코드: `generator/app/config.py`, `common.py`, `corruption.py`, `traffic.py`, `output.py`, `main.py`, `domains/ecommerce.py`
> (`main_.py`, `ecommerce_.py` 등 언더바 붙은 연습용 파일과 `venv`는 제외)

## 전체 그림

이 프로젝트는 "가짜지만 그럴듯한" 애플리케이션 로그를 계속 만들어내는 시뮬레이터입니다. 역할을 파일 단위로 쪼개면 이렇게 됩니다.

```
config.py     → 환경변수를 읽어서 "이번 실행 설정"을 하나의 객체로 확정
domains/*.py  → 도메인(이커머스/금융/게임/스마트팩토리)별로 이벤트 1건의 "내용"을 만듦
common.py     → 도메인이 만든 내용을 공통 로그 포맷(봉투)으로 포장
traffic.py    → 다음 이벤트를 몇 초 뒤에 만들지 계산 (시간대/요일/버스트 반영)
corruption.py → 일정 확률로 로그를 일부러 망가뜨림 (ETL 학습용 더러운 데이터)
output.py     → 완성된 로그를 stdout/파일에 씀
main.py       → 위 부품들을 순서대로 엮어서 반복 실행하는 지휘자
```

즉 `main.py`가 매 반복(loop)마다 **"이벤트 생성 → 오염 처리 → 출력 → 대기"**를 하고, 나머지 파일들은 그 4단계 각각을 담당하는 부품입니다.

---

## 1. `config.py` — 환경변수 기반 실행 설정

### 이 파일이 하는 일
컨테이너/스크립트를 실행할 때 넘겨주는 환경변수(`DOMAIN`, `BASE_RPS` 등)를 읽어서, 값이 올바른지 검증하고, `Settings`라는 하나의 객체로 묶어줍니다. 나머지 코드는 환경변수를 직접 읽지 않고 이 `Settings` 객체만 참조합니다 — **설정을 다루는 코드를 한 곳에 몰아넣는 패턴**입니다.

### 헬퍼 함수들
```python
def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()

def _env_int(name: str, default: int) -> int:
    return int(_env(name, str(default)))

def _env_float(name: str, default: float) -> float:
    return float(_env(name, str(default)))

def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name, "true" if default else "false").lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")
```
- `os.getenv(name, default)`: 환경변수가 없으면 `default`를 대신 사용합니다. 환경변수는 항상 **문자열**이라서, 정수/실수/불리언이 필요하면 직접 변환(`int(...)`, `float(...)`)해줘야 합니다. `_env_int`, `_env_float`가 그 변환을 대신 해주는 함수입니다.
- `_env_bool`은 `"true"`, `"1"`, `"yes"`처럼 사람마다 다르게 쓸 수 있는 boolean 표현들을 다 받아주고, 그 외 값이면 `ValueError`를 던져서 오타를 조기에 잡아냅니다.
- 함수 이름 앞의 `_`(언더스코어)는 "이 모듈 밖에서는 쓰지 말라"는 파이썬의 관례적 표시(강제는 아님)입니다.

### `Settings` 클래스
```python
@dataclass(frozen=True)
class Settings:
    domain: str
    duration_seconds: int
    max_events: int
    base_rps: float
    ...
    seed: int | None
```
- `@dataclass`는 `__init__`, `__repr__` 같은 반복적인 코드를 자동으로 만들어주는 데코레이터입니다. 필드만 선언하면 생성자가 자동으로 생깁니다.
- `frozen=True`는 인스턴스를 만든 뒤 값을 바꿀 수 없게(불변, immutable) 만듭니다. "실행 설정은 한 번 정해지면 프로그램이 끝날 때까지 바뀌면 안 된다"는 의도를 코드로 강제한 것입니다.
- `seed: int | None`은 파이썬 3.10+ 문법으로 "정수 또는 None"이라는 뜻입니다. 파일 맨 위 `from __future__ import annotations` 덕분에 이 타입 힌트들이 실행 시점에 즉시 평가되지 않고 문자열처럼 지연 평가되어, 오래된 파이썬에서도 최신 타입 문법을 안전하게 쓸 수 있습니다.

### `from_env()` — 검증하며 값 읽기
```python
@classmethod
def from_env(cls) -> "Settings":
    domain = _env("DOMAIN", "ecommerce").lower()
    if domain not in VALID_DOMAINS:
        raise ValueError(f"DOMAIN must be one of: {', '.join(sorted(VALID_DOMAINS))}")
    ...
    return cls(domain=domain, ...)
```
- `@classmethod`는 인스턴스 없이 `Settings.from_env()`처럼 클래스 자체에서 바로 호출할 수 있게 해주는 데코레이터입니다. 첫 번째 인자 `cls`는 파이썬이 자동으로 넘겨주는 "클래스 자신"(여기선 `Settings`)입니다.
- 각 환경변수를 읽을 때마다 바로 유효성 검사를 하고, 잘못되면 `ValueError`를 던집니다. `main.py`에서 이 예외를 잡아서 `[configuration-error] ...` 형태로 출력하고 종료 코드 2를 반환하는 구조입니다(아래 `main.py` 참고).
- 마지막에 `cls(...)`로 검증이 끝난 값들만 모아서 `Settings` 인스턴스를 생성합니다.

> **참고(주의할 점)**: `from_env()` 안에서 `duration_seconds == 0 and max_events == 0` 검사가 `max_events = _env_int(...)`로 **정의되기 전**에 실행됩니다. 지금은 `run-local.sh`/`run-generator.sh`가 항상 `DURATION_SECONDS`에 0이 아닌 값을 넘겨서 이 줄까지 도달하지 않아 문제가 드러나지 않았지만, `DURATION_SECONDS=0`으로 실행하면 `UnboundLocalError`가 날 수 있는 순서 버그입니다. 다음 프로젝트에서 이 패턴을 가져다 쓸 때는 "검증 로직이 참조하는 변수가 그 위에서 이미 정의됐는지" 순서를 한 번 더 확인하는 게 좋습니다.

---

## 2. `common.py` — 공통 로그 스키마 조립

### 이 파일이 하는 일
4개 도메인 파일이 공통으로 쓰는 세 함수를 제공합니다.
- `http_status(...)`: 그럴듯한 확률로 HTTP 상태코드를 생성
- `latency_ms(...)`: 그럴듯한 응답 지연시간(ms)을 생성
- `make_base_event(...)`: 도메인이 만든 데이터를 공통 로그 포맷으로 감싸기

**핵심 설계 아이디어**: "도메인마다 다른 부분(`data`)"과 "모든 도메인에 공통인 부분(`event_id`, `occurred_at`, `request`, `response` 등)"을 분리해서, 공통 부분은 여기 한 곳에서만 관리합니다. 도메인 파일들은 자기만의 `data`를 만들고 `make_base_event`를 호출하기만 하면 됩니다.

### `http_status`
```python
def http_status(method: str, success: float = 0.965, client_error: float = 0.027) -> int:
    r = random.random()
    if r < success:
        method = method.upper()
        if method == "GET":
            return 200
        if method == "POST":
            return random.choices([200, 201, 202, 204], weights=[48, 32, 15, 5], k=1)[0]
        ...
    if r < success + client_error:
        return random.choices([400, 401, 403, 404, 409, 429], weights=[18, 14, 12, 24, 14, 18], k=1)[0]
    return random.choices([500, 502, 503, 504], weights=[45, 18, 27, 10], k=1)[0]
```
- `random.random()`은 0.0~1.0 사이 실수를 균등하게 뽑습니다. 이 값이 `success`보다 작으면 "성공", `success ~ success+client_error` 사이면 "클라이언트 오류(4xx)", 그 이상이면 "서버 오류(5xx)"로 분기합니다. 즉 확률 구간을 숫자 축 위에 나눠놓고 주사위를 굴리는 방식입니다.
- `random.choices(모집단, weights=가중치, k=1)[0]`: 모집단 중 하나를 가중치 비율대로 무작위 선택합니다. 예를 들어 POST 성공 시 `200`이 48, `201`이 32의 비율로 나오도록 한 것 — 실제 API는 200만 나오지 않고 201(생성됨), 202(비동기 접수), 204(내용 없음)도 섞여 나온다는 걸 흉내낸 겁니다.

### `latency_ms`
```python
def latency_ms(median_ms: float, sigma: float = 0.4) -> int:
    value = median_ms * random.lognormvariate(0, sigma)
    return max(1, round(value))
```
- 실제 API 응답 시간은 "가끔 아주 느린 값이 튀는" 비대칭 분포를 가집니다(오른쪽으로 긴 꼬리). 이런 분포를 흉내내기 좋은 게 **로그정규분포(log-normal distribution)**입니다.
- `random.lognormvariate(0, sigma)`는 평균 1 근처를 중심으로 오른쪽으로 치우친 양수를 반환합니다. 여기에 기준값(`median_ms`, 이벤트별로 다르게 지정된 "평범한 경우의 지연시간")을 곱해서 그 기준 주변에서 흔들리는 지연시간을 만듭니다.
- `sigma`가 클수록 변동폭(가끔 튀는 정도)이 커집니다. `smartfactory.py`는 `latency_ms(median_latency, sigma=0.35)`처럼 기본값과 다르게 넘기기도 합니다.
- `max(1, round(value))`로 최소 1ms는 보장하고 정수로 반올림합니다.

### `make_base_event` — 공통 봉투 만들기
```python
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
    now_utc = datetime.now(timezone.utc)
    occurred_at = now_utc.astimezone(ZoneInfo(timezone_name))

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
        "service": {"name": service_name, "environment": environment},
        "client": {"ip": fake.ipv4(), "user_agent": fake.user_agent()},
        "request": {"method": method, "path": path, "request_bytes": request_bytes},
        "response": {"status_code": status_code, "latency_ms": latency, "response_bytes": response_bytes},
        "data": data,
    }
```
- 매개변수 목록 맨 앞의 `*`는 "이 뒤 인자들은 반드시 `이름=값` 형태의 키워드 인자로만 넘길 수 있다"는 뜻입니다(위치 인자 금지). 인자가 12개나 되기 때문에, 순서를 몰라도 이름만 맞으면 되도록 강제한 겁니다 — 도메인 파일들이 실제로 `make_base_event(fake=fake, domain="ecommerce", ...)`처럼 전부 이름을 붙여 호출하는 이유입니다.
- 시각을 **UTC로 먼저 구하고(`datetime.now(timezone.utc)`)**, 그걸 `ZoneInfo(timezone_name)`으로 원하는 지역 시간대로 변환합니다. `occurred_at`(지역 시간)과 `generated_at_utc`(UTC)는 사실 같은 순간을 두 가지 표기로 담은 것입니다 — 실제 분산 시스템 로그에서 흔히 두 값을 같이 남기는 이유(지역 표시용 + 정렬/집계용)를 재현한 것입니다.
- `fake.ipv4()`, `fake.user_agent()`는 Faker 라이브러리가 제공하는 "그럴듯한 가짜 값 생성기"입니다. `Faker` 인스턴스 하나(`fake`)를 여러 도메인 함수가 공유해서 씁니다.
- `request_bytes`/`response_bytes`는 GET이면 작게, 그 외(POST 등 바디가 있는 요청)면 크게 나오도록 범위를 다르게 잡은 것 — 실제 트래픽 특성을 단순 규칙으로 흉내낸 예시입니다.
- 반환값은 그냥 **중첩 딕셔너리**입니다. 이게 나중에 `output.py`에서 `json.dumps`로 한 줄 JSON(JSONL)이 됩니다.

---

## 3. `domains/ecommerce.py` — 도메인별 로그 내용 만들기 (대표 예시)

> `finance.py`, `game.py`, `smartfactory.py`도 구조는 완전히 동일합니다(이벤트 목록 정의 → 이벤트별 라우트/지연시간 매핑 → `data` 구성 → `make_base_event` 호출). 도메인 지식(필드 이름, 값 범위)만 다를 뿐이라 하나를 이해하면 나머지는 그대로 응용됩니다.

### 이벤트 종류와 발생 비율
```python
EVENTS     = ["product_view", "search", "add_to_cart", "checkout", "order_created", "payment_completed"]
WEIGHTS    = [34, 20, 17, 9, 11, 9]
CATEGORIES = ["food", "fashion", "beauty", "electronics", "home", "sports"]
PAYMENTS   = ["card", "bank_transfer", "easy_pay", "points"]
```
- `EVENTS`와 `WEIGHTS`는 인덱스로 짝지어집니다. `product_view`가 34, `search`가 20 비율로 뽑힌다는 뜻 — 실제 이커머스에서 "둘러보기"가 "결제"보다 훨씬 많이 일어나는 깔때기(funnel) 구조를 반영한 겁니다.

### `generate` 함수
```python
def generate(fake: Faker, *, timezone_name: str, environment: str, run_id: str) -> dict:
    event_type  = random.choices(EVENTS, weights=WEIGHTS, k=1)[0]
    user_id     = f"usr_{random.randint(100000, 999999)}"
    session_id  = uuid.uuid4().hex[:20]
    product_id  = f"prd_{random.randint(10000, 99999)}"
    quantity    = random.choices([1, 2, 3, 4], weights=[70, 20, 7, 3], k=1)[0]
    unit_price  = random.randrange(5000, 300000, 100)
```
- `main.py`가 `GENERATORS[settings.domain]`으로 이 함수를 골라서 매 반복마다 호출합니다. 시그니처(`fake`, `timezone_name`, `environment`, `run_id`)는 4개 도메인 파일이 전부 동일하게 맞춰놨습니다 — `main.py`가 도메인이 뭔지 몰라도 똑같은 방식으로 호출할 수 있게(다형성) 하기 위한 약속입니다.
- `quantity`는 "1개 구매가 압도적으로 많다(70%)"는 현실을 가중치로 표현했습니다.
- `uuid.uuid4().hex[:20]`: 무작위 UUID를 만들고 하이픈 없는 32자 16진수 문자열(`hex`)에서 앞 20자만 잘라 세션 ID로 씁니다.

### 이벤트별 요청 정보 매핑
```python
routes = {
    "product_view":         ("GET", f"/api/products/{product_id}", 70),
    "search":               ("GET", "/api/search", 95),
    "add_to_cart":          ("POST", "/api/cart/items", 110),
    "checkout":             ("POST", "/api/checkout", 240),
    "order_created":        ("POST", "/api/orders", 310),
    "payment_completed":    ("POST", "/api/payments", 420),
}
method, path, median_latency = routes[event_type]
status = http_status(method, success=0.972, client_error=0.022)
```
- 딕셔너리 값으로 `(메서드, 경로, 기준지연시간)` **튜플**을 넣어두고, 방금 뽑은 `event_type`을 키로 한 번에 꺼내(`routes[event_type]`) 세 변수에 동시에 풀어 담습니다(튜플 언패킹). "이벤트 → API 스펙" 매핑을 한눈에 보이는 표처럼 관리하는 패턴 — 다음 프로젝트에서도 그대로 쓰기 좋은 아이디어입니다.
- `checkout`/`order_created`/`payment_completed`처럼 뒤로 갈수록 처리할 일이 많은 이벤트일수록 `median_latency`(70 → 420)를 크게 잡아, `common.latency_ms()`가 그 기준 주변에서 지연시간을 생성하게 했습니다.

### 도메인 고유 데이터(`data`) 구성
```python
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

if event_type == "search":
    data.update({"keyword": fake.word(), "result_count": random.randint(0, 240)})
if event_type in {"checkout", "order_created", "payment_completed"}:
    data.update({
        "order_id": f"ord_{uuid.uuid4().hex[:16]}",
        "total_amount": unit_price * quantity,
        "payment_method": random.choice(PAYMENTS),
    })
if event_type == "payment_completed":
    data["payment_result"] = "approved" if status < 400 else random.choice(["declined", "timeout", "cancelled"])
```
- 모든 이벤트에 공통인 필드를 먼저 딕셔너리로 만들고, 이벤트 종류에 따라 `if`로 필드를 **추가**해나가는 방식입니다. 예를 들어 `search` 이벤트에만 `keyword`/`result_count`가 붙고, 결제 관련 이벤트에만 `order_id`/`total_amount`가 붙습니다.
- `random.choice([None, None, None, "summer_sale", ...])`처럼 리스트에 `None`을 여러 번 넣는 건 "캠페인이 없는 경우가 더 흔하다"는 확률을 리스트 길이로 대충 흉내낸 간단한 트릭입니다(정교하게 하려면 `random.choices`+`weights`를 쓰는 게 낫지만, 이 정도 정밀도면 충분하다고 판단한 것).
- `status < 400`으로 성공/실패를 나눠서, 결제 실패 시엔 다른 값이 들어가게 했습니다 — 앞서 만든 HTTP 상태코드와 도메인 데이터가 서로 앞뒤가 맞도록(정합성 있게) 연결한 부분입니다.

### 마무리: 공통 스키마로 포장
```python
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
```
지금까지 만든 재료(`event_type`, `method`, `path`, `status`, `data` 등)를 `common.make_base_event()`에 그대로 넘기기만 하면, `event_id`/`occurred_at`/`request`/`response` 같은 공통 필드가 붙은 완성된 로그 한 건이 반환됩니다.

---

## 4. `traffic.py` — 시간대/요일/버스트를 반영한 발생 속도

### 이 파일이 하는 일
"다음 이벤트를 몇 초 뒤에 만들지"를 계산해서 `main.py`의 `time.sleep(...)`에 넘겨줍니다. 그냥 일정한 간격이 아니라, **시간대별로 트래픽이 오르내리고, 가끔 갑자기 몰리는(버스트)** 현실적인 패턴을 흉내냅니다.

### 시간대별 가중치 테이블
```python
HOURLY_PROFILE = {
    "ecommerce": [0.25, 0.20, 0.18, ..., 1.95, 1.85, 1.25, 0.65],  # 24개(0시~23시)
    "finance": [...],
    "smartfactory": [...],
    "game": [...],
}
```
- 리스트의 인덱스가 그대로 "몇 시"를 의미합니다(0번째=0시, 23번째=23시). 값이 1.0이면 "기본 RPS와 같다", 2.0이면 "기본 RPS의 2배"라는 뜻입니다.
- 도메인마다 패턴이 다릅니다: 이커머스는 저녁 시간대(19~21시) 최대, 금융은 평일 오전~낮 시간대 최대, 스마트팩토리는 24시간 비교적 일정, 게임은 야간(20~21시) 최대 — 실제 업종별 인사이트를 숫자로 미리 박아둔 것입니다.

### `TrafficController` 클래스
```python
class TrafficController:
    def __init__(self, domain: str, base_rps: float, timezone: str, time_scale: float = 1.0):
        self.domain = domain
        self.base_rps = base_rps
        self.tz = ZoneInfo(timezone)
        self.time_scale = time_scale
        self._burst_events_left = 0
        self._burst_multiplier = 1.0
```
- 생성자에서 기본 설정을 저장하고, "지금 버스트 상태인지"를 나타내는 두 상태값(`_burst_events_left`, `_burst_multiplier`)을 0/1.0으로 초기화합니다. 앞에 `_`가 붙은 건 클래스 내부에서만 쓰는 상태라는 표시입니다.

### 요일 보정
```python
def _calendar_multiplier(self, now: datetime) -> float:
    hourly = HOURLY_PROFILE[self.domain][now.hour]
    weekday = now.weekday()  # Mon=0
    if self.domain == "finance" and weekday >= 5:
        return hourly * 0.55   # 주말 금융은 평일의 55%
    if self.domain == "ecommerce" and weekday >= 5:
        return hourly * 1.18   # 주말 이커머스는 18% 증가
    ...
    return hourly
```
- `now.weekday()`는 월요일이 0, 일요일이 6입니다. `>= 5`는 토/일(주말)을 뜻합니다.
- 도메인별로 "주말에 오르는지 내리는지"까지 다르게 반영했습니다 — 금융/공장은 주말에 줄고, 이커머스/게임은 주말에 늘어난다는 실제 업종 특성을 그대로 숫자로 표현했습니다.

### 버스트(갑작스런 트래픽 폭증)
```python
def _burst_factor(self) -> float:
    if self._burst_events_left > 0:
        self._burst_events_left -= 1
        return self._burst_multiplier

    if random.random() < 0.004:
        self._burst_events_left = random.randint(8, 35)
        self._burst_multiplier = random.uniform(2.0, 5.0)
        return self._burst_multiplier

    return 1.0
```
- 이벤트 하나가 생성될 때마다 0.4% 확률로 "버스트"가 시작됩니다. 시작되면 앞으로 8~35건 동안 트래픽이 2~5배로 뛰도록 상태를 저장해두고, 그 이벤트 수가 소진될 때까지(`_burst_events_left`가 0이 될 때까지) 계속 배율을 적용합니다.
- 이런 상태를 객체(`self`)에 저장해두고 호출될 때마다 줄여나가는 패턴은, "한 번의 확률 판정으로 여러 번에 걸친 효과를 만드는" 흔한 시뮬레이션 기법입니다. 마케팅 캠페인, 장비 알람 폭주, 게임 이벤트 같은 상황을 흉내냅니다.

### 최종 RPS와 다음 대기시간
```python
def current_rps(self) -> float:
    now = datetime.now(self.tz)
    calendar = self._calendar_multiplier(now)
    jitter = random.uniform(0.85, 1.15)
    burst = self._burst_factor()
    return max(0.02, self.base_rps * calendar * jitter * burst)

def next_sleep_seconds(self) -> float:
    interval = random.expovariate(self.current_rps())
    return min(interval / self.time_scale, 10.0)
```
- 최종 RPS = 기본 RPS × 시간대/요일 배율 × ±15% 흔들림(jitter) × 버스트 배율. 여러 요인을 곱으로 합성하는 구조입니다.
- `random.expovariate(rate)`는 **지수분포**를 따르는 난수를 반환합니다. "평균 발생률이 일정한 무작위 사건들 사이의 간격은 지수분포를 따른다"는 포아송 과정(Poisson process)의 성질을 이용한 것 — RPS가 2면 평균 0.5초 간격이 나오되, 매번 정확히 0.5초가 아니라 확률적으로 들쭉날쭉한 간격이 나옵니다(진짜 트래픽처럼).
- `TIME_SCALE`로 대기시간을 나눠서 시연/테스트할 때 배속으로 돌릴 수 있게 했고, 최대 10초로 캡을 씌워 너무 오래 멈추지 않게 했습니다.

---

## 5. `corruption.py` — 의도적으로 로그를 오염시키기

### 이 파일이 하는 일
정상 로그를 일정 확률로 "더러운 데이터"로 바꿔서 반환합니다. 실무에서 ETL/데이터 파이프라인은 항상 이런 지저분한 데이터를 처리해야 하는데, 그 연습 데이터를 미리 만들어주는 역할입니다.

### 오염 유형 정의
```python
STRUCTURED_CORRUPTIONS = [
    "missing_field", "null_required", "wrong_type", "invalid_timestamp",
    "numeric_outlier", "invalid_enum", "negative_latency",
]
```
필드 삭제, 필수값 null화, 잘못된 타입, 깨진 타임스탬프, 극단값, 허용 안 된 enum 값, 음수 지연시간 — 실제로 파이프라인에서 자주 마주치는 오류 유형들을 목록화한 것입니다.

### 라벨 붙이기
```python
def _mark(event: dict[str, Any], corruption_type: str, include_label: bool) -> None:
    if include_label:
        event["_simulation"] = {"is_corrupted": True, "corruption_type": corruption_type}
```
- `include_label`이 켜져 있으면 "이 로그는 어떤 유형으로 오염시킨 것"인지 이벤트 안에 표시를 남깁니다. 실습 난이도를 조절하는 옵션 — 라벨을 켜두면 "정답"을 알고 파이프라인 검증을 하기 쉽고, 꺼두면 실제 운영 환경처럼 어떤 게 이상 데이터인지 스스로 찾아내야 합니다.

### 구조적 오염 적용
```python
def corrupt_structured(event: dict[str, Any], corruption_type: str, include_label: bool) -> dict[str, Any]:
    result = copy.deepcopy(event)

    if corruption_type == "missing_field":
        candidates = [
            (result, "event_id"),
            (result, "occurred_at"),
            (result.get("response", {}), "status_code"),
            (result.get("data", {}), next(iter(result.get("data", {"x": 1})), "x")),
        ]
        parent, key = random.choice(candidates)
        parent.pop(key, None)
    elif corruption_type == "null_required":
        target = random.choice(["event_type", "domain", "occurred_at"])
        result[target] = None
    elif corruption_type == "wrong_type":
        result.setdefault("response", {})["latency_ms"] = random.choice(["fast", "120ms", [120]])
    ...
```
- `copy.deepcopy(event)`로 원본을 건드리지 않고 복사본에만 손을 댑니다(원본 `event`는 `main.py`에서 "다음 duplicate 오염용 재료"로 재사용되기 때문에 훼손되면 안 됩니다).
- `missing_field`는 지울 후보 `(부모 딕셔너리, 키)` 쌍을 몇 개 만들어두고 그 중 하나를 무작위로 골라 `pop`으로 삭제합니다. 최상위 필드뿐 아니라 `response.status_code`, `data`의 임의 키까지 후보에 넣어서 "어디가 망가질지 예측 불가능하게" 만든 것이 포인트입니다.
- `elif` 체인으로 오염 유형별 처리를 나열합니다. `numeric_outlier`, `invalid_enum`은 도메인(`smartfactory`/`finance`/`ecommerce`/그 외)에 따라 망가뜨리는 필드가 다르게 분기되어 있어서, 도메인 지식에 맞는 이상치를 만들어냅니다.

### 오염 여부 결정과 특수 오염(중복/JSON 깨짐)
```python
def maybe_corrupt(
    event: dict[str, Any],
    *,
    corruption_rate: float,
    include_label: bool,
    previous_event: dict[str, Any] | None,
) -> tuple[dict[str, Any], str | None, bool]:
    if random.random() >= corruption_rate:
        return event, None, False

    available = STRUCTURED_CORRUPTIONS + ["malformed_json"]
    if previous_event is not None:
        available.append("duplicate")

    corruption_type = random.choice(available)

    if corruption_type == "duplicate":
        duplicate = copy.deepcopy(previous_event)
        _mark(duplicate, "duplicate", include_label)
        return duplicate, "duplicate", False

    if corruption_type == "malformed_json":
        marked = copy.deepcopy(event)
        _mark(marked, "malformed_json", include_label)
        return marked, "malformed_json", True

    return (corrupt_structured(event, corruption_type, include_label), corruption_type, False)
```
- `main.py`는 매 이벤트마다 이 함수 하나만 호출합니다. `corruption_rate`(예: 0.03 = 3%) 확률로만 오염이 일어나고, 그 외엔 원본 그대로(`event, None, False`) 돌려줍니다.
- `duplicate`(직전 이벤트를 그대로 다시 내보내는 것)는 **구조를 망가뜨리지 않고도** 만들 수 있는 오염이라 별도로 처리합니다. 그래서 `previous_event`가 있을 때만 후보에 들어갑니다.
- `malformed_json`은 딕셔너리 구조는 멀쩡하지만, 이 함수는 세 번째 반환값(`malformed_json_flag`)만 `True`로 표시해두고 실제로 JSON을 깨뜨리는 작업은 `output.py`에 맡깁니다(관심사 분리: "무엇을 오염시킬지 결정"과 "실제로 문자열을 자르는 방법"을 나눔).
- 반환 타입이 `tuple[dict, str | None, bool]`인 이유: `main.py`가 세 정보(최종 이벤트, 오염 유형, JSON을 깨야 하는지)를 한 번에 받아야 하기 때문입니다.

---

## 6. `output.py` — JSONL로 출력하기

### 이 파일이 하는 일
완성된 이벤트 딕셔너리를 JSON 문자열로 바꿔서 stdout이나 파일(또는 둘 다)에 한 줄씩(JSONL) 씁니다.

```python
class JsonlOutput:
    def __init__(self, mode: str, log_file: str):
        self.mode = mode
        self.log_file = log_file
        self._handle: TextIO | None = None

        if mode in {"file", "both"}:
            path = Path(log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = path.open("a", encoding="utf-8", buffering=1)
```
- `mode`가 `"file"`이나 `"both"`일 때만 실제 파일을 엽니다(`"stdout"` 모드면 파일 핸들을 아예 만들지 않아 불필요한 파일 I/O를 피합니다).
- `path.parent.mkdir(parents=True, exist_ok=True)`로 로그 파일이 위치할 상위 디렉토리가 없으면 자동으로 만듭니다.
- `open(..., "a", ...)`: 이어쓰기(append) 모드라 재실행해도 기존 로그를 덮어쓰지 않습니다. `buffering=1`은 줄 단위 버퍼링 — 한 줄 쓸 때마다 바로 디스크에 반영되어, 프로그램이 중간에 죽어도 이미 쓴 로그는 보존됩니다.

```python
def emit(self, event: dict, malformed_json: bool = False) -> None:
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))

    if malformed_json:
        cut = max(1, len(line) - max(1, min(12, len(line) // 10)))
        line = line[:cut]

    if self.mode in {"stdout", "both"}:
        print(line, flush=True)
    if self._handle is not None:
        self._handle.write(line + os.linesep)
```
- `json.dumps(..., ensure_ascii=False, separators=(",", ":"))`: 한글이 유니코드 이스케이프(`\uXXXX`)로 깨지지 않게(`ensure_ascii=False`) 하고, 공백 없이 압축된 JSON(`separators`)으로 한 줄에 담습니다 — 이게 "JSONL(JSON Lines)" 포맷의 기본입니다.
- `malformed_json=True`면 `corruption.py`가 표시만 해둔 걸 여기서 실제로 실행합니다: 문자열 뒤쪽 일부(전체 길이의 최대 10%, 1~12자)를 그냥 잘라서 파싱 불가능한 JSON을 만듭니다. "왜 자르기만 해도 깨지나?" — JSON은 중괄호/따옴표가 정확히 닫혀야 하는데, 끝부분을 잘라버리면 괄호가 안 닫힌 상태가 되어 파서가 실패하기 때문입니다.
- `flush=True`로 매번 즉시 출력 버퍼를 비워서, 컨테이너 로그 수집기(CloudWatch 등)가 실시간으로 로그를 긁어갈 수 있게 합니다.

```python
def close(self) -> None:
    if self._handle is not None:
        self._handle.close()
```
파일이 열려있을 때만 닫습니다. `main.py`가 `try/finally`로 정상 종료든 예외든 항상 이 메서드를 호출하도록 되어 있습니다.

---

## 7. `main.py` — 전체 조립(오케스트레이션)

### 실행 진입점
```python
if __name__ == "__main__":
    raise SystemExit(run())
```
- 파이썬 파일이 "직접 실행됐을 때만"(다른 파일에서 `import`된 게 아니라) `run()`을 호출하는 관용구입니다.
- `run()`의 반환값(정수)을 `SystemExit`에 넘기면 그게 그대로 프로세스 종료 코드가 됩니다(`echo $?`로 확인 가능). `0`은 정상, `2`는 설정 오류로 구분해뒀습니다.

### 도메인 매핑
```python
Generator = Callable[..., dict]
GENERATORS: dict[str, Generator] = {
    "ecommerce": ecommerce.generate,
    "finance": finance.generate,
    "smartfactory": smartfactory.generate,
    "game": game.generate,
}
```
- `Callable[..., dict]`는 "인자가 뭐든 상관없이, `dict`를 반환하는 함수"라는 타입입니다. 4개 도메인의 `generate` 함수 시그니처가 다 똑같기 때문에 이렇게 하나의 타입으로 묶을 수 있습니다.
- 문자열(도메인 이름) → 함수를 매핑해두면, `if/elif`로 도메인을 분기하지 않고 `GENERATORS[settings.domain]` 한 줄로 원하는 함수를 꺼낼 수 있습니다. **딕셔너리를 스위치문 대신 쓰는 전형적인 패턴**입니다.

### 종료 시그널 처리
```python
STOP_REQUESTED = False

def _handle_stop(signum, frame) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
...
signal.signal(signal.SIGTERM, _handle_stop)
signal.signal(signal.SIGINT, _handle_stop)
```
- ECS/Docker가 컨테이너를 멈출 때 보통 `SIGTERM`을 보내고, 터미널에서 `Ctrl+C`를 누르면 `SIGINT`가 옵니다. 이 신호가 오면 프로그램을 그 자리에서 강제 종료하는 대신 전역 플래그(`STOP_REQUESTED`)만 켜두고, 메인 루프가 다음 반복 시작 시점에 스스로 멈추게 합니다 — "안전한 종료(graceful shutdown)"를 위한 패턴입니다. 그래야 파일 핸들을 제대로 닫고 끝낼 수 있습니다.
- `global STOP_REQUESTED`: 함수 안에서 모듈 최상단의 전역 변수를 수정하겠다고 명시하는 선언입니다.

### `run()` 함수 흐름
```python
def run() -> int:
    try:
        settings = Settings.from_env()
    except Exception as exc:
        print(f"[configuration-error] {exc}", file=sys.stderr)
        return 2

    if settings.seed is not None:
        random.seed(settings.seed)
        Faker.seed(settings.seed)

    fake = Faker(settings.faker_locale)
    generator = GENERATORS[settings.domain]
    traffic = TrafficController(domain=settings.domain, base_rps=settings.base_rps,
                                 timezone=settings.timezone, time_scale=settings.time_scale)
    output = JsonlOutput(settings.output_mode, settings.log_file)

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    started = time.monotonic()
    emitted = 0
    previous_event: dict | None = None
```
- 설정 로드 실패는 `try/except`로 잡아서 사용자에게 원인을 알려주고 **조기 종료**(fail fast)시킵니다.
- `settings.seed`가 있으면 `random`과 `Faker`의 난수 시드를 동일하게 고정합니다 — 같은 시드면 매번 완전히 똑같은 로그가 재현되어, 디버깅이나 테스트에 유용합니다.
- `time.monotonic()`은 시스템 시계(사용자가 시간을 바꾸거나 NTP 보정이 일어나도 영향받지 않는) 기준으로 흐르는 시간을 잽니다. 실행 시간 측정처럼 "얼마나 지났는지"를 잴 때는 `datetime.now()`보다 이게 안전합니다.

```python
    try:
        while not STOP_REQUESTED:
            elapsed = time.monotonic() - started
            if settings.duration_seconds > 0 and elapsed >= settings.duration_seconds:
                break
            if settings.max_events > 0 and emitted >= settings.max_events:
                break

            event = generator(fake, timezone_name=settings.timezone,
                               environment=settings.environment, run_id=settings.run_id)

            event_to_emit, _, malformed = maybe_corrupt(
                event, corruption_rate=settings.corruption_rate,
                include_label=settings.include_corruption_label, previous_event=previous_event)

            output.emit(event_to_emit, malformed_json=malformed)

            previous_event = event
            emitted += 1
            time.sleep(traffic.next_sleep_seconds())
    finally:
        output.close()

    return 0
```
- 반복문 종료 조건이 세 가지입니다: ① 종료 신호(`STOP_REQUESTED`), ② 지정한 실행 시간 초과, ③ 지정한 최대 이벤트 수 도달. `duration_seconds`나 `max_events`가 `0`이면 그 조건은 무시(무제한)됩니다.
- 매 반복의 순서가 앞서 설명한 4단계와 정확히 일치합니다: `generator(...)`로 생성 → `maybe_corrupt(...)`로 오염 처리 → `output.emit(...)`으로 출력 → `time.sleep(...)`으로 대기.
- `previous_event = event`는 **오염되지 않은 원본**을 저장해둡니다(오염된 `event_to_emit`이 아니라). 그래야 다음 반복에서 `duplicate` 오염이 필요할 때 "정상적인" 이벤트를 복제하지, 이미 망가진 이벤트를 또 복제하는 일이 없습니다.
- `try/finally`: 반복문이 정상 종료(break)되든, 처리 중 예외가 나든, **항상** `output.close()`가 실행되도록 보장합니다. 파일 핸들을 안전하게 닫기 위한 필수 패턴입니다.

---

## 정리: 다음 프로젝트에 가져다 쓰기 좋은 패턴 5가지

1. **환경변수 → 하나의 불변 설정 객체** (`config.py`의 `Settings.from_env()`): 설정 읽기/검증을 한 곳에 몰아넣고, 나머지 코드는 검증된 객체만 믿고 쓴다.
2. **공통 스키마와 도메인 로직 분리** (`common.py`의 `make_base_event`): "공통 봉투"와 "도메인별 내용물"을 분리하면 새 도메인을 추가할 때 공통 부분을 다시 짤 필요가 없다.
3. **딕셔너리를 라우팅 테이블처럼 쓰기** (`GENERATORS`, `routes`): `if/elif`를 반복하는 대신 이름→값(또는 함수)의 매핑으로 관리하면 코드가 짧아지고 확장하기 쉽다.
4. **상태를 객체에 저장해 여러 호출에 걸친 효과 만들기** (`TrafficController`의 버스트 로직): 한 번의 확률 판정 결과를 인스턴스 변수에 저장해두고 이후 호출에서 소비하는 패턴.
5. **`try/finally`로 자원 정리 보장** (`output.close()`): 정상/예외 종료 모두에서 파일 핸들 같은 자원이 새지 않게 한다.
