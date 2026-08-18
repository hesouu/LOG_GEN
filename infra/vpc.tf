# 로그 생성기 전용 VPC
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}
# IGW, 외부에서 자유롭게 처리 가능
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}
# 각각 가용영역에 퍼블릭 서브넷 반영
resource "aws_subnet" "public" {
  # 2개
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  availability_zone       = local.availability_zones[count.index]
  cidr_block              = var.public_subnet_cidrs[count.index]
  # NAT 없이 인터넷 통신 가능토록 Public IP 할당 (이 비용 월 0.5달러)
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${count.index+1}"
    Type = "loggen-public"
  }
}

# 라우트 테이블
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}
# 외부 트레픽을 IGW 전달
resource "aws_route" "internet" {
  route_table_id = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id = aws_internet_gateway.this.id
}
# 퍼블릭 서브넷, IGW (연결)
resource "aws_route_table_association" "public" {
  # 퍼블릭 서브넷 2개 -> 2번 연결
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}