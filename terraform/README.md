# Terraform: Customer 360 AWS infrastructure

Codifies the S3 bucket and IAM identities this project depends on — the
same resources originally created by hand through the AWS Console during
initial development, now expressed as code so the infrastructure is
reproducible, reviewable, and destroyable in one command.

## What this manages

- The private, encrypted, versioned S3 bucket used as the raw landing zone
- A scoped IAM user for the dlt ingestion pipeline (not `AmazonS3FullAccess`)
- An IAM role trusted by Snowflake's storage integration, scoped to
  read-only access on this bucket's prefix

## What this does NOT manage (and why)

Snowflake-side objects (database, warehouse, schema, storage integration,
stage, tables) are **not** in this Terraform config. That's a deliberate
scope decision, not an oversight — there's a genuine chicken-and-egg
dependency between AWS and Snowflake here:

1. Snowflake's storage integration must exist first to generate its own
   IAM user ARN and external ID
2. This Terraform config needs those two values to build the trust policy
   on the AWS side
3. Only after the AWS role exists can you go back into Snowflake and set
   `STORAGE_AWS_ROLE_ARN` to point at it

Terraform *does* have a Snowflake provider that could manage the
Snowflake-side objects too, closing this loop entirely — that's a natural
next step, not included here to keep this first pass focused on the AWS
side.

## Usage

```bash
cd terraform
terraform init

# Step 1: create the Snowflake storage integration manually first (see
# main project README), then run:
DESC STORAGE INTEGRATION customer360_s3_int;
# copy STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID from the output

terraform plan \
  -var="snowflake_iam_user_arn=arn:aws:iam::<snowflake-account>:user/<...>" \
  -var="snowflake_external_id=<...>"

terraform apply \
  -var="snowflake_iam_user_arn=arn:aws:iam::<snowflake-account>:user/<...>" \
  -var="snowflake_external_id=<...>"

# Step 2: after apply, take the snowflake_role_arn output and run in Snowflake:
ALTER STORAGE INTEGRATION customer360_s3_int
  SET STORAGE_AWS_ROLE_ARN = '<snowflake_role_arn output>';

# Step 3: create an access key for the dlt IAM user (not managed by
# Terraform - secrets don't belong in state files) and add it to
# ingestion/.dlt/secrets.toml:
aws iam create-access-key --user-name customer360-dlt
```

## Migrating existing hand-created resources

If you already have the bucket and IAM identities from the manual setup
(as this project originally did), `terraform apply` will fail with
"already exists" errors rather than silently duplicating them. Import
the existing resources into Terraform's state first:

```bash
terraform import aws_s3_bucket.raw_landing bazale-customer360-raw
terraform import aws_iam_user.dlt_ingestion customer360-dlt
terraform import aws_iam_role.snowflake_customer360 snowflake_customer360_role
```

After importing, run `terraform plan` — it should show no changes (or only
minor drift like missing tags), confirming the code now accurately
represents what's already running.

## Destroying

```bash
terraform destroy
```

Note the S3 bucket has versioning enabled, which can leave old object
versions behind that block deletion. If `destroy` fails on the bucket,
empty all versions first via the console or `aws s3api
delete-objects`/`aws s3 rb --force`.
