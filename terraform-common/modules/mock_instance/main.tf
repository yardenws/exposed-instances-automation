# Creates a deliberately exposed EC2 instance for testing the scanner.
# Only created when var.create = true. Use in dev/testing environments only.

data "aws_ami" "amazon_linux" {
  count       = var.create ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- VPC ---

resource "aws_vpc" "mock" {
  count      = var.create ? 1 : 0
  cidr_block = "10.0.0.0/24"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-mock-vpc"
  })
}

# --- Internet Gateway ---

resource "aws_internet_gateway" "mock" {
  count  = var.create ? 1 : 0
  vpc_id = aws_vpc.mock[0].id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-mock-igw"
  })
}

# --- Public Subnet ---

resource "aws_subnet" "mock" {
  count                   = var.create ? 1 : 0
  vpc_id                  = aws_vpc.mock[0].id
  cidr_block              = "10.0.0.0/24"
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-mock-public-subnet"
  })
}

# --- Route Table ---

resource "aws_route_table" "mock" {
  count  = var.create ? 1 : 0
  vpc_id = aws_vpc.mock[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mock[0].id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-mock-rt"
  })
}

resource "aws_route_table_association" "mock" {
  count          = var.create ? 1 : 0
  subnet_id      = aws_subnet.mock[0].id
  route_table_id = aws_route_table.mock[0].id
}

# --- Permissive Security Group ---

resource "aws_security_group" "mock" {
  count       = var.create ? 1 : 0
  name        = "${var.name_prefix}-mock-wide-open"
  description = "Intentionally permissive SG for testing the exposure scanner"
  vpc_id      = aws_vpc.mock[0].id

  # SSH from anywhere
  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP from anywhere
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # PostgreSQL from anywhere
  ingress {
    description = "PostgreSQL from anywhere"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-mock-wide-open"
  })
}

# --- EC2 Instance ---

resource "aws_instance" "mock" {
  count                       = var.create ? 1 : 0
  ami                         = data.aws_ami.amazon_linux[0].id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.mock[0].id
  vpc_security_group_ids      = [aws_security_group.mock[0].id]
  associate_public_ip_address = true

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-mock-exposed"
    Environment = "test"
    Purpose     = "scanner-testing"
  })
}
