# --- Raw landing bucket ---
# Private data lake bucket that dlt writes partitioned Parquet into, and
# that Snowflake reads from via the storage integration defined below.

resource "aws_s3_bucket" "raw_landing" {
  bucket = var.bucket_name

  tags = {
    Project = "customer360"
    Layer   = "raw"
  }
}

resource "aws_s3_bucket_public_access_block" "raw_landing" {
  bucket = aws_s3_bucket.raw_landing.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "raw_landing" {
  bucket = aws_s3_bucket.raw_landing.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_landing" {
  bucket = aws_s3_bucket.raw_landing.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Free-tier friendly: raw Parquet is cheap to keep, but this project doesn't
# need indefinite retention. Expire objects after 90 days rather than
# accumulating storage forever from daily Airflow runs.
resource "aws_s3_bucket_lifecycle_configuration" "raw_landing" {
  bucket = aws_s3_bucket.raw_landing.id

  rule {
    id     = "expire-raw-after-90-days"
    status = "Enabled"

    filter {
      prefix = var.raw_prefix
    }

    expiration {
      days = 90
    }
  }
}
