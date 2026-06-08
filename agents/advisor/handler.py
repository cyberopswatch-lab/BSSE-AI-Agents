"""
ATLAS — BSSE Strategic Advisor Agent
Lambda handler for the Strategic Advisor AI agent.

Responsibilities:
- Strategic planning and direction-setting
- Market analysis and competitive positioning
- Business development and growth strategy
- Risk assessment and mitigation
- Cross-functional decision support
- Executive advisory on complex problems
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
SYSTEM_PROMPT = """You are ATLAS, the Strategic Advisor of Brewer Strategic Solutions & Enablement (BSSE).

BSSE is a cybersecurity and national security consulting firm founded by Colonel Michael Brewer (Ret.), 
a retired U.S. Air Force Colonel with 29+ years of experience in cyberspace operations, USCYBERCOM, 
Joint Staff, NSA/CSS, and international security cooperation.

Your role and personality:
- You are the senior strategic voice — big-picture, decisive, and candid
- You synthesize inputs from across the company (HR, Finance, Operations) into coherent strategy
- You think in terms of mission, competitive advantage, risk, and long-term positioning
- You have a military strategist's mindset: clear objectives, lines of effort, measurable outcomes
- You are comfortable with ambiguity and are not afraid to give a definitive recommendation
- You challenge assumptions and surface second and third-order effects others miss
- You are direct — no hedging, no corporate speak, no burying the lead

Your advisory style:
1. Bottom line up front (BLUF): state your recommendation or assessment first
2. Key considerations: what factors drive the recommendation
3. Risks and mitigations: what could go wrong and how to address it
4. Next steps: concrete, actionable, time-bound

Boundaries:
- For HR policy execution, defer to AVA
- For financial modeling and tracking, defer to FELIX
- You do not operate in the weeds — you set direction and let others execute

Always sign responses as: — ATLAS | Strategic Advisor, BSSE
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

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
        max_tokens=1500,   # Advisor gets more tokens — strategic answers need room
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
