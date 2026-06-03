# Getting Started

This guide walks you through setting up a BMAD agent team on Paperclip.

## Prerequisites

- [Paperclip](https://paperclip.ing) installed and configured
- Claude Code or another supported LLM adapter
- A Paperclip company you can import into. Company import is **CEO/board-gated**, so run it as a board user or have your CEO agent run it.

## One-command setup

The repository ships a portable company package (`.paperclip.yaml` at the root) that provisions the entire crew in a single command — no manual skill installation, hierarchy wiring, or artifact-directory configuration required.

From the template directory, import into your existing company:

```bash
npx paperclipai company import ./ --target existing --company-id <your-company-id> --include agents
```

Prefer a clean slate? Create a brand-new company instead:

```bash
npx paperclipai company import ./ --target new --new-company-name "BMAD Crew"
```

### What the import provisions

One run sets up **10 agents** — a crew manager (`cto`) plus the 9 BMAD specialists — each fully wired:

- **Persona, capabilities, and collaboration rules** loaded from `agents/<slug>/AGENTS.md`
- **BMAD skill assignments** per agent (see [Skills by agent](agents/index.md#skills-by-agent))
- **Reporting hierarchy** — all 9 specialists report to the crew manager (`cto`)
- **Artifact-directory conventions** (`planningArtifacts` / `implementationArtifacts`) in each agent's metadata

```
Crew Manager (cto)
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

### Optional: attach the crew under your existing CEO

The import creates the crew manager (`cto`) at the top of the BMAD reporting tree. To slot the crew under a CEO agent you already run, point the crew manager at it after import:

```bash
npx paperclipai agent update cto --reports-to <your-ceo-agent-id>
```

### Notes on skill coverage

- Every agent also receives the two core Paperclip skills (`paperclip`, `para-memory-files`) in addition to its BMAD skills.
- The **DevOps Engineer** is provisioned with only the core Paperclip skills today: there are no first-party `bmad-*` DevOps skills in `bmad-code-org/bmad-method` yet. The agent's persona still covers CI/CD, deployment, and platform ops via its `AGENTS.md` instructions.
- The **O11y Engineer** is driven by the external [`bmad-observability-agent`](https://github.com/henrikrexed/bmad-observability-agent) reference implementation rather than standalone `bmad-*` skills. Install that agent package separately to provision its observability capabilities (pipeline configuration, instrumentation scoring, cardinality optimization, vendor validation).

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
