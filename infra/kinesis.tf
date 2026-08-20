resource "aws_kinesis_stream" "logs" {
  name = local.kinesis_stream_name
  shard_count = var.kinesis_shard_count
  retention_period = var.kinesis_retention_hour

  # 구성 방식
  stream_mode_details {
    # 프로비저닝 모드로 구성 => 샤드수 직접 지정 (부족하면 성능저하, 과하면 비용 과대 -> 측정 데이터가 없으면 온디맨드로 감)
    stream_mode = "PROVISIONED"
  }
}