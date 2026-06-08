terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Store Terraform state in S3 (optional but recommended for teams)
  # Uncomment after first deploy if you want remote state:
  # backend "s3" {
  #   bucket = "bsse-terraform-state"
  #   key    = "state/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project     = "BSSE"
      ManagedBy   = "Terraform"
      Environment = var.environment
      Owner       = "Michael Brewer"
    }
  }
}
