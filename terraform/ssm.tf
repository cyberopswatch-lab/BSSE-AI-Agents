# ── Anthropic API Key (SecureString) ─────────────────────────────────────────
# Stored encrypted in SSM. Lambda functions retrieve it at runtime.
# You set the actual value in scripts/.env — deploy.sh pushes it here.

resource "aws_ssm_parameter" "anthropic_api_key" {
  name        = "/${var.project_name}/anthropic_api_key"
  description = "Anthropic API key for BSSE AI agents"
  type        = "SecureString"

  # Placeholder — deploy.sh overwrites this with your real key
  value = "REPLACE_ME_SEE_DEPLOY_SH"

  # Use AWS-managed KMS key (free tier)
  key_id = "alias/aws/ssm"

  lifecycle {
    # Prevent Terraform from overwriting the key after initial creation.
    # deploy.sh manages the actual value via AWS CLI.
    ignore_changes = [value]
  }

  tags = {
    Name = "${var.project_name}-anthropic-api-key"
  }
}
