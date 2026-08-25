# Managed Service for Apache Flink ( 관리형 서비스 형태의 Flink ) 의 IAM
data "aws_iam_policy_document" "flink_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["kinesisanalytics.amazonaws.com"]
    }
  }
}
# 2. 해당 Role 정의(생성) -> 기본 flink 정책 반영된 role
resource "aws_iam_role" "flink" {
  name               = "${var.project_name}-flink-role"
  assume_role_policy = data.aws_iam_policy_document.flink_assume.json
}

# 3. 추가로 정책을 반영 (정책 조회 -> 정책 role 연결)
#    브론즈 kinesis 읽기(입력,  inputsteam)
#    실버 kinesis  쓰기 (출력,  outputstream)
#    s3에 flink의 애플리케이션 zip 파일 읽기 -> 실행할수 있음
#    Cloudwatch에 로그 기록
data "aws_iam_policy_document" "flink" {
  statement {
    sid    = "ReadBronzeKinesis" # statement 구분용
    effect = "Allow"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:GetShardIterator",
      "kinesis:GetRecords",
      "kinesis:ListShards"
    ]
    resources = [
      aws_kinesis_stream.logs.arn
    ]
  }
  # 실버 레벨에 존재하는 kinesis로 데이터 전송(쓰기, 출력스트림)에 대한 권한
  statement {
    sid    = "WriteSilverKinesis"
    effect = "Allow"
    actions = [
      "kinesis:PutRecord",
      "kinesis:PutRecords"
    ]
    resources = [
      aws_kinesis_stream.silver.arn
    ]
  }
  statement {
    sid    = "WriteRejectKinesis"
    effect = "Allow"
    actions = [
      "kinesis:PutRecord",
      "kinesis:PutRecords"
    ]
    resources = [
      aws_kinesis_stream.rejected.arn
    ]
  }
  # s3에 저장된 flink 어플리케이션 코드(zip 형태로 구성)
  statement {
    sid    = "ReadFlinkCode"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion"
    ]
    resources = [
      # 본인 버킷/flink/*
      "${aws_s3_bucket.data.arn}/flink/*"
    ]
  }
  # 로그 읽기
  statement {
    sid    = "DescribeFlinkLog"
    effect = "Allow"
    actions = [
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ]
    resources = [
      "*"
    ]
  }
  # 로그 쓰기 
  statement {
    sid    = "WriteFlinkLog"
    effect = "Allow"
    actions = [
      "logs:PutLogEvents"
    ]
    resources = [
      "${aws_cloudwatch_log_group.flink.arn}:*" # <- 수정
    ]
  }
}

# 위에서 만든 기본 role에 아래에서 조회한 정책 부여
resource "aws_iam_role_policy" "flink" {
  name   = "${var.project_name}-flink-policy"
  role   = aws_iam_role.flink.id
  policy = data.aws_iam_policy_document.flink.json
}


# silver layer 에서 사용하는 firehose role
data "aws_iam_policy_document" "firehose_silver_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "firehose_silver" {
  name               = "${var.project_name}-firehose-silver-role"
  assume_role_policy = data.aws_iam_policy_document.firehose_silver_assume.json
}
data "aws_iam_policy_document" "firehose_silver" {
  # silver kinesis 읽기 권한 관련  
  statement {
    effect = "Allow"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:GetShardIterator",
      "kinesis:GetRecords",
      "kinesis:ListShards"
    ]
    resources = [
      aws_kinesis_stream.silver.arn
    ]
  }
  # s3 저장 권한 관련
  statement {
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:ListBucket",
      "s3:PutObject"
    ]
    resources = [
      aws_s3_bucket.data.arn,       # 해당 버킷
      "${aws_s3_bucket.data.arn}/*" # 해당 버킷 이하 모든 경로
    ]
  }
  # [GLUE] Firehose가 JSON -> Parquet로 변환 처리시 GLue catalog의 Schema 조회할수 있는 권한 부여
  statement {
    effect = "Allow"
    actions = [
      "glue:GetTable",
      "glue:GetTableVersion",
      "glue:GetTableVersions"
    ]
    resources = ["*"]
  }
}
resource "aws_iam_role_policy" "firehose_silver" {
  name   = "${var.project_name}-firehose-silver-s3-policy"
  role   = aws_iam_role.firehose_silver.id
  policy = data.aws_iam_policy_document.firehose_silver.json
}

# rejected용 데이터 파이프라인 구성을 위한 firehose role 작성
data "aws_iam_policy_document" "firehose_rejected_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "firehose_rejected" {
  name               = "${var.project_name}-firehose-rejected-role"
  assume_role_policy = data.aws_iam_policy_document.firehose_rejected_assume.json
}
data "aws_iam_policy_document" "firehose_rejected" {
  statement {
    effect = "Allow"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:GetShardIterator",
      "kinesis:GetRecords",
      "kinesis:ListShards"
    ]
    resources = [
      aws_kinesis_stream.rejected.arn
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:ListBucket",
      "s3:PutObject"
    ]
    resources = [
      aws_s3_bucket.data.arn,       # 해당 버킷
      "${aws_s3_bucket.data.arn}/*" # 해당 버킷 이하 모든 경로
    ]
  }
}
resource "aws_iam_role_policy" "firehose_rejected" {
  name   = "${var.project_name}-firehose-rejected-s3-policy"
  role   = aws_iam_role.firehose_rejected.id
  policy = data.aws_iam_policy_document.firehose_rejected.json
}