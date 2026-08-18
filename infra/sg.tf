# ecs => cloudwatch => s3, kinesis,.... , 외부 연결 x
resource "aws_security_group" "fargate" {
  name = "${var.project_name}-fargate-sg"
  description = "외부 연결 없이 fargate 전용"
  vpc_id = aws_vpc.this.id
  #  ingress allow(허가) 정의 x => 모두 차단함
  tags = {
    Name = "${var.project_name}-fargate-sg"
  }
}

# ECR push, Cloudwatch Logs 전송 => outbound 허용
# 위에서 egress를 적용하지 않고, 다른 리소스에서 특정 sg에 반영하는 케이스
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.fargate.id
  cidr_ipv4 = "0.0.0.0/0"
  ip_protocol = "-1" # -1 : 모든 프로토콜에 대응
}