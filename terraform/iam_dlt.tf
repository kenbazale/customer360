# --- dlt ingestion IAM user ---
# Programmatic access for the dlt pipeline. Scoped to just this bucket and
# prefix - not AmazonS3FullAccess, which is broader than the pipeline needs.

resource "aws_iam_user" "dlt_ingestion" {
  name = "customer360-dlt"

  tags = {
    Project = "customer360"
  }
}

data "aws_iam_policy_document" "dlt_ingestion" {
  statement {
    sid    = "ListBucketPrefix"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [aws_s3_bucket.raw_landing.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.raw_prefix}*"]
    }
  }

  statement {
    sid    = "ReadWriteObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.raw_landing.arn}/${var.raw_prefix}*"]
  }
}

resource "aws_iam_policy" "dlt_ingestion" {
  name   = "customer360-dlt-s3-access"
  policy = data.aws_iam_policy_document.dlt_ingestion.json
}

resource "aws_iam_user_policy_attachment" "dlt_ingestion" {
  user       = aws_iam_user.dlt_ingestion.name
  policy_arn = aws_iam_policy.dlt_ingestion.arn
}

# Access key is created manually via the console (or `aws iam
# create-access-key`) rather than in Terraform state - secret keys
# shouldn't live in a .tfstate file, encrypted or not.
