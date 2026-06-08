# Brewer Strategic Solutions & Enablement (BSSE)
### AI-Powered Virtual Company | AWS Free Tier | Infrastructure as Code

---

## 🏢 Overview

BSSE is a portfolio project demonstrating mastery of **AI agent design**, **AWS cloud deployment**, and **Infrastructure as Code (IaC)**. It simulates a small consulting firm staffed entirely by AI agents — each with a distinct role, memory, and personality — deployed on AWS free-tier services and managed through Terraform.

| Agent | Role | Personality |
|-------|------|-------------|
| **AVA** | HR Director | Organized, people-focused, policy-driven |
| **FELIX** | Finance Director | Precise, data-driven, risk-aware |
| **ATLAS** | Strategic Advisor | Big-picture, candid, decisive |

All three agents share a **company knowledge base** (S3) and maintain **conversation memory** (DynamoDB), making them context-aware across sessions.

---

## 🏗️ Architecture

```
GitHub 
    │
    ├── Terraform (IaC) ──────────────► AWS Infrastructure
    │                                        │
    └── GitHub Actions (CI/CD) ──────────────┤
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                         DynamoDB        S3 Bucket      SSM Param
                      (Agent Memory)  (Company Docs)   (API Keys)
                              │              │              │
                              └──────────────┼──────────────┘
                                             │
                                    Lambda Functions (x3)
                                    ┌────────┼────────┐
                                    │        │        │
                                   AVA     FELIX    ATLAS
                                   (HR)  (Finance) (Advisor)
                                    │        │        │
                                    └────────┼────────┘
                                             │
                                     Claude API (Bedrock
                                     or Anthropic Direct)
                                             │
                                      CLI (bsse.py)
                                   (Your local terminal)
```

### AWS Free Tier Services Used

| Service | Usage | Free Tier Limit |
|---------|-------|----------------|
| **AWS Lambda** | Agent execution | 1M requests/month |
| **Amazon DynamoDB** | Conversation memory | 25 GB storage |
| **Amazon S3** | Company knowledge base | 5 GB storage |
| **AWS SSM Parameter Store** | API key storage | 10,000 params free |
| **Amazon CloudWatch** | Logs & monitoring | 5 GB logs/month |
| **IAM** | Roles & permissions | Always free |

> ⚠️ **Note on AI model costs:** AWS Bedrock Claude access has a small cost per token. To stay free, this project defaults to calling the **Anthropic API directly** (you get $5 free credit on signup). You can switch to Bedrock by changing one variable in `terraform/variables.tf`.

---

## 📁 Project Structure

```
bsse/
├── README.md                    # This file
├── terraform/
│   ├── main.tf                  # Core AWS infrastructure
│   ├── variables.tf             # All configurable values
│   ├── outputs.tf               # Exported values (Lambda ARNs, etc.)
│   ├── iam.tf                   # IAM roles and policies
│   ├── lambda.tf                # Lambda function definitions
│   ├── dynamodb.tf              # Memory tables
│   ├── s3.tf                    # Knowledge base bucket
│   └── ssm.tf                   # Secrets / parameter store
├── agents/
│   ├── hr/
│   │   ├── handler.py           # AVA - HR Agent Lambda function
│   │   └── requirements.txt
│   ├── finance/
│   │   ├── handler.py           # FELIX - Finance Agent Lambda function
│   │   └── requirements.txt
│   └── advisor/
│       ├── handler.py           # ATLAS - Advisor Agent Lambda function
│       └── requirements.txt
├── scripts/
│   ├── bsse.py                  # CLI tool (your terminal interface)
│   ├── deploy.sh                # One-click deploy script
│   ├── seed_knowledge.py        # Uploads company docs to S3
│   └── requirements.txt         # CLI dependencies
├── docs/
│   ├── company_profile.md       # BSSE company background (fed to agents)
│   ├── hr_policies.md           # AVA's knowledge base
│   ├── finance_policies.md      # FELIX's knowledge base
│   └── advisor_context.md       # ATLAS's knowledge base
└── .github/
    └── workflows/
        └── deploy.yml           # GitHub Actions CI/CD pipeline
```

