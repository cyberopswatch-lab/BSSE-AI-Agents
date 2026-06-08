# ── Knowledge Base Bucket ─────────────────────────────────────────────────────
# Stores company documents that agents retrieve at runtime.
# Bucket name must be globally unique — project_name + account ID suffix handles that.

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "knowledge_base" {
  # Globally unique: bsse-knowledge-base-<your-account-id>
  bucket = "${var.project_name}-knowledge-base-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-knowledge-base"
  }
}

# Block all public access — this bucket is internal only
resource "aws_s3_bucket_public_access_block" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning so you can track document changes
resource "aws_s3_bucket_versioning" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
