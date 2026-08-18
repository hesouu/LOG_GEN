# 설정 로드 → 도메인 로그 생성 → 오염 처리 → 출력 → 속도 제어를 수행하는 메인 실행 파일

# 타입 힌트 평가를 지연해 최신 타입 문법을 안정적으로 사용
from __future__ import annotations

# 이벤트 종류·값·상태 등을 확률적으로 생성
import random
# SIGTERM/SIGINT 종료 신호를 받아 안전하게 종료
import signal
# 표준 오류 출력과 프로세스 종료 처리에 사용
import sys
# 실행시간 측정과 이벤트 발생 간격 대기에 사용
import time
# 도메인별 로그 생성 함수의 타입 정의
from collections.abc import Callable

# 이름·IP 등 현실적인 가짜 데이터 생성
from faker import Faker

# 환경변수 기반 실행 설정 클래스 가져오기
from app.config import Settings
# 일정 확률로 로그를 오염시키는 함수 가져오기
from app.corruption import maybe_corrupt
# 4개 도메인의 실제 로그 생성 모듈을 가져오기
from app.domains import ecommerce, finance, game, smartfactory
# 생성 로그를 JSONL로 출력하는 클래스 가져오기
from app.output import JsonlOutput
# 로그 발생 속도를 제어하는 클래스 가져오기
from app.traffic import TrafficController


# 도메인별 generate 함수가 반환할 형태를 타입으로 정의
# Callable → 호출 가능한 것, 주로 함수
# ... → 매개변수 형태는 제한하지 않음
# dict → 반환값은 딕셔너리
# Generator라는 이름으로 매개변수 상관없이 “dict를 반환하는 함수 타입”을 정의한 코드
Generator = Callable[..., dict]
# 도메인 이름과 실제 로그 생성 함수를 연결하는 매핑 => 키과 함수(그런 유형의)를 매칭하는 딕셔너리 구성
GENERATORS: dict[str, Generator] = {
    "ecommerce": ecommerce.generate,
    "finance": finance.generate,
    "smartfactory": smartfactory.generate,
    "game": game.generate,
}

# 종료 신호 수신 여부를 저장하는 전역 플래그
STOP_REQUESTED = False


# 종료 신호가 오면 메인 반복문이 멈추도록 플래그 변경
def _handle_stop(signum, frame) -> None:  # noqa: ANN001
    # 함수 내부에서 전역 종료 플래그를 수정하도록 선언
    global STOP_REQUESTED
    # 반복문이 다음 순회에서 종료되도록 플래그 설정
    STOP_REQUESTED = True


# 로그 생성기의 전체 실행 흐름을 담당
def run() -> int:
    # 1. 환경 변수 획득
    try:
        # 환경변수에서 실행 설정을 읽고 검증
        settings = Settings.from_env()
    except Exception as exc:
        # 잘못된 설정 내용을 표준 오류로 출력
        print(f"[configuration-error] {exc}", file=sys.stderr)
        # 설정 오류를 의미하는 종료 코드 2 반환
        return 2

    # 2. 난수 시드 설정
    if settings.seed is not None:
        # Python random의 난수 시드를 고정
        random.seed(settings.seed)
        # Faker 데이터 생성 결과도 동일하게 재현되도록 시드 고정
        Faker.seed(settings.seed)

    # 3. 지정한 locale로 Faker 인스턴스 생성. 지역별 설정
    fake = Faker(settings.faker_locale)
    
    # 4. 선택한 도메인에 해당하는 generate 함수 선택
    generator = GENERATORS[settings.domain]

    # 5. 도메인·시간대·RPS를 기준으로 이벤트 발생 속도 제어기 생성
    traffic = TrafficController(
        domain      =settings.domain,       # 도메인
        base_rps    =settings.base_rps,     # 기본 초당 이벤트 생성량(RPS)을 읽음
        timezone    =settings.timezone,     # 타임존
        time_scale  =settings.time_scale,   # 이벤트 생성 속도 배율을 읽음
    )

    # 6. stdout/file/both 설정에 맞는 출력기 생성
    output = JsonlOutput(settings.output_mode, settings.log_file)

    # 7. ECS 종료 시 주로 전달되는 SIGTERM 신호 처리 함수 등록
    signal.signal(signal.SIGTERM, _handle_stop)

    # 8. Ctrl+C(SIGINT) 종료 신호 처리 함수 등록
    signal.signal(signal.SIGINT, _handle_stop)

    # 9. 시스템 시계 변경의 영향을 받지 않는 실행시간 측정 시작
    started = time.monotonic()

    # 10, 지금까지 출력한 이벤트 개수를 0으로 초기화
    emitted = 0
    
    # 11. 중복 오염 생성에 사용할 직전 정상 이벤트 보관 변수
    previous_event: dict | None = None

    try:
        # 종료 요청이 들어올 때까지 이벤트 생성 반복
        while not STOP_REQUESTED:
            # 실행 시작 후 경과 시간을 계산
            elapsed = time.monotonic() - started
            # 수행시간이 이벤트 발생 시간(설정한)을 초과하면 종료
            if settings.duration_seconds > 0 and elapsed >= settings.duration_seconds:
                # 종료 조건을 만족하면 이벤트 생성 반복문 종료
                break
            # 현재 발생된 이벤트 수가 최대 이벤트 수 이상하면 종료
            if settings.max_events > 0 and emitted >= settings.max_events:
                # 종료 조건을 만족하면 이벤트 생성 반복문 종료
                break

            # 선택된 도메인의 generate 함수로 정상 이벤트 한 건 생성
            # 이벤트 생성
            event = generator(
                fake,
                timezone_name   =settings.timezone,
                environment     =settings.environment,
                run_id          =settings.run_id,
            )

            # 정상 이벤트를 설정된 확률에 따라 오염 처리
            event_to_emit, _, malformed = maybe_corrupt(
                event,
                corruption_rate =settings.corruption_rate,
                include_label   =settings.include_corruption_label,
                previous_event  =previous_event,
            )

            # 최종 이벤트를 JSONL 형식으로 출력
            output.emit(event_to_emit, malformed_json=malformed)

            # Store the clean event as the source for a future duplicate.
            # 다음 이벤트에서 duplicate 오염을 만들 수 있도록 정상 이벤트 저장
            previous_event = event
            
            # 출력 이벤트 개수를 1 증가
            emitted += 1

            # 계산된 이벤트 간격만큼 대기해 트래픽 속도 조절
            time.sleep(traffic.next_sleep_seconds())
    finally:
        # 정상·예외 종료 모두에서 파일 출력 핸들을 닫음
        output.close()

    # 정상 실행 완료를 의미하는 종료 코드 0 반환
    return 0


# 이 파일을 직접 실행했을 때만 run() 호출
if __name__ == "__main__":
    # run() 반환값을 프로세스 종료 코드로 사용
    raise SystemExit(run())