output "bucket_name" {
  description = "S3 bucket name - use in .dlt/config.toml as bucket_url"
  value       = aws_s3_bucket.raw_landing.id
}

output "bucket_arn" {
  value = aws_s3_bucket.raw_landing.arn
}

output "dlt_iam_user_name" {
  description = "IAM user for dlt - create an access key for this user manually"
  value       = aws_iam_user.dlt_ingestion.name
}

output "snowflake_role_arn" {
  description = "Paste this into Snowflake: ALTER STORAGE INTEGRATION ... SET STORAGE_AWS_ROLE_ARN = '<this>'"
  value       = aws_iam_role.snowflake_customer360.arn
}
