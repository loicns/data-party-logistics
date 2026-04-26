# infra/rds.tf — RDS Postgres with PostGIS for the DPL warehouse

# ─── Data sources ─────────────────────────────────────────────────────────────
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

locals {
  my_ip = "${chomp(data.http.my_ip.response_body)}/32"
}

# ─── Security group ────────────────────────────────────────────────────────────
resource "aws_security_group" "rds_postgres" {
  name        = "dpl-rds-postgres"
  description = "Allow Postgres access from developer IP"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Postgres from developer IP"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [local.my_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = "data-party-logistics"
    Week    = "3"
  }
}

# ─── DB subnet group ───────────────────────────────────────────────────────────
resource "aws_db_subnet_group" "dpl" {
  name       = "dpl-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Project = "data-party-logistics"
  }
}

# ─── RDS instance ──────────────────────────────────────────────────────────────
resource "aws_db_instance" "dpl_postgres" {
  identifier     = "dpl-warehouse"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"

  allocated_storage     = 20
  max_allocated_storage = 30
  storage_type          = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.dpl.name
  vpc_security_group_ids = [aws_security_group.rds_postgres.id]
  publicly_accessible    = true

  multi_az = false

  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false

  performance_insights_enabled = true

  tags = {
    Project = "data-party-logistics"
    Week    = "3"
  }
}

# ─── Variables ─────────────────────────────────────────────────────────────────
variable "db_name" {
  description = "Database name"
  type        = string
  default     = "dpl_dev"
}

variable "db_username" {
  description = "Master username"
  type        = string
  default     = "dpl"
}

variable "db_password" {
  description = "Master password"
  type        = string
  sensitive   = true
}

# ─── Outputs ───────────────────────────────────────────────────────────────────
output "rds_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.dpl_postgres.endpoint
}

output "rds_host" {
  description = "RDS hostname only"
  value       = aws_db_instance.dpl_postgres.address
}

output "rds_port" {
  description = "RDS port"
  value       = aws_db_instance.dpl_postgres.port
}
