# 생성된 이벤트를 JSONL 형식으로 stdout 또는 파일에 출력

# 타입 힌트 평가를 지연해 최신 타입 문법을 안정적으로 사용
from __future__ import annotations

# Python 딕셔너리를 JSON 문자열로 직렬화
import json
# 환경변수와 OS 개행 문자 사용
import os
# 로그 파일 경로와 디렉터리를 안전하게 처리
from pathlib import Path
# 파일 핸들의 타입을 명확하게 지정
from typing import TextIO


# JSONL 형식의 stdout/파일 출력을 담당하는 클래스
class JsonlOutput:
    # 출력 방식과 로그 파일 경로를 초기화
    def __init__(self, mode: str, log_file: str):
        # stdout/file/both 중 선택한 출력 모드 저장
        self.mode = mode
        # 파일 출력 시 사용할 경로 저장
        self.log_file = log_file
        # 아직 열리지 않은 파일 핸들을 None으로 초기화
        self._handle: TextIO | None = None

        # 파일 출력이 필요한 모드일 때만 파일을 준비
        if mode in {"file", "both"}:
            # 문자열 파일 경로를 Path 객체로 변환
            path = Path(log_file)
            # 상위 디렉터리가 없으면 자동으로 생성
            path.parent.mkdir(parents=True, exist_ok=True)
            # 기존 파일 뒤에 UTF-8 라인 버퍼링 방식으로 이어쓰기
            self._handle = path.open("a", encoding="utf-8", buffering=1)

    # 이벤트 한 건을 JSON 문자열로 변환해 지정된 출력 대상으로 전송
    def emit(self, event: dict, malformed_json: bool = False) -> None:
        # 이벤트를 한 줄짜리 compact JSON 문자열로 직렬화
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))

        # 깨진 JSON 실습 레코드라면 문자열 일부를 잘라냄
        if malformed_json:
            # Intentionally break the line so parsers must handle bad records.
            # JSON 끝에서 제거할 위치를 계산
            cut = max(1, len(line) - max(1, min(12, len(line) // 10)))
            # JSON을 의도적으로 잘라 파싱 불가능한 레코드 생성
            line = line[:cut]

        # stdout 출력 모드가 포함되면 콘솔로 로그 출력
        if self.mode in {"stdout", "both"}:
            # stdout에 즉시 출력해 컨테이너 로그로 전달
            print(line, flush=True)
        # 파일이 실제로 열려 있을 때만 파일 작업 수행
        if self._handle is not None:
            # 파일 출력 모드에서는 이벤트 한 건을 한 줄로 기록
            self._handle.write(line + os.linesep)

    # 열려 있는 로그 파일 핸들을 안전하게 닫음
    def close(self) -> None:
        # 파일이 실제로 열려 있을 때만 파일 작업 수행
        if self._handle is not None:
            # 열려 있는 파일 자원을 닫아 버퍼를 반영
            self._handle.close()