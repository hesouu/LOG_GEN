# Fargate는 ECR TASK(로그 생성)를 생성하여 CloudWatch에 저장
# ECR에 등록된 이미지(PUSH 작업 진행), CloudWatch에 저장(로그 전송) -> 2개 권한 필요
# 1. ECR TASK policy 조회(어떤 것이 가능-> xx.amazon.com )
data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}
# 2. 해당 Role 정의(생성)
resource "aws_iam_role" "ecs_execution" {
  name               = "${var.project_name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

# 3. Role, 정책 연결 마무리, 실제 실행시 필요한 권한 부여!!
resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}