provider "aws" {
  region  = var.aws_region    # From variables.tf — eu-west-3
  profile = "dpl"             # Uses ~/.aws/credentials [dpl] profile — same as AWS CLI

  default_tags {
    tags = {
      Project     = "data-party-logistics"    # Visible in AWS Console and Cost Explorer
      Environment = var.environment            # "dev" for this course
      ManagedBy   = "terraform"               # Signals this resource is IaC-managed (don't touch manually)
    }
  }
}

# Fetch the current AWS account ID at plan time
# This avoids hardcoding the 12-digit account ID anywhere in the config
data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  # locals are computed values — like Python variables in Terraform
  # Used as: local.account_id throughout other .tf files
}
