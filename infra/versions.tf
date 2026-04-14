terraform {
  required_version = ">= 1.5"   # Minimum Terraform CLI version

  required_providers {
    aws = {
      source  = "hashicorp/aws"  # Official AWS provider from Hashicorp registry
      version = "~> 5.0"         # "~> 5.0" means: 5.0 ≤ version < 6.0 (patch updates OK, major not)
    }
  }
}
