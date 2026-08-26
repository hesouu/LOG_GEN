# 목표
- 실버에서 골드로 파이프라인 구성중 기점으로 lambda 사용
    - 실시간 관점에서는 flink를 거치는게 적절함.
- 구성 조합
    - bronze -> flink/lambda -> Silver : 신뢰할수 있는 데이터를 필터링/구성
        - 데이터 클리닝 작업 -> 레코드 단위로 stream processing 처리(flink 관점)
    - `silver -> flink/lambda -> Gold` : 데이터를 사용할 수 있게 구성 (만든다)
         비즈니스 목적에 맞게 변환 처리
            - flink : 실시간 처리
            - lambda : 이볜트 드라이븐 처리 (실습상 s3에 업로드 이벤트 등 활용 or silver-kinesis에서 lambda로 바로 전송(실시간성 살리는컨셉))

# 목표 시스템
```
 kinesis
    ↓
 Firehose
    ↓   
Bronze  -> raw 데이터 / 원본 (정상,오염)
 JSON/GZIP
    ↓
 Kinesis
    ↓
  Flink -> 정제 (고비용/고가용성) -> SQL로 구성 (insert를 통해 silver)
    ↓
Silver Kinesis
    │
    ├── 기존 Firehose
    │       ↓
    │   Parquet(SNAPPY) -> Glue / Model catalog -> Database -> table
    │       ↓
    │   S3 silver/ -> Airflow 배치 프로세싱 -> Athena -> SQL -> 데일리 리포트 구성 (GOLD)
    │
    └── [추가] Lambda : 의도적으로 Silver Kinesis에서 이미 정제된 데이터를 실시간으로 받아서 실시간 파이프라인 흐름 유지
              ↓
         비즈니스 가공 (분석용 데이터로 구성, 집계, 통계, ...) -> pandas / polars / spark(무거움) or  단순구성 처리
              ↓
         Gold Kinesis
              ↓
          Firehose
              ↓
       Glue Schema 참조
              ↓
       Parquet + SNAPPY
              ↓
          S3 gold/
              ↓
         Glue / Athena -> 작업 그룹 구성 -> 대시보드/서비스에서 SQL로 데이터 획득하여 서비스에서 활용
```

# 데이터 변화 확인
- 브론즈 : 원본 raw 데이터 보존
```
{
  "event_id": "evt_...",
  "domain": "ecommerce",
  "event_type": "payment_completed",
  "occurred_at": "2026-08-25T18:35:00.123+09:00",

  "request": {
    "method": "POST",
    "path": "/api/payments"
  },

  "response": {
    "status_code": 200,
    "latency_ms": 418
  },

  "data": {
    "user_id": "usr_483921",
    "session_id": "af20d91c84d24978ac31",
    "product_id": "prd_38142",
    "category": "electronics",
    "quantity": 2,
    "unit_price": 45900,
    "currency": "KRW",
    "campaign": "summer_sale",
    "order_id": "ord_38ab72cf219a4182",
    "total_amount": 91800,
    "payment_method": "card",
    "payment_result": "approved"
  }
}
```
- 브론즈 : 오염 데이터 (보관) -> 후속 처리(원인규명)
- 임의로 구성한것이므로 -> 시나리오를 구성, 실제에 대해 조사후 반영
```
{
  "event_id": "evt_...",
  "domain": "ecommerce",
  "event_type": "payment_completed",
  "occurred_at": "2026-08-25T18:35:01.382+09:00",

  "request": {
    "method": "POST",
    "path": "/api/payments"
  },

  "response": {
    "status_code": 200,
    "latency_ms": 391
  },

  "data": {
    "user_id": "usr_738251",
    "session_id": "98dc15b31d2a4017a832",
    "product_id": "prd_71632",
    "category": "food",

    "quantity": 1000000,

    "unit_price": 18900,
    "currency": "KRW",
    "campaign": null,
    "order_id": "ord_82ae31c20bb84081",
    "total_amount": 18900,
    "payment_method": "easy_pay",
    "payment_result": "approved"
  },

  "_simulation": {
    "is_corrupted": true,
    "corruption_type": "numeric_outlier"
  }
}
```

