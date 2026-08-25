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
| ---------- | --------------- | ------------------------------------------------ |
| **신규**     | `iam-flink.tf`  | Flink + Silver Firehose IAM                      |
| **신규**     | `silver.tf`     | Silver Kinesis + Silver Firehose 생성              |
| **신규**     | `flink.tf`      | Managed Flink + `flink/`에 코드 업로드                 |
| **신규**     | `flink-logs.tf` | Flink CloudWatch 로그                              |
| **수정**     | `outputs.tf`    | Silver/Flink 관련 Output 추가                        |


# flink 앱 구성
- 구성
```
flink/
├── app/
│   ├── main.py         : flink 앱 엔트리포인트(실행파트), 브론즈 kinesis 읽기, 
│   │                     transform 모둘 불러서 clean 작업진행, 실버 kinesis 가동된(전처리된) 데이터 전송
│   └── transform.py    : 정제, 전처리 등 데이터 처리 작업 진
├── target/             : 빌드후 생성 : maven 빌드 결과물로 생성
│   └── *.zip           : 빌드후 생성 : 빌드 결과로 생성된  flink 앱
├── assembly/
│   └── assembly.xml    : flink 앱(zip 파일) 성분 구성에 대한 정의 (*.py, pyflink-dependencies.jar)
│
├── application_properties.json : 로컬에서 실행시 input/output kinesis 설정
├── pom.xml             : 의존성 파일들 다운로드, jar 생성, zip 패키징 실행
├── README.md
└── .gitignore
```

- 빌드전 설치 (java, maven)
```
# 윈도우
winget search Microsoft.OpenJDK 
winget install Microsoft.OpenJDK.11
  java -version

choco install maven or scoop install main/maven or 직접설치
https://maven.apache.org/download.cgi?utm_source=chatgpt.com 접속 > apache-maven-3.9.16-bin.zip 다운
bin 폴더를 path 설정
  mvn -version

# 맥
brew install openjdk@11 maven
export JAVA_HOME=$(/usr/libexec/java_home -v 11)
export PATH="$JAVA_HOME/bin:$PATH"
java -version
mvn -version
```

- 빌드
```
./scripts/build-flink.bat
sh ./scripts/build-flink.sh
```

# 세팅 
```
# 인프라 구성
terraform -chdir=infra fmt
terraform -chdir=infra validate
terraform -chdir=infra plan

./scripts/setup.bat

# Flink 서비스 진입 -> 어플리케이션의 상태 체크 -> 실행 상태가 확인되면 (그린라이트)

# 로그 발송 -> 1분 전후로 s3/버킷/silver 생성 여부 확인 -> 하위에 로그가 존재함 => 완료!!

```

# 트레블 슈팅
```
# 등록된 리소스 확인
terraform state list

# AlreadyExists => 예전게 남아 있는 경우 
# 리소스 등록분에서 누락된 부분이 잇으면 수동 연결
# terraform import 리소스명 리소스값
terraform import aws_ecr_repository.generator de-ai-09-loggen-repo


```




# 확인
- 실시간 스트리밍 데이터 처리 관점
  - 실버 레벨 추가 부분
    - flink 앱 코드 확인
      - 추후 필요시 코드 업그레이드(기능 추가 부여)

    - 오염된 데이터 삭제(현재) => 별도 보관(저장) => 추후 해당 원인 분석 할수 있게 보관 (확장)
    - 저장데이터 -> jsonl (gzip) => parquet 저장(glue 사용)
    - flink 역활 lambda 대체 (차이점 이해)
  - 실버 -> 골드 추가
    - flink or lambda 사용 가능 => 최종 목표 형태로 가공
    - 중간 과정 동일
    - 최종 s3 적제(parquet) / opensearch
  - 대시보드 (프로메테우스, 그라파다 등 연결)
    - s3=>athena 쿼리질의, opensearch 검색질의 => 대시보드상 실시간 모니터링 데이터 조회에 응답가능

- 로그 생성기 => kinesis => firehose => s3(브론즈) 저장
  - 배치 프로세싱 (airflow 기반) + 메탈리온 아킥텍처 적용
    - 특정 주기 단위로 airflow 작동 => 브론즈 -> 실버 -> 골드 -> 최종 산출물(대시보드, 래포트) 구성

- 카프카 (뒤에서 체크)
- ELK, EFK
- step function, eventbridge 

# flink 앱 코드 확인
- 80% 코드 유지
  - 필요한 기능만 추가하는 구조로 활용
  - 함수에서 핵심 부분(정제, 전처리)만 커스텀 하면 기능 활용
  - 리소스가 변경되면 보정(설정값)

