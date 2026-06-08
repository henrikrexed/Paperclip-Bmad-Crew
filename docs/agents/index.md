# BMAD Agents Overview

The BMAD template includes 9 specialized agents, each with a distinct persona, expertise domain, and role in the product development lifecycle.

## Agent Roster

| Agent | Persona | Phase | Role |
|-------|---------|-------|------|
| [Brainstormer](brainstormer.md) | Mary | Phase 1: Analysis | Business analysis, research, brainstorming |
| [Product Manager](product-manager.md) | John | Phase 2: Planning | PRDs, epics, requirements |
| [Architect](architect.md) | Winston | Phase 3: Solutioning | Architecture decisions, tech selection |
| [Story Writer](story-writer.md) | — | Phase 3/4 | Story decomposition, acceptance criteria |
| [Code Reviewer](code-reviewer.md) | Amelia | Phase 4: Implementation | Adversarial code review |
| [Testing Architect](testing-architect.md) | Amelia | Phase 4: Implementation | Test generation, coverage |
| [DevOps Engineer](devops-engineer.md) | — | Phase 3/4 | CI/CD, deployment, platform ops |
| [Challenger](challenger.md) | — | Cross-cutting | Adversarial review, edge cases |
| [O11y Engineer](o11y-engineer.md) | — | Cross-cutting | Observability, OpenTelemetry, Dynatrace |

## Skills by Agent

Each agent declares the skills it uses in the `skills:` frontmatter of its `agents/<slug>/AGENTS.md` (that is the authoritative list). The import wires these references onto each agent; the skill *content* is installed into the company separately — see [Install the BMAD skills](../getting-started.md#install-the-bmad-skills). Every agent also receives the two core Paperclip skills (`paperclip`, `para-memory-files`) in addition to the BMAD skills below.

| Agent | BMAD skills |
|-------|-------------|
| Brainstormer (Mary) | `bmad-brainstorming`, `bmad-market-research`, `bmad-domain-research`, `bmad-technical-research`, `bmad-product-brief`, `bmad-prfaq`, `bmad-document-project` |
| Product Manager (John) | `bmad-create-prd`, `bmad-validate-prd`, `bmad-edit-prd`, `bmad-create-epics-and-stories`, `bmad-check-implementation-readiness`, `bmad-correct-course` |
| Architect (Winston) | `bmad-create-architecture`, `bmad-check-implementation-readiness` |
| Story Writer | `bmad-create-story`, `bmad-create-epics-and-stories` |
| Code Reviewer (Amelia) | `bmad-code-review` |
| Testing Architect | `bmad-qa-generate-e2e-tests` |
| DevOps Engineer | Core Paperclip skills only — no first-party `bmad-*` DevOps skills exist yet; CI/CD, deploy, and platform ops are covered by the agent's `AGENTS.md` persona |
| Challenger | `bmad-review-adversarial-general`, `bmad-review-edge-case-hunter`, `bmad-editorial-review-prose`, `bmad-editorial-review-structure` |
| O11y Engineer | Core Paperclip skills only — driven by the external [`bmad-observability-agent`](https://github.com/henrikrexed/bmad-observability-agent) reference implementation (install separately) |

## Org Chart

```mermaid
graph TD
    CTO["CTO / Manager"]
    CTO --> Mary["Brainstormer<br/>(Mary)"]
    CTO --> John["Product Manager<br/>(John)"]
    CTO --> Winston["Architect<br/>(Winston)"]
    CTO --> SW["Story Writer"]
    CTO --> Amelia_CR["Code Reviewer<br/>(Amelia)"]
    CTO --> Amelia_TA["Testing Architect"]
    CTO --> DevOps["DevOps Engineer"]
    CTO --> CH["Challenger"]
    CTO --> O11y["O11y Engineer"]
```

All BMAD agents report to a CTO or engineering manager. They collaborate through structured handoffs defined in each agent's Cross-Agent Collaboration table.

## Ticket Reassignment: Who Creates Tickets for Whom

Two agents serve as critical reassignment hubs in the BMAD workflow:

### Product Manager (John) — Phase 2 → Phase 3

After completing the PRD and epics, John creates and assigns tickets to:

- **Architect (Winston)** — Architecture design ticket with PRD
- **Story Writer** — Story detailing tickets with epics
- **O11y Engineer** — Observability planning ticket (if applicable)

### Architect (Winston) — Phase 3 → Phase 4

After finalizing architecture, Winston creates and assigns tickets to:

- **Code Reviewer (Amelia)** — Implementation tickets per component
- **DevOps Engineer** — Infrastructure and CI/CD tickets
- **Testing Architect** — Test strategy tickets
- **O11y Engineer** — Instrumentation spec tickets

See the [Workflow Phases](../workflow-phases.md) page for detailed ticket flow diagrams.

## Shared Design Patterns

Every BMAD agent follows the same structural pattern in its `AGENTS.md`:

1. **Identity** — Who the agent is, their expertise, their persona
2. **Communication Style** — How they speak and interact
3. **Core Principles** — Non-negotiable rules that guide behavior
4. **BMAD Workflow Phase** — Where they sit in the 4-phase flow
5. **Capabilities** — Skill codes mapped to BMAD skills
6. **Output Conventions** — Where artifacts go and what format they use
7. **Cross-Agent Collaboration** — Explicit handoff rules

This consistency makes it easy to add new agents or modify existing ones.
