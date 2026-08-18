from python:3.12-slim

#  PYTHONDONTWRITEBYTECODE : .pyc 캐시파일 생성 방지
#  PYTHONUNBUFFERED : 파이썬에는 로그 출력시 버퍼링 하지 않고 즉시 출력
#  버퍼링 하면 로그가 발생되고 기록될때 왜곡이 됨
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스카피
copy app ./app

# 컨테이너 실행되면 구동할 명령어
entrypoint [ "python", "-m", "app.main"]