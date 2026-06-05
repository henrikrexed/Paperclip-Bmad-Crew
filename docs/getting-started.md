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

> The repository ships a portable company package (`.paperclip.yaml` + `COMPANY.md` at the root) that provisions the entire crew — personas, reporting hierarchy, and artifact-directory conventions — in a single import. Both paths use the same package; they differ only in how you get an authenticated company to import into.
>
> **One thing the import does not do: install the BMAD skill *content*.** The package references each agent's skills by their canonical keys (e.g. `bmad-code-org/bmad-method/bmad-create-prd`), but it does not bundle the skill payloads. The two core Paperclip skills (`paperclip`, `para-memory-files`) are seeded into every company automatically, but the `bmad-code-org/bmad-method/*` skills must be installed into the company once — see [Install the BMAD skills](#install-the-bmad-skills). Until you do, the import prints `references skill … but that skill is not present in the package` warnings and those agents start without their BMAD skills.

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

`--target new` creates the company **and** provisions all 10 agents in the same run — including the crew manager (`cto`). That resolves the "no company / no CTO" errors a fresh install hits. The command prints the new company's ID — copy it for the next step.

> You will see `references skill … but that skill is not present in the package` warnings for the `bmad-*` skills. That is expected on a fresh company — the skill content is installed in the next step.

### A4. Install the BMAD skills into the new company

```bash
npx paperclipai skills import https://github.com/bmad-code-org/BMAD-METHOD --company-id <new-company-id>
```

See [Install the BMAD skills](#install-the-bmad-skills) for what this does and how to confirm each agent picked up its skills. Then continue to [What the import provisions](#what-the-import-provisions).

---

## Path B — Existing org

You already run a Paperclip company with a CEO agent and a board admin. Import the BMAD crew on top of it.

```bash
git clone https://github.com/henrikrexed/Paperclip-Bmad-Crew.git
cd Paperclip-Bmad-Crew

# Make sure your CLI is authenticated as a board user (import is board-gated)
npx paperclipai auth whoami || npx paperclipai auth login

# One command: installs the BMAD skill content, then imports the crew, in order.
./setup.sh --company-id <your-company-id>
```

`setup.sh` is the supported one-command path. It installs the `bmad-*` skill content **before** the agent import — so every skill reference resolves on the first pass, with no missing-skill warnings — then runs the company import. Pass `--ceo-agent-id <your-ceo-agent-id>` to have it print the exact command to re-parent the crew under your CEO once it finishes. Run `./setup.sh --help` for all options.

<details>
<summary>Prefer to run the two steps yourself?</summary>

```bash
# Install the BMAD skill content into your company first, so the agent import
# resolves every skill reference immediately (no missing-skill warnings).
npx paperclipai skills import https://github.com/bmad-code-org/BMAD-METHOD --company-id <your-company-id>

npx paperclipai company import ./ --target existing --company-id <your-company-id> --include agents
```

Because you already have a company UUID, install the skills **before** the agent import. See [Install the BMAD skills](#install-the-bmad-skills) for details.

</details>

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
- **BMAD skill assignments** per agent — the references are wired up (see [Skills by agent](agents/index.md#skills-by-agent)); the skill *content* is installed via [Install the BMAD skills](#install-the-bmad-skills)
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

## Install the BMAD skills

The agent package references each agent's skills by their canonical keys (the authoritative list is the `skills:` block in each `agents/<slug>/AGENTS.md`). It does **not** carry the skill content itself, so the skills have to exist in the target company for the references to resolve:

- **`paperclip` and `para-memory-files`** (`paperclipai/paperclip/*`) — seeded into every company automatically by Paperclip. No action needed.
- **The `bmad-*` skills** (`bmad-code-org/bmad-method/*`) — installed once from the upstream BMAD-METHOD repository:

```bash
npx paperclipai skills import https://github.com/bmad-code-org/BMAD-METHOD --company-id <your-company-id>
```

This registers the skills under the keys the agents reference (`bmad-code-org/bmad-method/<slug>`), so resolution is by canonical key and does not depend on the company UUID.

Agent skill attachment is resolved dynamically from each agent's stored skill references, so once the skills are installed the agents pick them up on their next heartbeat. To attach them immediately, sync an agent explicitly:

```bash
# Confirm what an agent currently sees
npx paperclipai skills agent list product-manager --company-id <your-company-id>

# Force a resync after installing skills (repeat per agent slug, or just wait for the next heartbeat)
npx paperclipai skills agent sync product-manager --company-id <your-company-id>
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
