# 프로그램 진입(엔트리 포인트)


def run() -> int:

  # 정상 실행 종료 표시
  return 0

if __name__ == '__main__':
  # run() 반환값을 프로세스 종료 코드로 활용
  raise SystemExit( run() )