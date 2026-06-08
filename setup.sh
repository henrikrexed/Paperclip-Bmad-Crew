#!/usr/bin/env bash
#
# Turnkey onboarding for the BMAD Paperclip crew.
#
# Runs the two steps that provision a fully working crew into an existing
# Paperclip company, in the right order:
#   1. Install the BMAD skill *content* from upstream BMAD-METHOD, so every
#      agent's skill references resolve with no missing-skill warnings.
#   2. Import the company package (all 10 agents + reporting hierarchy +
#      artifact-directory conventions + skill references).
#
# Usage:
#   ./setup.sh --company-id <your-company-id> [options]
#   PAPERCLIP_COMPANY_ID=<id> ./setup.sh
#
# Options:
#   --company-id <id>     Target Paperclip company UUID (or set PAPERCLIP_COMPANY_ID).
#   --ceo-agent-id <id>   If set, prints the exact command to re-parent the crew
#                         manager (cto) under your existing CEO agent.
#   --skills-repo <url>   Override the BMAD skills source repo
#                         (default: https://github.com/bmad-code-org/BMAD-METHOD).
#   -h, --help            Show this help and exit.
#
# Prerequisites:
#   - paperclipai CLI available via npx (npm install -g paperclipai)
#   - CLI authenticated as a board user (company import is board-gated):
#       npx paperclipai auth login
#   - An existing Paperclip company. Fresh install with no company yet? See
#     Path A in docs/getting-started.md to bootstrap the instance and create
#     the company first.

set -euo pipefail

SKILLS_REPO="https://github.com/bmad-code-org/BMAD-METHOD"
COMPANY_ID="${PAPERCLIP_COMPANY_ID:-}"
CEO_AGENT_ID=""

usage() {
  cat <<'EOF'
Turnkey onboarding for the BMAD Paperclip crew.

Runs the two onboarding steps in the right order:
  1. Install the BMAD skill content from upstream BMAD-METHOD, so every
     agent's skill references resolve with no missing-skill warnings.
  2. Import the company package (all 10 agents + reporting hierarchy +
     artifact-directory conventions + skill references).

Usage:
  ./setup.sh --company-id <your-company-id> [options]
  PAPERCLIP_COMPANY_ID=<id> ./setup.sh

Options:
  --company-id <id>     Target Paperclip company UUID (or set PAPERCLIP_COMPANY_ID).
  --ceo-agent-id <id>   If set, prints the exact command to re-parent the crew
                        manager (cto) under your existing CEO agent.
  --skills-repo <url>   Override the BMAD skills source repo
                        (default: https://github.com/bmad-code-org/BMAD-METHOD).
  -h, --help            Show this help and exit.

Prerequisites:
  - paperclipai CLI available via npx (npm install -g paperclipai)
  - CLI authenticated as a board user (company import is board-gated):
      npx paperclipai auth login
  - An existing Paperclip company. Fresh install with no company yet? See
    Path A in docs/getting-started.md to bootstrap the instance first.
EOF
  exit "${1:-0}"
}

die() {
  echo "error: $*" >&2
  echo "Run './setup.sh --help' for usage." >&2
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --company-id)   COMPANY_ID="${2:-}"; shift 2 ;;
    --company-id=*) COMPANY_ID="${1#*=}"; shift ;;
    --ceo-agent-id)   CEO_AGENT_ID="${2:-}"; shift 2 ;;
    --ceo-agent-id=*) CEO_AGENT_ID="${1#*=}"; shift ;;
    --skills-repo)   SKILLS_REPO="${2:-}"; shift 2 ;;
    --skills-repo=*) SKILLS_REPO="${1#*=}"; shift ;;
    -h|--help) usage 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ -n "$COMPANY_ID" ] || die "missing --company-id (or PAPERCLIP_COMPANY_ID). This is the UUID of the company to provision into."

if ! command -v npx >/dev/null 2>&1; then
  die "npx not found. Install Node.js, then 'npm install -g paperclipai'."
fi

# Run from the package root so 'company import ./' resolves the .paperclip.yaml here.
cd "$(dirname "$0")"
[ -f ".paperclip.yaml" ] || die "could not find .paperclip.yaml next to setup.sh — run this script from inside the cloned repo."

echo "==> BMAD crew onboarding for company: $COMPANY_ID"
echo

echo "==> Step 1/2: installing BMAD skill content from $SKILLS_REPO"
npx paperclipai skills import "$SKILLS_REPO" --company-id "$COMPANY_ID"
echo

echo "==> Step 2/2: importing the crew (10 agents + hierarchy + skill references)"
npx paperclipai company import ./ --target existing --company-id "$COMPANY_ID" --include agents
echo

echo "==> Done. The crew is provisioned and every skill reference resolves."
echo
echo "Next steps:"
if [ -n "$CEO_AGENT_ID" ]; then
  echo "  • Attach the crew under your existing CEO:"
  echo "      npx paperclipai agent update cto --reports-to $CEO_AGENT_ID --company-id $COMPANY_ID"
else
  echo "  • (Optional) Attach the crew under your existing CEO agent:"
  echo "      npx paperclipai agent update cto --reports-to <your-ceo-agent-id> --company-id $COMPANY_ID"
fi
echo "  • Kick off the first workflow by assigning a research task to the Brainstormer:"
echo "      npx paperclipai issue create \\"
echo "        --company-id $COMPANY_ID \\"
echo "        --title \"Research: <your topic>\" \\"
echo "        --description \"Conduct market research and produce a product brief.\" \\"
echo "        --assignee-agent-id <brainstormer-agent-id> \\"
echo "        --status todo"
