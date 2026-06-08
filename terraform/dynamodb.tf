# ── Agent Memory Table ────────────────────────────────────────────────────────
# Stores conversation history for all three agents.
# Partition key: agent_id (e.g. "ava", "felix", "atlas")
# Sort key: session_id (allows multiple sessions per agent)
# Each item contains: messages (list), timestamp, ttl

resource "aws_dynamodb_table" "agent_memory" {
  name         = "${var.project_name}-agent-memory"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "agent_id"
  range_key    = "session_id"

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  # TTL: automatically delete old conversations after N days
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-agent-memory"
  }
}
