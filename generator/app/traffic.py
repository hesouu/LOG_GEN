# 도메인·시간대·요일·버스트를 반영해 현실적인 이벤트 발생 속도를 계산

# 타입 힌트 평가를 지연해 최신 타입 문법을 안정적으로 사용
from __future__ import annotations

# 이벤트 종류·값·상태 등을 확률적으로 생성
import random
# 현재 시간과 시간대별 트래픽 계산에 사용
from datetime import datetime
# Asia/Seoul 같은 IANA 시간대 적용
# 시간대 문자열을 실제 시간대 객체로 변환
from zoneinfo import ZoneInfo


# Hour-of-day multipliers. 1.0 means BASE_RPS.
# 도메인별 24시간 트래픽 가중치 정의
HOURLY_PROFILE = {
    # 24개 트래픽 가중치 사전 정의
    "ecommerce": [
        0.25, 0.20, 0.18, 0.16, 0.18, 0.25,
        0.45, 0.70, 0.85, 0.95, 1.05, 1.20,
        1.35, 1.20, 1.05, 1.00, 1.10, 1.30,
        1.55, 1.80, 1.95, 1.85, 1.25, 0.65,
    ],
    "finance": [
        0.20, 0.16, 0.14, 0.13, 0.15, 0.22,
        0.38, 0.65, 1.10, 1.55, 1.45, 1.35,
        1.25, 1.30, 1.45, 1.50, 1.35, 1.10,
        0.90, 0.75, 0.62, 0.50, 0.38, 0.28,
    ],
    "smartfactory": [
        0.95, 0.95, 0.95, 0.95, 0.90, 0.85,
        0.80, 1.00, 1.05, 1.05, 1.05, 1.00,
        0.90, 1.00, 1.05, 1.05, 1.00, 0.90,
        0.85, 1.00, 1.05, 1.05, 1.00, 0.95,
    ],
    "game": [
        0.45, 0.30, 0.22, 0.18, 0.16, 0.18,
        0.25, 0.35, 0.45, 0.50, 0.55, 0.60,
        0.70, 0.75, 0.78, 0.82, 0.95, 1.20,
        1.55, 1.90, 2.15, 2.25, 1.80, 1.10,
    ],
}


