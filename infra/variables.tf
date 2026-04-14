variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "dpl"          # Short prefix: all resources named dpl-*
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"          # Single environment for this course
}
