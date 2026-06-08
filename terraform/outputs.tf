output "hr_agent_lambda_arn" {
  description = "ARN of AVA the HR Agent Lambda function"
  value       = aws_lambda_function.hr_agent.arn
}

output "finance_agent_lambda_arn" {
  description = "ARN of FELIX the Finance Agent Lambda function"
  value       = aws_lambda_function.finance_agent.arn
}

output "advisor_agent_lambda_arn" {
  description = "ARN of ATLAS the Advisor Agent Lambda function"
  value       = aws_lambda_function.advisor_agent.arn
}

output "knowledge_base_bucket" {
  description = "S3 bucket name for the company knowledge base"
  value       = aws_s3_bucket.knowledge_base.bucket
}

output "memory_table_name" {
  description = "DynamoDB table name for agent conversation memory"
  value       = aws_dynamodb_table.agent_memory.name
}

output "ssm_api_key_path" {
  description = "SSM parameter path where the Anthropic API key is stored"
  value       = aws_ssm_parameter.anthropic_api_key.name
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

# Convenience block for CLI configuration
output "cli_config" {
  description = "Paste this into scripts/.env after deploying"
  value = <<-EOT
    # Add these to scripts/.env after deployment:
    HR_LAMBDA_ARN=${aws_lambda_function.hr_agent.arn}
    FINANCE_LAMBDA_ARN=${aws_lambda_function.finance_agent.arn}
    ADVISOR_LAMBDA_ARN=${aws_lambda_function.advisor_agent.arn}
    MEMORY_TABLE=${aws_dynamodb_table.agent_memory.name}
    KNOWLEDGE_BUCKET=${aws_s3_bucket.knowledge_base.bucket}
    AWS_REGION=${var.aws_region}
  EOT
}
