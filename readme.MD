# 목표
- AWS Fargate를 이용한 로그 생성기
  - AWS Fargate
    - EC2 사용/관리 x
    - ECR에 등록된 이미지를 이용하여 ECS에서 직접 컨테이너 실행 -> `서버리스`로 실행환경 제공 받고 수행 
    - 비용 가장 저렴
  - 발생된 데이터
    - 데이터 형태 : 요청 -> 서비스 대응 -> 응답 => 모두 합친 최종 로그, 서비스 구성 x
    - 데이터 저장 
      - s3 : 다음 챕터에서 확장 활용
      - cloudwatch : aws 로그 저장
      - file
      - 콘솔

# 인프라 구성
- variables.tf  : 리전, 프로젝트명, CPU/Memory 등 정보 기술, 구성 조정
- version.tf    : 
- provider.tf   : 
- locals.tf     : 공통값 가공, 태그, 전페 프로젝트 프리픽스
- vpc.tf        : 전용 네트워크, VPC, subnet, IGW, Route table, SG, AZ 가능
- sg.tf         : 보안그룹 (외부 연결 x) -> ingress 미지정
- iam.tf        : Fargate가 ECR 이미지 획득, CloudWatch에 로그기록 -> 권한부여
- logs.tf       : ECS 컨테이너내에 (로그 생성기 존재) 발생되는 로그 -> 로그 그룹 지정
- ecr.tf        : 로그 생성기 (파이썬 코드) -> Docker 이미지로 생성하여 저장할 저장소
- ecs.tf        : ECS 클러스터와 Fargate Task Definition등이 구동되는 실행 환경 제공 -> 1회성 (상시 운영 x)
- outputs.tf    : 생성후 각종 정보 출력

# 인프라 구성
```
> ~/infra
> terraform init
> terraform fmt
> terraform vaildate
> terraform plan
> terraform apply
```

# 로그 생성기 (~/generator)
## 로그 포멧 (공통)
- 서비스 요청에 따른 처리가 완료된후 로그로 기록하는 최종 필드를 포함한 데이터 샘플
```json
{
  "schema_version": "1.0",
  "record_type": "application_log",
  "event_id": "...",
  "trace_id": "...",
  "run_id": "...",
  "occurred_at": "2026-08-12T16:30:11.123+09:00",
  "generated_at_utc": "2026-08-12T07:30:11.123+00:00",
  "domain": "ecommerce",
  "event_type": "order_created",
  "service": {...},
  "client": {...},
  "request": {
    "method": "POST",
    "path": "/api/orders",
    "request_bytes": 1234
  },
  "response": {
    "status_code": 201,
    "latency_ms": 287,
    "response_bytes": 3590
  },
  "data": {... domain specific ...}  <- 도메인별로 커스텀 구성
}
```

## 지원 도메인 및 이벤트 정의
- domain으로 카테고리 설정

| DOMAIN | 주요 이벤트 예시 |
|---|---|
| `ecommerce` | product_view, search, add_to_cart, checkout, order_created, payment_completed |
| `finance` | account_login, balance_inquiry, card_payment, transfer, deposit, withdrawal |
| `smartfactory` | sensor_reading, equipment_state, quality_inspection, alarm, maintenance_event |
| `game` | login, session_heartbeat, match_started, match_finished, item_purchase, quest_completed |