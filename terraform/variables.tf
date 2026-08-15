variable "aws_region" {
  description = "AWS region for the raw landing bucket"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for the raw landing zone"
  type        = string
  default     = "bazale-customer360-raw"
}

variable "raw_prefix" {
  description = "Key prefix under the bucket that dlt writes to"
  type        = string
  default     = "customer360_raw/"
}

variable "snowflake_iam_user_arn" {
  description = <<-EOT
    The STORAGE_AWS_IAM_USER_ARN value from Snowflake's
    `DESC STORAGE INTEGRATION <name>` output. Snowflake generates this -
    it does not exist until the storage integration is created in Snowflake
    first, so this is a chicken-and-egg step documented in README.md.
  EOT
  type        = string
}

variable "snowflake_external_id" {
  description = <<-EOT
    The STORAGE_AWS_EXTERNAL_ID value from Snowflake's
    `DESC STORAGE INTEGRATION <name>` output. Used as a trust-policy
    condition so only that specific Snowflake integration can assume the role.
  EOT
  type        = string
}