- 실버
- flink를 토앻서 클린 작업 진행(5가지 유형만), 전처리등 작업 진행
- data 항목에 모든 도메인에 대해 커버 가능하도록 컬럼 추가함, 해당 도메인이 아니면 null 세팅 (슈퍼셋)
- _silver를 추가 => 어떤 단계에서 어떤 프로세서 사용(flink), 언제 정제/전처리등 진행 시간 기록
    - 로그 발생 시간, 각 단계별 처리 시간 비교 => 지연, 전체 처리 시간등 모니터링, 분석처리 가능
```
{
  "schema_version": "1.0",
  "record_type": "application_log",
  "event_id": "befbbe74-c142-475e-a26b-2be5d175b273",
  "trace_id": "aff1b4e4d10a4a589873baa3395ddba4",
  "run_id": "loggen-1695217703-16184",

  "occurred_at": "2026-08-25T14:41:53.280+09:00",
  "generated_at_utc": "2026-08-25T05:41:53.280+00:00",

  "domain": "ecommerce",
  "event_type": "product_view",

  "service": {
    "name": "commerce-api",
    "environment": "simulation",
    "instance_id": "sim-07"
  },

  "client": {
    "ip": "128.189.114.29",
    "user_agent": "Mozilla/5.0 Chrome/151.0 Android/15",
    "device_id": "973ee19556c34e20"
  },

  "request": {
    "method": "GET",
    "path": "/api/products/prd_31528",
    "request_bytes": 147
  },

  "response": {
    "status_code": 200,
    "latency_ms": 57,
    "response_bytes": 2204
  },

  "data": {
    "user_id": "usr_366134",
    "session_id": "0119d7b2a06f401ab8c3",
    "product_id": "prd_31528",
    "category": "fashion",
    "quantity": 1,
    "unit_price": 297200,
    "currency": "KRW",

    "campaign": null,
    "keyword": null,
    "result_count": null,
    "order_id": null,
    "total_amount": null,
    "payment_method": null,
    "payment_result": null
  },

  "_silver": {
    "layer": "silver",
    "processor": "apache-flink",
    "schema_version": "1.0",
    "processed_at": "2026-08-25T05:41:54.644721+00:00"
  }
}
```
- 골드
- 분석용 데이터 생성 목표
    - 집계, 통계등 분석에 필요한 데이터 형태를 구성
    - lambda에서 아래 처럼 데이터를 구성 or 아래 처럼 데이터를 확보할수 있게 전단계 구성
        - athena를 통해서 최종 집계뜽 데이터 조회
```
{
  "domain": "ecommerce",
  "category": "electronics",

  "action_count": 1523,
  "total_revenue": 28452000,
  "avg_order": 18681,
  "conversion_rate": 0.087
}
```



# 인프라 및 코드 구성
- lambda/lambda_function.py 신규
- infra/gold-lambda.py 신규
- infra/glue-gold.py 신규
- infra/outputs.tf 내용 추가
- lambda 서비스 배포 작업 (필요한 추가파일등 고려)

# lambda
- 서버에 대한 걱정 없이 코드 실행(함수 단위)
    - 파이썬/노드/자바 등 언어에 대한 세팅x
    - 최소 라이브러리만 지원 => 필요시 서브 파트 라이브러리 업로드 해야함
- 서버리스
- 이벤트 드라이븐 형태로 작동
    - s3에 뭔가 업로드 되었다(소카 서비스 이용후 차량 촬영하여 업로드) -> 트리거 작동 ->
        람다 작동 -> 사진 전처리/분석 행위 -> 결과를 SQS 전송 -> gold에 도달 -> 고객 앱으로 전달(eX. 파손 비용 10만원 부과)

# 람다 코드 작성
'''
/
L lambda
|   L lambda_function.py: 현재는 간단하게 헬로월드 수준으로 구성
```

# 인프라 구성
-