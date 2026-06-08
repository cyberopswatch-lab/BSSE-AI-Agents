# ── Lambda Package Paths ──────────────────────────────────────────────────────
# deploy.sh builds these zip files before running terraform apply.

locals {
  hr_package      = "${path.module}/../agents/hr/hr_agent.zip"
  finance_package = "${path.module}/../agents/finance/finance_agent.zip"
  advisor_package = "${path.module}/../agents/advisor/advisor_agent.zip"

  # Shared environment variables for all agents
  common_env = {
    PROJECT_NAME      = var.project_name
    MEMORY_TABLE      = aws_dynamodb_table.agent_memory.name
    KNOWLEDGE_BUCKET  = aws_s3_bucket.knowledge_base.bucket
    SSM_API_KEY_PATH  = aws_ssm_parameter.anthropic_api_key.name
    CLAUDE_MODEL      = var.claude_model
    MODEL_PROVIDER    = var.model_provider
    CONVERSATION_TTL  = tostring(var.conversation_ttl_days * 86400)
    AWS_REGION_NAME   = var.aws_region
  }
}

# ── AVA — HR Agent ────────────────────────────────────────────────────────────
resource "aws_lambda_function" "hr_agent" {
  function_name    = "${var.project_name}-hr-agent"
  description      = "AVA: BSSE HR Director AI Agent"
  filename         = local.hr_package
  source_code_hash = filebase64sha256(local.hr_package)
  handler          = "handler.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = merge(local.common_env, {
      AGENT_ID   = "ava"
      AGENT_NAME = "AVA"
      AGENT_ROLE = "HR Director"
      KB_PREFIX  = "hr/"
    })
  }
}

resource "aws_cloudwatch_log_group" "hr_agent" {
  name              = "/aws/lambda/${aws_lambda_function.hr_agent.function_name}"
  retention_in_days = 7  # Keep logs 7 days (free tier conscious)
}

# ── FELIX — Finance Agent ─────────────────────────────────────────────────────
resource "aws_lambda_function" "finance_agent" {
  function_name    = "${var.project_name}-finance-agent"
  description      = "FELIX: BSSE Finance Director AI Agent"
  filename         = local.finance_package
  source_code_hash = filebase64sha256(local.finance_package)
  handler          = "handler.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = merge(local.common_env, {
      AGENT_ID   = "felix"
      AGENT_NAME = "FELIX"
      AGENT_ROLE = "Finance Director"
      KB_PREFIX  = "finance/"
    })
  }
}

resource "aws_cloudwatch_log_group" "finance_agent" {
  name              = "/aws/lambda/${aws_lambda_function.finance_agent.function_name}"
  retention_in_days = 7
}

# ── ATLAS — Strategic Advisor ─────────────────────────────────────────────────
resource "aws_lambda_function" "advisor_agent" {
  function_name    = "${var.project_name}-advisor-agent"
  description      = "ATLAS: BSSE Strategic Advisor AI Agent"
  filename         = local.advisor_package
  source_code_hash = filebase64sha256(local.advisor_package)
  handler          = "handler.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = merge(local.common_env, {
      AGENT_ID   = "atlas"
      AGENT_NAME = "ATLAS"
      AGENT_ROLE = "Strategic Advisor"
      KB_PREFIX  = "advisor/"
    })
  }
}

resource "aws_cloudwatch_log_group" "advisor_agent" {
  name              = "/aws/lambda/${aws_lambda_function.advisor_agent.function_name}"
  retention_in_days = 7
}
