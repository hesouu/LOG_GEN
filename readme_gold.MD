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
Bronze
 JSON/GZIP
    ↓
 Kinesis
    ↓
  Flink
    ↓
Silver Kinesis
    │
    ├── 기존 Firehose
    │       ↓
    │   Parquet
    │       ↓
    │   S3 silver/
    │
    └── [추가] Lambda : 의도적으로 Silver Kinesis에서 이미 정제된 데이터를 실시간으로 받아서 실시간 파이프라인 흐름 유지
              ↓
         비즈니스 가공 (분석용 데이터로 구성, 집계, 통계, ...) -> pandas / polars / spark
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
         Glue / Athena
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