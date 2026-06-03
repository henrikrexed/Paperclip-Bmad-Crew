# Getting Started

This guide walks you through setting up a BMAD agent team on Paperclip.

## Prerequisites

- [Paperclip](https://paperclip.ing) installed (`npm install -g paperclipai`)
- Claude Code or another supported LLM adapter

## Pick your starting point

The setup steps depend on whether you already have a Paperclip company. Company import is **CEO/board-gated**, so you must run it as an authenticated board user (or have a CEO agent run it). On a brand-new install there is no company, no board admin, and no agents yet — that's the first thing we fix.

| Your situation | Go to |
|----------------|-------|
| Fresh Paperclip install — no company, no CEO/CTO yet | **[Path A — Empty instance](#path-a-empty-instance)** |
| You already run a Paperclip company with a CEO | **[Path B — Existing org](#path-b-existing-org)** |

> The repository ships a portable company package (`.paperclip.yaml` + `COMPANY.md` at the root) that provisions the entire crew in a single import — no manual skill installation, hierarchy wiring, or artifact-directory configuration required. Both paths use the same package; they differ only in how you get an authenticated company to import into.

---

## Path A — Empty instance

A fresh Paperclip install has no company, no board admin, and no agents. Trying to import straight away fails because there is nothing to authenticate as and nothing to import into. Bootstrap the instance first, then create the company and crew in one import.

### A1. Start the instance and claim the first admin

```bash
# Bootstrap local config, run health checks, and start Paperclip
npx paperclipai run

# In a second terminal: mint a one-time invite to claim the first instance admin
npx paperclipai auth bootstrap-ceo
```

`auth bootstrap-ceo` prints a one-time invite URL. Open it in your browser and claim the first **board admin** account — this human account is the top-level owner ("CEO") of your instance. (Re-run with `--force` only if you need to issue a fresh invite after an admin already exists.)

### A2. Authenticate the CLI as that board user

```bash
npx paperclipai auth login
npx paperclipai auth whoami   # confirm you are logged in as the board admin
```

Import is board-gated, so the CLI must be logged in before the next step works.

### A3. Create the company and the whole crew in one import

```bash
git clone https://github.com/henrikrexed/Paperclip-Bmad-Crew.git
cd Paperclip-Bmad-Crew

npx paperclipai company import ./ --target new --new-company-name "BMAD Crew" --include agents
```

`--target new` creates the company **and** provisions all 10 agents in the same run — including the crew manager (`cto`). That resolves the "no company / no CTO" errors a fresh install hits. Skip ahead to [What the import provisions](#what-the-import-provisions).

---

## Path B — Existing org

You already run a Paperclip company with a CEO agent and a board admin. Import the BMAD crew on top of it.

```bash
git clone https://github.com/henrikrexed/Paperclip-Bmad-Crew.git
cd Paperclip-Bmad-Crew

# Make sure your CLI is authenticated as a board user (import is board-gated)
npx paperclipai auth whoami || npx paperclipai auth login

npx paperclipai company import ./ --target existing --company-id <your-company-id> --include agents
```

By default the imported crew manager (`cto`) sits at the top of the BMAD reporting tree with `reportsTo: null`. To slot the whole crew **under your existing CEO**, edit `agents/cto/AGENTS.md` before importing and set the `reportsTo:` frontmatter field to your CEO agent's slug:

```yaml
---
kind: agent
slug: cto
name: "Crew Manager"
reportsTo: "ceo"   # ← your existing CEO agent's slug
---
```

The 9 specialists already point at `cto` via their own `reportsTo:` frontmatter, so re-parenting the crew manager moves the entire tree.

---

## What the import provisions

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

By default the crew manager (`cto`) sits at the top of the reporting tree. If you want to attach the crew under a CEO agent you already run, see the `reportsTo:` edit in [Path B](#path-b-existing-org) — do this **before** importing.

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