# 오염된 데이터 삭제(현재) => 별도 보관(저장)
## 개요
- 추후 해당 원인 분석 할수 있게 보관 (확장)
- 구성
```
Bronze Kinesis -> 배치 프로세싱을 통해 오염 데이터만 추출하여 주기적으로 모니터링 방법
      ↓
    Flink
      │
      ├─ 정상 → Silver Kinesis → Firehose → S3 silver/
      │
      └─ 비정상 → Rejected Kinesis
                       ↓
                    Firehose
                       ↓
                  S3 rejected/ => 차후 배치 프로세싱을 통해 => 근본적인 문제 해결
```
- 정상과 비정상은 flink에서 연결
  - none으로 처리되는 부분을 Rejected Kinesis로 전달하도록 sql 수정
- Rejected Kinesis -> Firehose > S3 Rejected/ : 인프라 구성

## 인프라 구성
- 추가 및 수정
  - 인프라 구성 -> 적용
    - 대상 : kinesis 신규, kinesis->firehose, iam, flink, locals, variables, outputs    
  - flink 수정 -> 테스트 -> 오염데이터를 비율 30% 상승 -> 로그 발생 -> 오염데이터 저장 확인
- 실행 절차
  - flink 앱 빌드 + 인프라 업데이트 및 앱 배포
    ```
      scripts\setup-flink.bat
      
      sh ./scripts/setup-flink.sh

      ----
      scripts\flink-status.bat
      ----------------------------------------------------------
      |                   DescribeApplication                  |
      +-------------------------------+--------------+---------+
      |             Name              |   Runtime    | Status  |
      +-------------------------------+--------------+---------+
      |  de-ai-09-loggen-silver-flink |  FLINK-1_20  |  READY  |
      +-------------------------------+--------------+---------+

      -----
      scripts\flink-start.bat

      scripts\flink-status.bat
      # READY -> STARTING -> RUNNING

      ----- 
      # RUNNING 상태가 확인되면 -> 로그 발생, 오염도 30% 확대
      scripts\run-generator.bat ecommerce 30 10 0.30 1 ap-northeast-2 1

      -----
      # s3에서 reject 폴더 하위 데이터 확인

      -----
      # flink 중단
      scripts\flink-stop.bat
      -----
      # 중단 후 확인
      scripts\flink-status.bat
      ----------------------------------------------------------                                               
      |                   DescribeApplication                  |
      +-------------------------------+--------------+---------+
      |             Name              |   Runtime    | Status  |
      +-------------------------------+--------------+---------+
    ```
  - 로그 제너레이터 가동 -> 오염도를 30% 올려서 잘 수집되도록 구성


# parquet 저장 => 스키마 필요 => 열검색, 기반 => Glue 제공 (데이터베이스, 테이블, 크롤러, job등 다양하게 제공)
## glue
- 데이터에 관련된 통합 서비스
- 데이터를 구조를 정의, 이를 기반으로 쿼리 수행(골드 레이어 적합한 데이터 형태로 추출(집계, 통계,..=>분석))등 기반 제공
- 데이터베이스, 테이블, 스키마, 크롤러(데이터를 보고 자동으로 스키마 구성), ETL job 시각적 구성, ...

## parquet
- `대규모 빅데이터를 효율적으로 저장`하고 `빠르게 조회`하기 위해 만든 `열(Column) 기반 오픈소스 파일 포맷`
- 같은 양의 데이터를 더 작은 공간을 사용, 검색 더 빠르고, 호환 거의다 지원

## 인프라 수정/추가
- silver.tf의 firehose 저장 파트의 저장 부분 수정
  - silver layer를 통해 저장된 데이터 => 현재:gzip 파일, 대체:parquet 형태
  - compression_format = "GZIP" => UNCOMPRESSED
  - 압축 담당 SNAPPY 담당
- glue-silver.tf
  - s3 silver/.... 저장되는 parquet 데이터의 `스키마` 정의
  - json -> parquet 으로 변환할때 스키마 참조
  - Athena(raw데이터, parquet등 압축데이터를 대상으로 쿼리 가능)이 해당 파일을 대상으로 SQL 수행시 테이블/스키마 제공
  - s3 저장될대, 파티션 형태로 저장(year/month/day/hour)된 형태에서 sql 수행 가능(파티션 활용)
- iam-flink.tf
  - 기존 role에 glue 권한 추가
- outputs.tf
  - glue 관련 이름, 리소스등 출력

- 인프라 반영
  - terraform -chdir=infra plan
  - terraform -chdir=infra apply
  - fink 앱 가동(대시보드 or flink-start.bat)
  - flink-status.bat => RUNNING
  - 로그 발송
  - 1분후 > s3://버킷/silver/..../*.parquet 확인 => 다운로드 => 구글 parquet 뷰어 => 드레그드롭
  - Glue가서 데이데이스, 테이블등 각각 조회 > 스키마 확인
  - flink 앱 중지(대시보드 or flink-stop.bat)
  - flink-status.bat => READY