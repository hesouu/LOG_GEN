# 편의상 실시간성을 고려하여 구성
# silver -> lambda -> gold kinesis -> firehose -> Glue schema -> Parkquet(SNAPPY) -> s3 gold/ 

# 파이썬 파일 -> ZIP 패키징 관련
# lambda python 소스코드를 AWS lmabda에 배포할 ZIP 파일에 포함하여 자동 생성
data "archive_file" "gold_lambda" {
    type = "zip"
    source_file = "${path.module}/../lambda/lambda_function.py"
    output_path = "${path.module}/../lambda/gold-lambda.zip"
 
}
