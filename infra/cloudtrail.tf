# ─────────────────────────────────────────────────────────────────────────────
# S3 BUCKET FOR CLOUDTRAIL LOGS
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "cloudtrail_logs" {
  bucket = "${local.account_id}-cloudtrail-logs"

  force_destroy = true # dev only
  # force_destroy = false In production you NEVER want audit logs accidentally deleted.

  tags = {
    Name = "CloudTrail audit logs"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# BLOCK ALL PUBLIC ACCESS TO THE BUCKET
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket_public_access_block" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  block_public_acls       = true # Reject any request to set a public ACL on the bucket or its objects
  block_public_policy     = true # Reject any bucket policy that grants public access
  ignore_public_acls      = true # Ignore any existing public ACLs (defense in depth)
  restrict_public_buckets = true # Restrict all cross-account access unless explicitly allowed
}

# ─────────────────────────────────────────────────────────────────────────────
# BUCKET POLICY — GRANTS CLOUDTRAIL SERVICE PERMISSION TO WRITE LOGS
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket_policy" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  # depends_on is CRITICAL here.
  # aws_s3_bucket_public_access_block must be applied before the bucket policy.
  # If public access block is applied AFTER the policy, Terraform may try to attach a
  # policy while public access is still enabled, which AWS rejects with an error.
  depends_on = [aws_s3_bucket_public_access_block.cloudtrail_logs]

  policy = jsonencode({
    # jsonencode() converts a Terraform object into a JSON string inline.
    # Alternative: write the JSON in a separate file and use file("cloudtrail_policy.json").
    # jsonencode() keeps everything in one file and is easier to read with Terraform syntax highlighting.

    Version = "2012-10-17"
    # IAM policy language version. Always "2012-10-17" — this is a literal constant,
    # not a date you change. It refers to the IAM policy language version.

    Statement = [
      # STATEMENT 1: Allow CloudTrail to check the bucket's ACL
      # CloudTrail reads the bucket ACL first to verify it has write access.
      # Without this permission, the trail creation fails immediately.
      {
        Sid = "AWSCloudTrailAclCheck"
        # Sid (Statement ID) is a human-readable label. No functional effect, just documentation.

        Effect = "Allow"
        # "Allow" grants the action. The only other option is "Deny".

        Principal = { Service = "cloudtrail.amazonaws.com" }
        # Principal = who is being granted this permission.
        # "cloudtrail.amazonaws.com" is the AWS CloudTrail service identity.
        # This is NOT your IAM user — it's the CloudTrail service itself acting on your behalf.
        # Service principals are how AWS services access each other without human credentials.

        Action = "s3:GetBucketAcl"
        # The specific S3 API action being allowed.
        # CloudTrail calls GetBucketAcl to verify it can write before starting to log.

        Resource = aws_s3_bucket.cloudtrail_logs.arn
        # ARN (Amazon Resource Name) is the globally unique identifier for an AWS resource.
        # Format: arn:aws:s3:::bucket-name
        # We reference the ARN from the bucket resource above — no hardcoding.
      },

      # STATEMENT 2: Allow CloudTrail to write log files to the bucket
      {
        Sid       = "AWSCloudTrailWrite"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        # PutObject = write a file to S3. CloudTrail writes one log file per ~5 minutes.

        Resource = "${aws_s3_bucket.cloudtrail_logs.arn}/AWSLogs/${local.account_id}/*"
        # The Resource is scoped to the exact prefix CloudTrail uses.
        # CloudTrail ALWAYS writes to: s3://{bucket}/AWSLogs/{account_id}/CloudTrail/{region}/{year}/{month}/{day}/
        # Scoping the allow to "/AWSLogs/{account_id}/*" means:
        # → CloudTrail CAN write to that path
        # → CloudTrail CANNOT write to any other path in the bucket (principle of least privilege)
        # The ${...} syntax is Terraform string interpolation — equivalent to f-strings in Python.

        Condition = {
          StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" }
          # This condition requires CloudTrail to set the "bucket-owner-full-control" ACL
          # on every object it writes. This ensures YOU (the bucket owner) always have
          # full control over the log files, even though CloudTrail is writing them.
          # Without this condition, CloudTrail could write files that only it can read.
        }
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# THE CLOUDTRAIL TRAIL
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_cloudtrail" "dpl_audit" {
  name = "dpl-audit-trail"
  # The trail name. Used in CLI lookups: aws cloudtrail lookup-events --name dpl-audit-trail
  # In Week 7: aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue=dpl-admin

  s3_bucket_name = aws_s3_bucket.cloudtrail_logs.id
  # Which S3 bucket receives the logs. References the bucket resource above.

  is_multi_region_trail = true
  # WHY MULTI-REGION?
  # Some AWS services make API calls in us-east-1 regardless of your configured region.
  # For example: IAM is a global service that logs to us-east-1. Route53, CloudFront,
  # billing APIs also use us-east-1. If is_multi_region_trail = false, you'd miss those calls.
  # Multi-region costs no extra money — it only affects where the logs are collected from.

  include_global_service_events = true
  # Records events from global services (IAM, STS, CloudFront, Route53).
  # Without this, an IAM CreateUser call wouldn't appear in your logs.
  # Always true when is_multi_region_trail = true.

  enable_log_file_validation = true
  # CloudTrail creates a SHA-256 digest file alongside each log file.
  # When you read the logs later, you can verify the digest matches — proving
  # the log files weren't modified after they were written.
  # In a security incident, log tampering is the first thing an attacker attempts.
  # This is the digital chain of custody. Non-negotiable for audit purposes.

  depends_on = [aws_s3_bucket_policy.cloudtrail_logs]
  # The trail CANNOT be created before the bucket policy exists.
  # If you remove this depends_on, Terraform might try to create the trail
  # before the bucket policy is attached — CloudTrail would refuse (no write permission).
  # Terraform usually infers dependencies from resource references, but here the trail
  # doesn't directly reference the policy resource, so we declare it explicitly.
}
