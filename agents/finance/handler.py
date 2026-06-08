"""
FELIX — BSSE Finance Director Agent
Lambda handler for the Finance AI agent.

Responsibilities:
- Budget planning and tracking
- Expense policy guidance
- Financial reporting and forecasting
- Contract and vendor cost analysis
- Invoice and billing questions
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
SYSTEM_PROMPT = """You are FELIX, the Finance Director of Brewer Strategic Solutions & Enablement (BSSE).

BSSE is a cybersecurity and national security consulting firm founded by Colonel Michael Brewer (Ret.), 
specializing in cyber operations strategy, workforce development, and international security cooperation.

Your role and personality:
- You are precise, methodical, and data-driven
- You handle all financial matters: budgeting, expenses, forecasting, contracts, billing
- You are conservative by default — you always flag risk before opportunity
- You think in numbers and timelines; you appreciate specificity
- You present options clearly with pros, cons, and cost implications
- You are direct and do not over-explain — executives want the bottom line first

Boundaries:
- You only answer questions within your Finance domain
- For HR questions, refer to AVA (HR Director)
- For high-level strategic decisions, refer to ATLAS (Strategic Advisor)
- You do not give investment advice beyond company operational finance

Always sign responses as: — FELIX | Finance Director, BSSE
"""

# ── Helpers (identical to HR agent — shared pattern) ─────────────────────────

def get_api_key() -> str:
    response = ssm.get_parameter(Name=SSM_API_KEY_PATH, WithDecryption=True)
    return response["Parameter"]["Value"]


def load_knowledge_base() -> str:
    try:
        response = s3.list_objects_v2(Bucket=KNOWLEDGE_BUCKET, Prefix=KB_PREFIX)
        docs = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".md") or key.endswith(".txt"):
                body = s3.get_object(Bucket=KNOWLEDGE_BUCKET, Key=key)["Body"].read().decode("utf-8")
                docs.append(f"--- {key} ---\n{body}")
        return "\n\n".join(docs) if docs else ""
    except Exception as e:
        print(f"Warning: Could not load knowledge base: {e}")
        return ""


def get_memory(session_id: str) -> list:
    table = dynamodb.Table(MEMORY_TABLE)
    try:
        response = table.get_item(Key={"agent_id": AGENT_ID, "session_id": session_id})
        return response.get("Item", {}).get("messages", [])
    except Exception as e:
        print(f"Warning: Could not load memory: {e}")
        return []


def save_memory(session_id: str, messages: list):
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
    action     = event.get("action", "chat")
    session_id = event.get("session_id", "default")
    user_msg   = event.get("message", "")

    if action == "history":
        messages = get_memory(session_id)
        return {"status": "ok", "agent": AGENT_NAME, "history": messages}

    if action == "clear":
        save_memory(session_id, [])
        return {"status": "ok", "agent": AGENT_NAME, "message": f"{AGENT_NAME} memory cleared for session '{session_id}'."}

    if not user_msg:
        return {"status": "error", "message": "No message provided."}

    knowledge = load_knowledge_base()
    messages  = get_memory(session_id)

    system = SYSTEM_PROMPT
    if knowledge:
        system += f"\n\n## BSSE Reference Documents\n\n{knowledge}"

    messages.append({"role": "user", "content": user_msg})

    api_key = get_api_key()
    client  = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system,
        messages=messages
    )

    assistant_reply = response.content[0].text
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
