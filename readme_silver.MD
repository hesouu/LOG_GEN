# 개요
- Bronze (raw 데이터 저장, 모은 단위 중요)
  - log generator => kinesis => firehose(1Mib/60s) => s3 bronze (raw data, GZIP)
- Silver (raw 데이터 -> 정제/전처리등 데이터 조작 -> 저장)
  - Streamming Ingestion => `Streamming Processing + Medalion Architecture`
  - step 1
    - log generator => kinesis(input) => flink(자바,파이썬(pyflink), pom.xml,maven) => kinesis(outut) => firehose => s3 silver
      - `flink, kinesis(outut), firehose 3개 리소스` 생성
      - s3 silver : 기존 버킷 하위에 구성
        - jsonl 저장 -> GZIP 저장
        - parquet 저장 -> Glue 스키마 구성하여 연동 
  - step 2
    - log generator => kinesis(input) => lambda => kinesis(outut) => firehose => s3 silver

# Flink
- 실시간으로 스트리밍 데이터에서 실행 가능한 분석 정보를 확보
  - 실시간 데이터를 실시간으로 전처리/정제등 작업 가능 -> 거의 지연 없다
- 실시간일 필요 없다 => Airlfow or Step Function(AWS) 이용하여 Batch Processing 처리
- Siiver 단계로 저장하는 방법
  - [v]실시간 -> flink, lambda
  - 배치   -> Airlfow or Step Function(AWS)

- 특징
  - 실시간 스트림 처리: Kinesis에서 들어오는 데이터를 계속 읽으면서 즉시 처리
  - Stateful Processing: 이전 이벤트 상태를 기억하면서 집계·판단 가능
  - Event Time 지원: 데이터가 실제 발생한 시간을 기준으로 처리 가능
  - Window 처리: 1분, 5분, 1시간 단위 집계 같은 작업에 강함
  - Checkpoint / 장애 복구: 처리 상태를 저장해서 장애 후 이어서 처리 가능
  - Exactly-once 처리 지원: 중복이나 누락을 최소화하는 신뢰성 높은 스트림 처리 가능
  - `대용량 처리에 적합`: 지속적인 고속 이벤트 처리에 Lambda보다 유리
  - 복잡한 처리 가능: 필터링, 변환, 집계, 조인, 이상 탐지 등에 적합


# 데이터 저장소
```
S3 Bucket
├── bronze/
│   └── year=.../month=.../day=.../hour=...
├── silver/
│   └── year=.../month=.../day=.../hour=...
├── flink/
│   └── applications/
│       └── flink-silver-xxxxx.zip <- flink 처리를 수행하는 앱(*.py, pom.xml, *.jar)
└── errors/
    ├── bronze/
    │   └── ...
    └── silver/
        └── ...

```

# 구조 
- 브론즈 유지 및 일부 수정
- 실버 레이어 추가 kinesis(브론즈) 공급자, flink는 소비자 관점
```
로그 생성기
    ↓
Kinesis Raw (2가지 방향성으로 전송)
    ├────────────→ Firehose → S3 Bronze
    │
    └→ Flink
         ↓
     검증 / 정제 / 변환
         ↓
   Kinesis Silver
         ↓
      Firehose
         ↓
      S3 Silver
```

# 인프라 수정

| 구분         | 파일              | 변경 내용                                            |
| ---------- | --------------- | ------------------------------------------------ |
| **수정**     | `locals.tf`     | Silver Kinesis/Flink/Firehose 이름 추가              |
| **수정**     | `variables.tf`  | Flink Runtime, Parallelism, Silver Shard 등 변수 추가 |
| **수정**     | `firehose.tf`   | Bronze 오류 경로를 `errors/bronze/`로 정리               |
| **수정**     | `outputs.tf`    | Silver/Flink 관련 Output 추가                        |
| ---------- | --------------- | ------------------------------------------------ |
| **신규**     | `iam-flink.tf`  | Flink + Silver Firehose IAM                      |
| **신규**     | `silver.tf`     | Silver Kinesis + Silver Firehose 생성              |
| **신규**     | `flink.tf`      | Managed Flink + `flink/`에 코드 업로드                 |
| **신규**     | `flink-logs.tf` | Flink CloudWatch 로그                              |