# 현실적인 이벤트 발생 간격을 계산하는 트래픽 제어 클래스
class TrafficController:
    """Create Poisson-like event intervals with time-of-day/week and burst effects."""

    # 도메인·기본 RPS·시간대·속도 배율을 초기화
    def __init__(self, domain: str, base_rps: float, timezone: str, time_scale: float = 1.0):
        # 트래픽 패턴을 선택할 도메인 저장
        self.domain = domain
        # 기본 초당 이벤트 발생량 저장
        self.base_rps = base_rps
        # 시간대 문자열을 실제 시간대 객체로 변환
        self.tz = ZoneInfo(timezone)
        # 이벤트 간격 가속/감속 배율 저장
        self.time_scale = time_scale

        # 두 값은 갑자기 트래픽이 몰리는 버스트(burst) 상황을 시뮬레이션하기 위한 상태값
        # 현재 버스트 상태에서 남은 이벤트 수 초기화, 버스트를 얼마나 오래 유지할지
        self._burst_events_left = 0     # 현재 버스트로 처리할 남은 이벤트가 없음
        # 현재 버스트 트래픽 배율 초기화, 버스트 동안 트래픽을 몇 배로 늘릴지
        self._burst_multiplier = 1.0    # 트래픽 증가 없음

        # 만약 
        # _burst_events_left = 20
        # _burst_multiplier = 3.5
        # 해석 : 앞으로 약 20개의 이벤트 동안 트래픽을 평소보다 3.5배 증가시킨다.
        # 이벤트가 하나 생성될 때마다 => self._burst_events_left -= 1 => 20 → 19 → 18 → ... → 1 → 0 => 0이 되면 버스트가 끝남

    # 현재 시간과 요일을 기준으로 도메인별 트래픽 배율 계산
    def _calendar_multiplier(self, now: datetime) -> float:
        # 현재 시간대에 해당하는 도메인별 가중치 선택
        hourly = HOURLY_PROFILE[self.domain][now.hour]
        weekday = now.weekday()  # Mon=0

        # 특정 도메인일 때 요일 특성에 맞는 배율 적용
        if self.domain == "finance" and weekday >= 5:
            # 주말 금융 트래픽을 평일 대비 55% 수준으로 낮춤
            return hourly * 0.55
        # 특정 도메인일 때 요일 특성에 맞는 배율 적용
        if self.domain == "smartfactory" and weekday >= 5:
            # 주말 공장 트래픽을 평일 대비 72% 수준으로 낮춤
            return hourly * 0.72
        # 특정 도메인일 때 요일 특성에 맞는 배율 적용
        if self.domain == "ecommerce" and weekday >= 5:
            # 주말 이커머스 트래픽을 약 18% 증가시킴
            return hourly * 1.18
        # 특정 도메인일 때 요일 특성에 맞는 배율 적용
        if self.domain == "game" and weekday >= 5:
            # 주말 게임 트래픽을 약 35% 증가시킴
            return hourly * 1.35
        # 주말 보정 대상이 아니면 시간대 배율만 사용
        return hourly

    # 짧은 시간 동안 트래픽이 급증하는 버스트 효과 계산
    def _burst_factor(self) -> float:
        if self._burst_events_left > 0:
            # 버스트 상태에서 이벤트 한 건을 소비
            self._burst_events_left -= 1
            return self._burst_multiplier

        # Short, occasional bursts emulate campaigns, market-open spikes,
        # equipment alarm storms, or game-event traffic.
        # 약 0.4% 확률로 짧은 트래픽 급증 시작
        if random.random() < 0.004:
            # 버스트가 지속될 이벤트 개수를 무작위 결정
            self._burst_events_left = random.randint(8, 35)
            # 버스트 동안 RPS를 2~5배 증가
            self._burst_multiplier = random.uniform(2.0, 5.0)
            return self._burst_multiplier

        return 1.0

    # 현재 시점의 최종 초당 이벤트 수(RPS) 계산
    def current_rps(self) -> float:
        # 설정된 시간대의 현재 시각 조회
        now = datetime.now(self.tz)
        # 시간대와 요일에 따른 트래픽 배율 계산
        calendar = self._calendar_multiplier(now)
        # 일정하지 않은 실제 트래픽처럼 ±15% 랜덤 변동 추가
        jitter = random.uniform(0.85, 1.15)
        # 이벤트성 순간 트래픽 증가 배율 계산
        burst = self._burst_factor()
        # 최종 RPS를 계산하되 최소값 0.02 보장
        return max(0.02, self.base_rps * calendar * jitter * burst)

    # 다음 이벤트까지 기다릴 시간을 확률적으로 계산
    # 다음 로그를 몇 초 뒤에 생성할지”를 결정하는 코드
    # 핵심은 일정한 간격으로 로그를 만들지 않고, 실제 트래픽처럼 랜덤한 간격으로 생성하는 것
    def next_sleep_seconds(self) -> float:
        # Exponential inter-arrival time approximates a Poisson arrival process.
        # 포아송 도착과 유사하도록 지수분포 기반 이벤트 간격 계산
        # 일정한 평균 발생률을 가진 랜덤 이벤트가 발생하는 상황을 포아송 프로세스로 모델링할 수 있고, 그 이벤트들 사이의 시간 간격은 지수분포를 따릅니다.
        # self.current_rps() — 현재 초당 이벤트 수 계산
        # random.expovariate() — 다음 이벤트까지 기다릴 시간
        # 지수분포(Exponential Distribution)를 이용해 다음 이벤트까지의 시간 간격을 랜덤하게 생성
        # random.expovariate(2.0) => 1 / λ => 1 / 2 => 0.5초 => 평균 대기시간
        # RPS와 평균 대기시간은 반비례 : RPS가 커질수록, 대기시간은 짦아짐
        interval = random.expovariate(self.current_rps())
        # TIME_SCALE=10 shortens event wait intervals by 10x for demonstrations.
        # Timestamps still use the real clock; only the generation pace is accelerated.
        # 시간배율을 적용하고 최대 대기시간을 10초로 제한
        return min(interval / self.time_scale, 10.0)