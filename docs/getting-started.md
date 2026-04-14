# Getting Started

This guide walks you through setting up a BMAD agent team on Paperclip.

## Prerequisites

- [Paperclip](https://paperclip.ing) installed and configured
- Claude Code or another supported LLM adapter
- A Paperclip company created

## Installation

### 1. Import the template

Use Paperclip's company import to set up the BMAD organization:

```bash
# From the template directory
npx paperclipai import --source ./
```

Or manually create each agent through the Paperclip CLI:

```bash
npx paperclipai agent create \
  --name "Brainstormer" \
  --title "BMAD Brainstormer" \
  --role engineer \
  --instructions-path agents/brainstormer/AGENTS.md
```

### 2. Install BMAD skills

Each agent needs specific BMAD skills installed. The skill mappings are defined in each agent's `AGENTS.md` file under the Capabilities table.

Core BMAD skills to install:

| Skill | Used by |
|-------|---------|
| `bmad-brainstorming` | Brainstormer |
| `bmad-market-research` | Brainstormer |
| `bmad-domain-research` | Brainstormer |
| `bmad-technical-research` | Brainstormer |
| `bmad-product-brief` | Brainstormer |
| `bmad-prfaq` | Brainstormer |
| `bmad-document-project` | Brainstormer |
| `bmad-create-prd` | Product Manager |
| `bmad-validate-prd` | Product Manager |
| `bmad-edit-prd` | Product Manager |
| `bmad-create-epics-and-stories` | Product Manager, Story Writer |
| `bmad-check-implementation-readiness` | Product Manager, Architect |
| `bmad-correct-course` | Product Manager |
| `bmad-create-architecture` | Architect |
| `bmad-create-story` | Story Writer |
| `bmad-code-review` | Code Reviewer |
| `bmad-qa-generate-e2e-tests` | Testing Architect |
| `bmad-review-adversarial-general` | Challenger |
| `bmad-review-edge-case-hunter` | Challenger |
| `bmad-editorial-review-prose` | Challenger |
| `bmad-editorial-review-structure` | Challenger |

### 3. Set up the reporting hierarchy

BMAD agents should report to a CTO or engineering manager. Example hierarchy:

```
CEO
  └── CTO
        ├── Brainstormer (Mary)
        ├── Product Manager (John)
        ├── Architect (Winston)
        ├── Story Writer
        ├── Code Reviewer (Amelia)
        ├── Testing Architect
        ├── DevOps Engineer
        ├── Challenger
        └── O11y Engineer
```

### 4. Configure artifact directories

BMAD agents write output to standardized directories. Configure these in your project:

- `{planning_artifacts}/` — PRDs, architecture docs, research, epics
- `{implementation_artifacts}/` — Story files, test summaries
- `{implementation_artifacts}/infra/` — Infrastructure code, CI/CD configs

These paths are referenced in each agent's Output Conventions section.

## Your first BMAD workflow

Here's what a typical project looks like from start to finish, showing how tickets flow between agents:

1. **Start with research.** Assign a task to the Brainstormer asking for market research or a product brief. Mary produces briefs and research reports.

2. **Create a PRD.** When Mary finishes, she creates a ticket and assigns it to the Product Manager. John takes the brief and produces a PRD through facilitated steps, then creates the epics listing.

3. **Design architecture.** John creates an architecture ticket and assigns it to the Architect. Winston reads the PRD and produces architecture decisions through his 8-step workflow.

4. **Write stories.** John also creates story tickets for the Story Writer, who decomposes epics into implementation-ready stories with acceptance criteria.

5. **Implement and review.** Winston creates implementation tickets for the Code Reviewer and testing tickets for the Testing Architect. Amelia reviews code with adversarial rigor. The Testing Architect generates comprehensive test suites.

6. **Set up infrastructure.** Winston creates infrastructure tickets for the DevOps Engineer, who handles CI/CD pipelines, deployment automation, and platform configuration.

7. **Add observability.** The O11y Engineer receives tickets from both the Product Manager (observability requirements) and the Architect (instrumentation specs), then implements monitoring, tracing, and alerting.

At any point, agents can create review tickets for the Challenger, who reviews artifacts for gaps and edge cases.

!!! tip "Key insight: agents create tickets for each other"
    Work doesn't magically appear in an agent's queue. Each agent is responsible for creating and assigning tickets to the next agent in the chain. This is what makes BMAD traceable — every handoff is an explicit ticket.

## Customization

Each agent's `AGENTS.md` is self-contained. You can:

- Modify personas and communication styles
- Add or remove capabilities
- Adjust collaboration patterns
- Add new agents that follow the same structure

The BMAD method is flexible — adapt it to your team's needs.
