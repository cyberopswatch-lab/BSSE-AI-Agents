variable "aws_region" {
  description = "AWS region to deploy into. us-east-1 has the broadest free-tier coverage."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name to use for deployment."
  type        = string
  default     = "default"
}

variable "environment" {
  description = "Deployment environment tag."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Short project identifier used in all resource names."
  type        = string
  default     = "bsse"
}

variable "lambda_runtime" {
  description = "Python runtime for Lambda functions."
  type        = string
  default     = "python3.11"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds. 30s is plenty for agent calls."
  type        = number
  default     = 30
}

variable "lambda_memory" {
  description = "Lambda memory in MB. 256MB keeps us firmly in free tier."
  type        = number
  default     = 256
}

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode. PAY_PER_REQUEST is free-tier friendly."
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "model_provider" {
  description = "Which AI provider to use: 'anthropic_direct' (uses Anthropic API key) or 'bedrock' (AWS Bedrock, requires Bedrock access)."
  type        = string
  default     = "anthropic_direct"

  validation {
    condition     = contains(["anthropic_direct", "bedrock"], var.model_provider)
    error_message = "model_provider must be 'anthropic_direct' or 'bedrock'."
  }
}

variable "claude_model" {
  description = "Claude model ID to use."
  type        = string
  default     = "claude-haiku-4-5-20251001"  # Fastest and cheapest; great for agents
}

variable "conversation_ttl_days" {
  description = "How many days to retain conversation history in DynamoDB before auto-expiry."
  type        = number
  default     = 30
}
