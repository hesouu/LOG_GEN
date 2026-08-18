# 프로그램 진입(엔트리 포인트)
from domains import ecommerce
from faker import Faker

fake = Faker("ko-KR") # ko_OR는 환경변수에서 획득

def run() -> int:
  log = ecommerce.generate(fake, timezone_name="", environment="", run_id="")
  print( log )
  # 정상 실행 종료 표시
  return 0

if __name__ == '__main__':
  # run() 반환값을 프로세스 종료 코드로 활용
  raise SystemExit( run() )