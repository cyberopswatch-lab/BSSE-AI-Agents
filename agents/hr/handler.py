"""
AVA — BSSE HR Director Agent
Lambda handler for the HR AI agent.

Responsibilities:
- Employee onboarding / offboarding guidance
- HR policy questions and interpretation
- Hiring and workforce planning advice
- Performance management consultation
- Benefits and compensation guidance
"""

import json
import os
import boto3
import anthropic
from datetime import datetime, timezone

# ── AWS Clients ───────────────────────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION_NAME"])
s3 = boto3.client("s3", region_name=os.environ["AWS_REGION_NAME"])
ssm = boto3.client("ssm", region_name=os.environ["AWS_REGION_NAME"])

# ── Config from environment ───────────────────────────────────────────────────
AGENT_ID        = os.environ["AGENT_ID"]
AGENT_NAME      = os.environ["AGENT_NAME"]
AGENT_ROLE      = os.environ["AGENT_ROLE"]
MEMORY_TABLE    = os.environ["MEMORY_TABLE"]
KNOWLEDGE_BUCKET= os.environ["KNOWLEDGE_BUCKET"]
SSM_API_KEY_PATH= os.environ["SSM_API_KEY_PATH"]
CLAUDE_MODEL    = os.environ["CLAUDE_MODEL"]
KB_PREFIX       = os.environ["KB_PREFIX"]
TTL_SECONDS     = int(os.environ.get("CONVERSATION_TTL", str(30 * 86400)))

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are AVA, the HR Director of Brewer Strategic Solutions & Enablement (BSSE).

BSSE is a cybersecurity and national security consulting firm founded by Colonel Michael Brewer (Ret.), 
specializing in cyber operations strategy, workforce development, and international security cooperation.

Your role and personality:
- You are organized, empathetic, and policy-driven
- You handle all people-related matters: hiring, onboarding, performance, benefits, culture
- You know BSSE's policies inside and out and apply them consistently
- You care deeply about employee wellbeing and company culture
- You are direct but tactful — you never sugarcoat policy, but you always deliver it with care
- When you don't know something, you say so and offer to research it

Boundaries:
- You only answer questions within your HR domain
- For financial questions, refer to FELIX (Finance Director)
- For strategic questions, refer to ATLAS (Strategic Advisor)
- You do not speculate about matters outside HR

Always sign responses as: — AVA | HR Director, BSSE
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_api_key() -> str:
    """Retrieve Anthropic API key from SSM Parameter Store."""
    response = ssm.get_parameter(Name=SSM_API_KEY_PATH, WithDecryption=True)
    return response["Parameter"]["Value"]


def load_knowledge_base() -> str:
    """Load agent-specific documents from S3 knowledge base."""
    try:
        response = s3.list_objects_v2(Bucket=KNOWLEDGE_BUCKET, Prefix=KB_PREFIX)
        docs = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".md") or key.endswith(".txt"):
                body = s3.get_object(Bucket=KNOWLEDGE_BUCKET, Key=key)["Body"].read().decode("utf-8")
                docs.append(f"--- {key} ---\n{body}")
        if docs:
            return "\n\n".join(docs)
        return ""
    except Exception as e:
        print(f"Warning: Could not load knowledge base: {e}")
        return ""


def get_memory(session_id: str) -> list:
    """Retrieve conversation history from DynamoDB."""
    table = dynamodb.Table(MEMORY_TABLE)
    try:
        response = table.get_item(Key={"agent_id": AGENT_ID, "session_id": session_id})
        item = response.get("Item", {})
        return item.get("messages", [])
    except Exception as e:
        print(f"Warning: Could not load memory: {e}")
        return []


def save_memory(session_id: str, messages: list):
    """Save conversation history to DynamoDB with TTL."""
    table = dynamodb.Table(MEMORY_TABLE)
    ttl = int(datetime.now(timezone.utc).timestamp()) + TTL_SECONDS
    try:
        table.put_item(Item={
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "messages": messages,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "ttl": ttl
        })
    except Exception as e:
        print(f"Warning: Could not save memory: {e}")


# ── Main Handler ──────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context) -> dict:
    """
    Lambda entry point.

    Expected event payload:
    {
        "action": "chat" | "clear" | "history",
        "session_id": "default",
        "message": "Your question here"
    }
    """
    action     = event.get("action", "chat")
    session_id = event.get("session_id", "default")
    user_msg   = event.get("message", "")

    # ── Handle history request ────────────────────────────────────────────────
    if action == "history":
        messages = get_memory(session_id)
        return {"status": "ok", "agent": AGENT_NAME, "history": messages}

    # ── Handle clear request ──────────────────────────────────────────────────
    if action == "clear":
        save_memory(session_id, [])
        return {"status": "ok", "agent": AGENT_NAME, "message": f"{AGENT_NAME} memory cleared for session '{session_id}'."}

    # ── Handle chat ───────────────────────────────────────────────────────────
    if not user_msg:
        return {"status": "error", "message": "No message provided."}

    # Load knowledge base and conversation history
    knowledge = load_knowledge_base()
    messages  = get_memory(session_id)

    # Build system prompt with knowledge base injected
    system = SYSTEM_PROMPT
    if knowledge:
        system += f"\n\n## BSSE Reference Documents\n\nUse the following documents to answer policy questions accurately:\n\n{knowledge}"

    # Append new user message
    messages.append({"role": "user", "content": user_msg})

    # Call Claude
    api_key = get_api_key()
    client  = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system,
        messages=messages
    )

    assistant_reply = response.content[0].text

    # Append assistant reply and persist
    messages.append({"role": "assistant", "content": assistant_reply})
    save_memory(session_id, messages)

    return {
        "status":     "ok",
        "agent":      AGENT_NAME,
        "role":       AGENT_ROLE,
        "session_id": session_id,
        "reply":      assistant_reply,
        "usage": {
            "input_tokens":  response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }
    }
