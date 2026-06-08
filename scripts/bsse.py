#!/usr/bin/env python3
"""
bsse.py — CLI interface for Brewer Strategic Solutions & Enablement AI Agents

Usage:
    python bsse.py --agent ava                  # Chat with AVA (HR)
    python bsse.py --agent felix                # Chat with FELIX (Finance)
    python bsse.py --agent atlas                # Chat with ATLAS (Advisor)
    python bsse.py --agent ava --session work   # Named session (persistent)
    python bsse.py --agent ava --history        # View conversation history
    python bsse.py --agent ava --clear          # Clear conversation memory
    python bsse.py --status                     # Show all agents and Lambda status
"""

import argparse
import boto3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── Load environment ──────────────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

AWS_REGION       = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE      = os.getenv("AWS_PROFILE", "default")
HR_LAMBDA_ARN    = os.getenv("HR_LAMBDA_ARN", "")
FINANCE_LAMBDA_ARN = os.getenv("FINANCE_LAMBDA_ARN", "")
ADVISOR_LAMBDA_ARN = os.getenv("ADVISOR_LAMBDA_ARN", "")

AGENT_MAP = {
    "ava":   {"arn": HR_LAMBDA_ARN,      "name": "AVA",   "role": "HR Director",       "color": "\033[94m"},
    "felix": {"arn": FINANCE_LAMBDA_ARN, "name": "FELIX", "role": "Finance Director",  "color": "\033[92m"},
    "atlas": {"arn": ADVISOR_LAMBDA_ARN, "name": "ATLAS", "role": "Strategic Advisor", "color": "\033[93m"},
}

# ANSI colors
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"

# ── AWS Lambda Client ─────────────────────────────────────────────────────────

def get_lambda_client():
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return session.client("lambda")


def invoke_agent(lambda_arn: str, payload: dict) -> dict:
    """Invoke a Lambda function and return the parsed response."""
    client = get_lambda_client()
    response = client.invoke(
        FunctionName=lambda_arn,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8")
    )
    raw = response["Payload"].read().decode("utf-8")
    result = json.loads(raw)
    # Lambda wraps errors in a different structure
    if "errorMessage" in result:
        raise RuntimeError(f"Lambda error: {result['errorMessage']}")
    return result


# ── Display Helpers ───────────────────────────────────────────────────────────

def print_header():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗
║   Brewer Strategic Solutions & Enablement (BSSE)         ║
║   AI Agent Command Interface                              ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")


def print_agent_banner(agent_key: str, session_id: str):
    agent = AGENT_MAP[agent_key]
    color = agent["color"]
    print(f"\n{color}{BOLD}┌─ {agent['name']} | {agent['role']} ─────────────────────────────┐{RESET}")
    print(f"{DIM}  Session: {session_id}  |  Type 'exit' or Ctrl+C to quit{RESET}")
    print(f"{DIM}  Commands: !history | !clear | !status{RESET}")
    print(f"{color}{BOLD}└──────────────────────────────────────────────────────────┘{RESET}\n")


def print_reply(agent_name: str, color: str, reply: str, usage: dict = None):
    print(f"\n{color}{BOLD}{agent_name}:{RESET}")
    print(f"{WHITE}{reply}{RESET}")
    if usage:
        print(f"\n{DIM}[tokens: {usage.get('input_tokens',0)} in / {usage.get('output_tokens',0)} out]{RESET}")
    print()


def print_history(history: list, agent_name: str, color: str):
    if not history:
        print(f"{DIM}No conversation history for this session.{RESET}\n")
        return
    print(f"\n{BOLD}Conversation History — {agent_name}{RESET}\n")
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            print(f"{CYAN}{BOLD}You:{RESET} {content}\n")
        elif role == "assistant":
            print(f"{color}{BOLD}{agent_name}:{RESET} {content}\n")
        print(f"{DIM}{'─' * 60}{RESET}")


def print_status():
    """Show all agents and their Lambda deployment status."""
    client = get_lambda_client()
    print(f"\n{BOLD}BSSE Agent Status{RESET}\n")
    print(f"{'Agent':<8} {'Name':<8} {'Role':<20} {'Status':<12} {'ARN'}")
    print("─" * 90)
    for key, agent in AGENT_MAP.items():
        arn = agent["arn"]
        if not arn:
            status = f"{RED}NOT CONFIGURED{RESET}"
            print(f"{key:<8} {agent['name']:<8} {agent['role']:<20} {status}")
            continue
        try:
            fn_name = arn.split(":")[-1]
            resp = client.get_function_configuration(FunctionName=fn_name)
            state = resp.get("State", "Unknown")
            status_color = "\033[92m" if state == "Active" else RED
            status = f"{status_color}{state}{RESET}"
        except Exception as e:
            status = f"{RED}ERROR{RESET}"
        print(f"{key:<8} {agent['name']:<8} {agent['role']:<20} {status:<20} {arn[-40:]}")
    print()


# ── Main Chat Loop ────────────────────────────────────────────────────────────

def chat(agent_key: str, session_id: str):
    agent = AGENT_MAP[agent_key]
    color = agent["color"]
    arn   = agent["arn"]

    if not arn:
        print(f"{RED}Error: Lambda ARN for {agent['name']} is not configured.{RESET}")
        print(f"Run ./deploy.sh first, then add the ARN to scripts/.env\n")
        sys.exit(1)

    print_agent_banner(agent_key, session_id)

    while True:
        try:
            user_input = input(f"{CYAN}{BOLD}You:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Goodbye.{RESET}\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye"):
            print(f"\n{DIM}Session ended. Memory saved.{RESET}\n")
            break

        # In-session commands
        if user_input == "!history":
            result = invoke_agent(arn, {"action": "history", "session_id": session_id})
            print_history(result.get("history", []), agent["name"], color)
            continue

        if user_input == "!clear":
            invoke_agent(arn, {"action": "clear", "session_id": session_id})
            print(f"{DIM}Memory cleared for this session.{RESET}\n")
            continue

        if user_input == "!status":
            print_status()
            continue

        # Normal chat
        try:
            print(f"{DIM}...{RESET}", end="\r")
            result = invoke_agent(arn, {
                "action":     "chat",
                "session_id": session_id,
                "message":    user_input
            })
            print_reply(agent["name"], color, result.get("reply", ""), result.get("usage"))
        except Exception as e:
            print(f"{RED}Error invoking agent: {e}{RESET}\n")


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BSSE AI Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--agent",   choices=["ava", "felix", "atlas"], help="Which agent to talk to")
    parser.add_argument("--session", default="default", help="Session ID (for named persistent sessions)")
    parser.add_argument("--history", action="store_true", help="Show conversation history and exit")
    parser.add_argument("--clear",   action="store_true", help="Clear agent memory and exit")
    parser.add_argument("--status",  action="store_true", help="Show all agent deployment status")

    args = parser.parse_args()

    print_header()

    if args.status:
        print_status()
        return

    if not args.agent:
        parser.print_help()
        print(f"\n{DIM}Tip: try  python bsse.py --agent atlas{RESET}\n")
        return

    agent_key = args.agent
    session_id = args.session

    if args.history:
        agent = AGENT_MAP[agent_key]
        result = invoke_agent(agent["arn"], {"action": "history", "session_id": session_id})
        print_history(result.get("history", []), agent["name"], agent["color"])
        return

    if args.clear:
        agent = AGENT_MAP[agent_key]
        invoke_agent(agent["arn"], {"action": "clear", "session_id": session_id})
        print(f"Memory cleared for {agent['name']} / session '{session_id}'.\n")
        return

    chat(agent_key, session_id)


if __name__ == "__main__":
    main()