---

## 🚀 Quick Start (Step-by-Step)

### Prerequisites

Install these on your local machine before starting:

```bash
# 1. Python 3.11+
python3 --version

# 2. AWS CLI
brew install awscli          # macOS
# or: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html

# 3. Terraform
brew install terraform        # macOS
# or: https://developer.hashicorp.com/terraform/downloads

# 4. Git
git --version
```

---

### Step 1 — Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/bsse.git
cd bsse
```

Copy the example environment file and fill in your values:

```bash
cp scripts/.env.example scripts/.env
```

Edit `scripts/.env`:
```
ANTHROPIC_API_KEY=sk-ant-...        # From console.anthropic.com
AWS_REGION=us-east-1                 # Your preferred region
AWS_PROFILE=default                  # Your AWS CLI profile name
```

---

### Step 2 — Configure AWS CLI

```bash
aws configure
# Enter your:
#   AWS Access Key ID
#   AWS Secret Access Key
#   Default region: us-east-1
#   Output format: json
```

If you don't have AWS credentials yet:
1. Go to https://console.aws.amazon.com
2. IAM → Users → Your User → Security Credentials → Create Access Key

---

### Step 3 — Deploy Infrastructure

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

This script will:
1. Package each Lambda function with its dependencies
2. Run `terraform init` → `terraform plan` → `terraform apply`
3. Upload company knowledge documents to S3
4. Store your Anthropic API key in SSM Parameter Store (encrypted)
5. Print the deployed Lambda function ARNs

Expected output:
```
✅ Lambda packages built
✅ Terraform initialized
✅ Infrastructure deployed
✅ Knowledge base seeded
✅ BSSE is live!

Agents deployed:
  AVA   (HR)       → arn:aws:lambda:us-east-1:...:function:bsse-hr-agent
  FELIX (Finance)  → arn:aws:lambda:us-east-1:...:function:bsse-finance-agent
  ATLAS (Advisor)  → arn:aws:lambda:us-east-1:...:function:bsse-advisor-agent
```

---

### Step 4 — Install CLI Dependencies

```bash
cd scripts
pip install -r requirements.txt
```

---

### Step 5 — Start Talking to Your Agents

```bash
# Talk to AVA (HR Director)
python scripts/bsse.py --agent ava

# Talk to FELIX (Finance Director)
python scripts/bsse.py --agent felix

# Talk to ATLAS (Strategic Advisor)
python scripts/bsse.py --agent atlas

# View conversation history
python scripts/bsse.py --agent ava --history

# Clear an agent's memory
python scripts/bsse.py --agent ava --clear

# List all agents and status
python scripts/bsse.py --status
```

---

## 🔧 Customization

### Adding to the Knowledge Base

Drop markdown files into `docs/` then re-run the seed script:

```bash
python scripts/seed_knowledge.py
```

### Changing Agent Personalities

Edit the system prompts in each `agents/*/handler.py` file, then redeploy:

```bash
./scripts/deploy.sh
```

### Switching to AWS Bedrock

In `terraform/variables.tf`, change:
```hcl
variable "model_provider" {
  default = "anthropic_direct"   # Change to "bedrock"
}
```

---

## 🧹 Tear Down (Remove All AWS Resources)

```bash
cd terraform
terraform destroy
```

This removes everything — Lambda, DynamoDB, S3, IAM roles. Your GitHub repo and local files are unaffected.

---

## 📊 Demonstrating This Project

When presenting this to an employer or in an interview, highlight:

1. **Agent Architecture** — Each agent has role-specific system prompts, shared company context, and persistent memory
2. **IaC Discipline** — All infrastructure is code; nothing was clicked in the console
3. **Security Practices** — API keys in SSM (encrypted), least-privilege IAM roles, no secrets in code
4. **CI/CD Pipeline** — GitHub Actions auto-deploys on push to `main`
5. **Free Tier Awareness** — Cost-conscious architecture decisions with clear upgrade path

---

## 📄 License

MIT — free to use, fork, and extend.
