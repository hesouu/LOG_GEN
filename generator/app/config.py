# 환경변수를 읽어 로그 생성기의 실행 설정을 만들고 값의 유효성을 검증

# 타입 힌트 평가를 지연해 최신 타입 문법을 안정적으로 사용
from __future__ import annotations

# 환경변수와 OS 개행 문자 사용
import os
# 실행 설정값을 구조화된 객체로 관리
from dataclasses import dataclass

# 실행 가능한 도메인 이름을 제한
VALID_DOMAINS = {"ecommerce", "finance", "smartfactory", "game"}
# 허용할 로그 출력 방식 정의
VALID_OUTPUT_MODES = {"stdout", "file", "both"}


# 문자열 환경변수를 읽고 공백을 제거
def _env(name: str, default: str) -> str:
    # 환경변수가 없으면 기본값을 사용하고 양쪽 공백 제거
    return os.getenv(name, default).strip()


# 환경변수를 정수로 변환해 반환
def _env_int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


# 환경변수를 실수로 변환해 반환
def _env_float(name: str, default: float) -> float:
    return float(_env(name, str(default)))


# 여러 형태의 문자열 환경변수를 Boolean 값으로 변환
def _env_bool(name: str, default: bool) -> bool:
    # Boolean 환경변수를 소문자 문자열로 정규화
    raw = _env(name, "true" if default else "false").lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


# 생성 후 설정값이 변경되지 않도록 불변 데이터클래스로 선언
@dataclass(frozen=True)
# 로그 생성기 전체 실행 옵션을 보관하는 불변 설정 클래스
class Settings:
    domain: str
    duration_seconds: int
    max_events: int
    base_rps: float
    time_scale: float
    corruption_rate: float
    include_corruption_label: bool
    output_mode: str
    log_file: str
    timezone: str
    faker_locale: str
    environment: str
    run_id: str
    seed: int | None

    # 인스턴스 없이 Settings.from_env() 형태로 호출 가능하게 선언
    @classmethod
    # cls : @classmethod로 정의 => Python이 자동으로 전달하는 클래스 자신을 의미  => Settings 클레스를 의미
    # 환경변수를 읽어 검증한 뒤 Settings 객체 생성
    def from_env(cls) -> "Settings":
        # 1. 실행할 도메인을 읽고 기본값을 ecommerce로 설정
        domain = _env("DOMAIN", "ecommerce").lower()
        # 지원하지 않는 도메인이면 즉시 설정 오류 처리
        if domain not in VALID_DOMAINS:
            raise ValueError(f"DOMAIN must be one of: {', '.join(sorted(VALID_DOMAINS))}")

        # 2. 실행 지속시간을 초 단위로 읽음
        duration_seconds = _env_int("DURATION_SECONDS", 300)
        # 실행 시간이 음수인지 검증
        if duration_seconds < 0:
            raise ValueError("DURATION_SECONDS must be >= 0")
        # 시간과 개수 제한이 모두 없어서 무한 실행되는 설정을 차단
        if duration_seconds == 0 and max_events == 0:
            raise ValueError("Set DURATION_SECONDS > 0 or MAX_EVENTS > 0 to bound the run")

        # 3. 최대 이벤트 수를 읽으며 0은 개수 제한을 사용하지 않음
        max_events = _env_int("MAX_EVENTS", 0)
        # 최대 이벤트 수가 음수인지 검증
        if max_events < 0:
            raise ValueError("MAX_EVENTS must be >= 0")

        # 4. 기본 초당 이벤트 생성량(RPS)을 읽음
        base_rps = _env_float("BASE_RPS", 2.0)
        # RPS가 0 이하가 되지 않도록 검증
        if base_rps <= 0:
            raise ValueError("BASE_RPS must be > 0")
    
        # 5. 데모용 이벤트 생성 속도 배율을 읽음
        time_scale = _env_float("TIME_SCALE", 1.0)
        # 시간 배율이 0 이하가 되지 않도록 검증
        if time_scale <= 0:
            raise ValueError("TIME_SCALE must be > 0")
        
        # 6. 오염 데이터를 생성할 확률을 읽음
        corruption_rate = _env_float("CORRUPTION_RATE", 0.03)
        # 오염률이 0~1 범위인지 검증
        if not 0.0 <= corruption_rate <= 1.0:
            raise ValueError("CORRUPTION_RATE must be between 0.0 and 1.0")

        # 7. 로그 출력 방식을 읽고 기본값을 stdout으로 설정
        output_mode = _env("OUTPUT_MODE", "stdout").lower()
        # 허용되지 않은 출력 모드이면 설정 오류 처리
        if output_mode not in VALID_OUTPUT_MODES:
            raise ValueError("OUTPUT_MODE must be stdout, file, or both")

        # 재현 가능한 난수 생성을 위한 선택적 seed 값 읽기
        seed_raw = _env("SEED", "")
        # seed가 있으면 정수로 변환하고 없으면 None 사용
        seed = int(seed_raw) if seed_raw else None

        # 검증이 끝난 환경변수 값으로 Settings 객체 생성 -> 클레스에 인자 넣어서 객체 생성
        return cls(
            domain                          =domain,
            duration_seconds                =duration_seconds,
            max_events                      =max_events,
            base_rps                        =base_rps,
            time_scale                      =time_scale,
            corruption_rate                 =corruption_rate,
            include_corruption_label        =_env_bool("INCLUDE_CORRUPTION_LABEL", False),
            output_mode                     =output_mode,
            # 선택 여지 없이 기본값
            log_file                        =_env("LOG_FILE", "/tmp/generated-logs.jsonl"),
            timezone                        =_env("TIMEZONE", "Asia/Seoul"),
            faker_locale                    =_env("FAKER_LOCALE", "ko_KR"),
            environment                     =_env("ENVIRONMENT", "simulation"),
            run_id                          =_env("RUN_ID", "manual"),
            seed                            =seed,
        )