
# Gold Kinesis Stream 이름을 출력한다.
output "gold_kinesis_stream_name" {
  value = aws_kinesis_stream.gold.name
}

# Gold Kinesis Stream ARN을 출력한다.
output "gold_kinesis_stream_arn" {
  value = aws_kinesis_stream.gold.arn
}

# Silver -> Gold Lambda 함수 이름을 출력한다.
output "gold_lambda_function_name" {
  value = aws_lambda_function.silver_to_gold.function_name
}

# Gold Firehose 이름을 출력한다.
output "gold_firehose_name" {
  value = aws_kinesis_firehose_delivery_stream.gold.name
}

# Gold Glue Database 이름을 출력한다.
output "gold_glue_database_name" {
  value = aws_glue_catalog_database.gold.name
}

# Athena에서 사용할 Gold Glue Table 이름을 출력한다.
output "gold_glue_table_name" {
  value = aws_glue_catalog_table.gold.name
}

# Gold 데이터가 저장되는 S3 Prefix를 출력한다.
output "gold_s3_prefix" {
  value = "s3://${aws_s3_bucket.data.bucket}/gold/"
}