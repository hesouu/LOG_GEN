# 개요
- main 브런치는 로그를 CloudWatch에 저장하고 있음
  - 애플리케이션 상태/오류/디버깅 용도 => 개발, 유지보수에 연관 => 앱/웹 개발자 관여
- 데이터 엔지니어 관점 새로운 흐름(파이프라인 구성) 필요
  - s3에 바로 저장 (다이렉트 저장)
    - 불필요한 I/O 아주 많이 발생 (빈번한 putObject 행위 발생)
    - 작은 파일이 많이 발생함
  - 방식
    - 해당 데이터는 실시간 스트리밍 수집 -> kinesis 활용
    - 데이터를 모아서(시간단위, 용량단위) 한번에 s3에 저장 -> firehose 활용
    - Streaming Ingestion

  - 향후 
    - kinesis -> flink(대용량,실시간 전처리) / lambda   -> kinesis -> firehose 로 구성하여 sliver 단계 구성 가능

# 구성도
- 기본적 스트리밍 수집
```
                      ┌→ CloudWatch Logs
                      │   운영/디버깅
Fargate Generator ────┤
                      │
                      └→ Kinesis
                           │
                           │
                           ↓
                        Firehose
                           ↓
                           S3 : bronze layer (메달리온 아킥텍처 기반)
                      데이터 파이프라인
```

# 메달리온 아키텍처
- 데이터 레이크(하우스)의 표준 데이터 품질 관리 패턴
- 구성

|단계|의미|뉘앙스|
|--|--|--|
|Bronze|가공되지 않은 기록<br>raw 데이터|무슨 일이 일어났는가?, gzip|
|Silver|전처리, 클리닝등 데이터 정제과정<br>분석 가능한 깔끔한 테이블|누가, 언제, 무엇을 구매했는가?, parquet|
|Gold|보고서에 바로 들어갈 숫자, 분석, 대시보드등<br> 즉시 사용(비즈니스)할 수준의 데이터레벨|이번 시간 매출은 얼마인가?, parquet|


# 수정 및 추가 workflow 
```
[1] Terraform 인프라 생성
       │
       ├─ Kinesis Data Stream
       ├─ S3 Bucket
       ├─ Firehose IAM Role
       └─ Firehose
       │
       ▼
[2] 기존 Fargate IAM 수정
       │
       └─ Task Role + kinesis:PutRecord(s)
       │
       ▼
[3] Python 로그 생성기 수정
       │
       ├─ config.py
       ├─ output.py
       └─ main.py
       │
       ▼
[4] Docker 이미지 재빌드
       │
       ▼
[5] run-generator.bat/shell 수정
       │
       ▼
[6] 실행
       │
       ▼
Fargate → Kinesis → Firehose → S3 확인 (jsonl, gzip)
```

# 인프라 수정 및 추가
- tree /f 명령으로 구성도에서 인프라만 추출
```
# 수정은 표기 않함
├─infra
│  │  ecr.tf            # 유지
│  │  ecs.tf            # 9. 수정
│  │  iam.tf            # 6/8. 수정 (6.firehose 관련, 8.ecs-task에서 kinesis put 처리) 
│  │  locals.tf         # 3. 수정
│  │  logs.tf           # 유지
│  │  outputs.tf        # 10. 수정
│  │  provider.tf       # 1. 수정
│  │  sg.tf             # 유지
│  │  variables.tf      # 2. 수정 
│  │  version.tf        # 유지
│  │  vpc.tf            # 유지
│  │  
│  ├─ kinesis.tf        # 4. 신규
│  ├─ firehose.tf       # 7. 신규
│  ├─ s3.tf             # 5. 신규
```

# 파이썬 검토 (kinesis로 전송 조정)
- 패키지
       ```
       Faker
       boto3  # AWS SDK 패키지
       ```
       - 로컬 PC에 boto3 설치
       ```
              pip install boto3
       ```
- config.py
       - ecs 세팅한 환경변수 전달
- output.py
       - 출력 방향에 kinesis 추가
- main.py
       - 생성자 매개변수 조정



# bat/shell 검토
- 코드 수정 => 이미지 수정 => ecr 업데이트 => setup.bat/sh
```
# setup.bat
docker build --no-cache --platform linux/amd64 -t "%REPO%:latest" "%GENERATOR%"

# setup.sh
docker build --no-cache --platform linux/amd64 -t "$REPO:latest" "$GENERATOR"
```

# 브론즈 데이터 생성
- 명령 옵션
```
ecommerce       도메인
5               5초 실행
5               기본 5 RPS
0.05            오염 데이터 5%
1               Fargate Task 1개
ap-northeast-2  서울 리전
1               Time Scale 1배
```
- 명령
- 25건 로그 생성
- Cloudwatch 로그 기록됨 (stdouT 설정이 기본)
- kinesis -> firehose -> s3 기록됨 (ecs 설정에 환경변수로 세팅되어 있음)
- s3에서 로그 발생후 언제 확인 가능한가? => 약간의 텀 존재함, 1분 이후 혹은 1Mib(firehose 버퍼링 조건) 초과 이후 확인 가능함
```
# 윈도우
scripts/run-generator.bat ecommerce 5 5 0.05 1 ap-northeast-2 1

# linux,mac
scripts/ ./run-generator.sh ecommerce 5 5 0.05 1 ap-northeast-2 1

```
-----------------------------------------------------------------------------------------------------------
|                                                 RunTask                                                 |
+---------------------------------------------------------------------------------------------------------+
|  arn:aws:ecs:ap-northeast-2:827913617635:task/de-ai-09-loggen-cluster/0a1923b7d479498cb8b51619f44db323  |
+---------------------------------------------------------------------------------------------------------+
Run ID: loggen-20260820-145055
Follow logs: aws logs tail '/ecs/de-ai-09-loggen' --follow --region 'ap-northeast-2'
```

- 실시간 로그 확인
```
aws logs tail "/ecs/de-ai-09-loggen" --follow --region "ap-northeast-2"
---
{"schema_version":"1.0","record_type":"application_log","event_id"......}
```

# jsonl => GZIP 변경하여 저장 (실습)
- 동일 로그 발생 => 최종 결과문 GZIP으로 저장
- 조치
       - 수정
       ```
       # ~/infra/firehose.tf
       # 주석 처리
       # compression_format = "UNCOMPRESSED" # 1차는 원본 지정, 활성화되지 않음
       # 주석 해제
       compression_format = "GZIP" # GZIP으로 압축
       ```
       - 인프라 반영
       ```
       LOG_GEN/   terraform -chdir=infra apply
       ```
       - 로그 발생
       ```
       (srcipts/) ./run-generator.sh game 5 5 0.05 1 ap-northeast-2 1
       ```
       - s3 확인
       ```
       de-ai-09-loggen-firehose-3-2026-08-20-15-39-45-06bccbf8-243c-4124-877c-4ef9d97833b3.gz
       ```
