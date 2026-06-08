#!/usr/bin/env bash
# deploy.sh — One-click deploy script for BSSE
# Run this from the repo root: ./scripts/deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[BSSE]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo -e "\n${CYAN}╔══════════════════════════════════════════════════╗"
echo -e "║  Brewer Strategic Solutions & Enablement (BSSE) ║"
echo -e "║  Deployment Script                              ║"
echo -e "╚══════════════════════════════════════════════════╝${NC}\n"

# ── Check prerequisites ───────────────────────────────────────────────────────
info "Checking prerequisites..."
command -v terraform >/dev/null 2>&1 || error "Terraform not found. Install from https://developer.hashicorp.com/terraform/downloads"
command -v aws       >/dev/null 2>&1 || error "AWS CLI not found. Install from https://aws.amazon.com/cli/"
command -v python3   >/dev/null 2>&1 || error "Python 3 not found."
command -v pip3      >/dev/null 2>&1 || error "pip3 not found."
success "All prerequisites found"

# ── Load .env ─────────────────────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
    warn ".env not found. Copying from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
    error "Please fill in $ENV_FILE with your ANTHROPIC_API_KEY and AWS settings, then re-run."
  else
    error ".env not found. Create $ENV_FILE with ANTHROPIC_API_KEY, AWS_REGION, AWS_PROFILE."
  fi
fi

set -a; source "$ENV_FILE"; set +a

[[ -z "${ANTHROPIC_API_KEY:-}" ]] && error "ANTHROPIC_API_KEY is not set in .env"
[[ -z "${AWS_REGION:-}" ]]        && error "AWS_REGION is not set in .env"
success ".env loaded"

# ── Package Lambda functions ──────────────────────────────────────────────────
info "Packaging Lambda functions..."

for AGENT in hr finance advisor; do
  AGENT_DIR="$REPO_ROOT/agents/$AGENT"
  PACKAGE="$AGENT_DIR/${AGENT}_agent.zip"

  info "  → Building $AGENT agent..."
  cd "$AGENT_DIR"

  # Install dependencies into a local package dir
  pip3 install -r requirements.txt -t ./package --quiet --upgrade

  # Zip: dependencies first, then handler
  cd package
  zip -r9 "$PACKAGE" . --quiet
  cd ..
  zip -g "$PACKAGE" handler.py --quiet

  # Cleanup
  rm -rf package/

  success "  ✓ $AGENT agent packaged: $(du -sh "$PACKAGE" | cut -f1)"
done

cd "$REPO_ROOT"
success "All Lambda packages built"

# ── Terraform Init & Apply ────────────────────────────────────────────────────
info "Initializing Terraform..."
cd "$REPO_ROOT/terraform"

terraform init -upgrade -input=false > /dev/null
success "Terraform initialized"

info "Planning infrastructure..."
terraform plan \
  -var="aws_region=$AWS_REGION" \
  -var="aws_profile=${AWS_PROFILE:-default}" \
  -input=false \
  -out=tfplan \
  > /dev/null

info "Applying infrastructure (this takes ~60 seconds on first run)..."
terraform apply -input=false -auto-approve tfplan

success "Infrastructure deployed"

# ── Push API key to SSM ───────────────────────────────────────────────────────
info "Storing Anthropic API key in SSM Parameter Store..."
aws ssm put-parameter \
  --name "/bsse/anthropic_api_key" \
  --value "$ANTHROPIC_API_KEY" \
  --type SecureString \
  --overwrite \
  --region "$AWS_REGION" \
  --profile "${AWS_PROFILE:-default}" \
  > /dev/null

success "API key stored (encrypted)"

# ── Capture outputs and update .env ──────────────────────────────────────────
info "Capturing Terraform outputs..."
HR_ARN=$(terraform output -raw hr_agent_lambda_arn)
FINANCE_ARN=$(terraform output -raw finance_agent_lambda_arn)
ADVISOR_ARN=$(terraform output -raw advisor_agent_lambda_arn)
MEMORY_TABLE=$(terraform output -raw memory_table_name)
KNOWLEDGE_BUCKET=$(terraform output -raw knowledge_base_bucket)

# Append Lambda ARNs to .env (remove old ones first)
cd "$REPO_ROOT"
grep -v "^HR_LAMBDA_ARN\|^FINANCE_LAMBDA_ARN\|^ADVISOR_LAMBDA_ARN\|^MEMORY_TABLE\|^KNOWLEDGE_BUCKET" "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE"
cat >> "$ENV_FILE" <<EOF
HR_LAMBDA_ARN=$HR_ARN
FINANCE_LAMBDA_ARN=$FINANCE_ARN
ADVISOR_LAMBDA_ARN=$ADVISOR_ARN
MEMORY_TABLE=$MEMORY_TABLE
KNOWLEDGE_BUCKET=$KNOWLEDGE_BUCKET
EOF
success ".env updated with Lambda ARNs"

# ── Seed Knowledge Base ───────────────────────────────────────────────────────
info "Seeding knowledge base to S3..."
python3 "$SCRIPT_DIR/seed_knowledge.py" --bucket "$KNOWLEDGE_BUCKET" --docs-dir "$REPO_ROOT/docs"
success "Knowledge base seeded"

# ── Install CLI dependencies ──────────────────────────────────────────────────
info "Installing CLI dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet
success "CLI ready"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗"
echo -e "║  ✅  BSSE is live!                               ║"
echo -e "╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Agents deployed:"
echo -e "  ${CYAN}AVA${NC}   (HR Director)       → $HR_ARN"
echo -e "  ${GREEN}FELIX${NC} (Finance Director)  → $FINANCE_ARN"
echo -e "  ${YELLOW}ATLAS${NC} (Strategic Advisor) → $ADVISOR_ARN"
echo ""
echo -e "Start chatting:"
echo -e "  ${CYAN}python scripts/bsse.py --agent ava${NC}"
echo -e "  ${GREEN}python scripts/bsse.py --agent felix${NC}"
echo -e "  ${YELLOW}python scripts/bsse.py --agent atlas${NC}"
echo ""
