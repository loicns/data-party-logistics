resource "aws_s3_bucket" "raw" {
  bucket = "${var.project_name}-raw-${local.account_id}"
  # Naming: "dpl-raw-123456789012"
  # Standard naming convention for all globally-named resources.

  tags = {
    Name = "Raw data landing zone"
  }
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id # Reference to the bucket above — Terraform resolves the ID automatically
  versioning_configuration {
    status = "Enabled"
    # WHY VERSIONING?
    # If an ingestion client writes a corrupted file, versioning lets you restore the previous version.
    # Also required for dbt's S3 external tables to work correctly.
    # Minimal cost: S3 charges for storage of old versions (lifecycle rule below deletes them).
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id

  rule {
    id     = "archive-old-raw"
    status = "Enabled"

    filter {} # Apply lifecycle rule to ALL objects in the bucket

    transition {
      days          = 90        # After 90 days → move to Glacier (10x cheaper than S3 Standard)
      storage_class = "GLACIER" # Glacier = archival storage, retrieval takes minutes
    }

    expiration {
      days = 365 # After 365 days → delete permanently (no cost)
    }
    # WHY THIS MATTERS:
    # AIS data arrives every 15 minutes = ~96 files/day = ~2,880 files/month.
    # Without lifecycle rules, files accumulate and costs compound.
    # With this rule: data is cheap after 90 days and gone after a year.
    # For a real pipeline, we'd use the Glacier data for model retraining.
    # For this project just keeps costs under control.
  }
}

output "s3_bucket_raw_name" {
  value = aws_s3_bucket.raw.id # Prints after terraform apply — copy this into your .env
}

output "s3_bucket_raw_arn" {
  value = aws_s3_bucket.raw.arn # ARN needed for IAM policies in Week 7
}
