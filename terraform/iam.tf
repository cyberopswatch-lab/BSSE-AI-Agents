# ── IAM Role for all Lambda functions ────────────────────────────────────────
# All three agents share the same execution role with least-privilege permissions.

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_execution_role" {
  name               = "${var.project_name}-lambda-execution-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  description        = "Execution role for BSSE agent Lambda functions"
}

# ── CloudWatch Logs (required for Lambda to write logs) ───────────────────────
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ── DynamoDB: Read/write to the memory table only ────────────────────────────
data "aws_iam_policy_document" "dynamodb_access" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = [
      aws_dynamodb_table.agent_memory.arn,
      "${aws_dynamodb_table.agent_memory.arn}/index/*"
    ]
  }
}

resource "aws_iam_policy" "dynamodb_access" {
  name        = "${var.project_name}-dynamodb-access"
  description = "Allow agents to read/write their memory in DynamoDB"
  policy      = data.aws_iam_policy_document.dynamodb_access.json
}

resource "aws_iam_role_policy_attachment" "dynamodb_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

# ── S3: Read-only access to the knowledge base bucket ────────────────────────
data "aws_iam_policy_document" "s3_read_access" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.knowledge_base.arn,
      "${aws_s3_bucket.knowledge_base.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "s3_read_access" {
  name        = "${var.project_name}-s3-read-access"
  description = "Allow agents to read company knowledge base from S3"
  policy      = data.aws_iam_policy_document.s3_read_access.json
}

resource "aws_iam_role_policy_attachment" "s3_read_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.s3_read_access.arn
}

# ── SSM: Read the Anthropic API key (encrypted) ───────────────────────────────
data "aws_iam_policy_document" "ssm_read_access" {
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.anthropic_api_key.arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = ["arn:aws:kms:${var.aws_region}:*:alias/aws/ssm"]
  }
}

resource "aws_iam_policy" "ssm_read_access" {
  name        = "${var.project_name}-ssm-read-access"
  description = "Allow agents to retrieve the Anthropic API key from SSM"
  policy      = data.aws_iam_policy_document.ssm_read_access.json
}

resource "aws_iam_role_policy_attachment" "ssm_read_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.ssm_read_access.arn
}
