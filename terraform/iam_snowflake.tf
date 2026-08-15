# --- Snowflake storage integration IAM role ---
# Trust policy allows ONLY Snowflake's specific IAM user to assume this
# role, and only when presenting the external ID Snowflake generated for
# this integration. This is what stops anyone else who might guess
# Snowflake's ARN from assuming the role.

data "aws_iam_policy_document" "snowflake_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.snowflake_iam_user_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [var.snowflake_external_id]
    }
  }
}

resource "aws_iam_role" "snowflake_customer360" {
  name               = "snowflake_customer360_role"
  assume_role_policy = data.aws_iam_policy_document.snowflake_trust.json

  tags = {
    Project = "customer360"
  }
}

data "aws_iam_policy_document" "snowflake_s3_access" {
  statement {
    sid       = "ReadObjects"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.raw_landing.arn}/${var.raw_prefix}*"]
  }

  statement {
    sid       = "ListBucketPrefix"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.raw_landing.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.raw_prefix}*"]
    }
  }
}

resource "aws_iam_role_policy" "snowflake_s3_access" {
  name   = "snowflake-s3-read"
  role   = aws_iam_role.snowflake_customer360.id
  policy = data.aws_iam_policy_document.snowflake_s3_access.json
}
