# 개요
- Bronze (raw 데이터 저장, 모은 단위 중요)
  - log generator => kinesis => firehose(1Mib/60s) => s3 bronze (raw data, GZIP)
- Silver (raw 데이터 -> 정제/전처리등 데이터 조작 -> 저장)
  - Streaming Ingestion => `Streamning Processing + Medalion Archetecher`
  - step 1
    - log generator => kinesis(input) => flink(자바,파이썬(pyflink), pom.xml,maven) => kinesis(outut) => firehose => s3 silver
  - step 2
    - log generator => kinesis(input) => lambda => kinesis(outut) => firehose => s3 silver

# Flink
- 실시간으로 스트리밍 데이터에서 실행 가능한 분석 정보를 확보
    - 실시간 데이터를 전처리/정제등 작업 가능 -> 거의 지연 없다

- 실시간일 필요 없다면 -> Airflow or step Function(AWS) 이용하여 Batch Processing 처리
- silver layer에 저장하는 방법
    -[v]실시간 -> fling, lambda
    - 배치   -> Airflow or step Fucntion(AWS)

- 특징
  - 실시간 스트림 처리: Kinesis에서 들어오는 데이터를 계속 읽으면서 즉시 처리
  - Stateful Processing: 이전 이벤트 상태를 기억하면서 집계·판단 가능
  - Event Time 지원: 데이터가 실제 발생한 시간을 기준으로 처리 가능
  - Window 처리: 1분, 5분, 1시간 단위 집계 같은 작업에 강함
  - Checkpoint / 장애 복구: 처리 상태를 저장해서 장애 후 이어서 처리 가능
  - Exactly-once 처리 지원: 중복이나 누락을 최소화하는 신뢰성 높은 스트림 처리 가능
  - `대용량 처리에 적합`: 지속적인 고속 이벤트 처리에 Lambda보다 유리
  - 복잡한 처리 가능: 필터링, 변환, 집계, 조인, 이상 탐지 등에 적합