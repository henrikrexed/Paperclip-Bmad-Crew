# BMAD Paperclip Template

A ready-to-use [Paperclip](https://paperclip.ing) organization template implementing the **BMAD Method** (Brainstorm, Map, Architect, Deliver) — a structured product development methodology for AI agent teams.

## What's included

**8 specialized agents** covering the full product lifecycle:

| Agent | Persona | Phase | Capabilities |
|-------|---------|-------|-------------|
| Brainstormer | Mary | Analysis | 7 — research, briefs, brainstorming, PRFAQ |
| Product Manager | John | Planning | 6 — PRDs, epics, readiness checks |
| Architect | Winston | Solutioning | 2 — architecture design, readiness checks |
| Story Writer | — | Solutioning/Implementation | 2 — story decomposition, epics |
| Code Reviewer | Amelia | Implementation | 1 — adversarial code review |
| Testing Architect | Amelia | Implementation | 1 — test generation (API, E2E) |
| Challenger | — | Cross-cutting | 4 — adversarial review, edge cases, editing |
| O11y Engineer | — | Cross-cutting | 59 — OpenTelemetry, Dynatrace, observability |

**Documentation site** built with MkDocs Material theme, including:
- Getting started guide
- Workflow phase documentation
- Per-agent capability reference
- Cross-agent collaboration diagrams

## Repository structure

```
.
├── README.md                  # This file
├── mkdocs.yml                 # MkDocs configuration
├── agents/                    # Agent configurations
│   ├── brainstormer/AGENTS.md
│   ├── product-manager/AGENTS.md
│   ├── architect/AGENTS.md
│   ├── story-writer/AGENTS.md
│   ├── code-reviewer/AGENTS.md
│   ├── testing-architect/AGENTS.md
│   ├── challenger/AGENTS.md
│   └── o11y-engineer/AGENTS.md
└── docs/                      # MkDocs documentation
    ├── index.md
    ├── getting-started.md
    ├── workflow-phases.md
    ├── agents/
    │   ├── index.md
    │   ├── brainstormer.md
    │   ├── product-manager.md
    │   ├── architect.md
    │   ├── story-writer.md
    │   ├── code-reviewer.md
    │   ├── testing-architect.md
    │   ├── challenger.md
    │   └── o11y-engineer.md
    └── collaboration/
        └── index.md
```

## Quick start

### 1. Import into Paperclip

```bash
npx paperclipai import --source ./
```

### 2. Install BMAD skills

Each agent references specific BMAD skills in its Capabilities table. Install them via the Paperclip skill system.

### 3. Set up reporting hierarchy

All BMAD agents should report to a CTO or engineering manager.

### 4. Start a workflow

Assign research to the Brainstormer, then follow the phase flow: Analysis → Planning → Solutioning → Implementation.

## The BMAD workflow

```
Phase 1: Analysis        Phase 2: Planning       Phase 3: Solutioning    Phase 4: Implementation
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Brainstormer   │────▶│ Product Manager │────▶│   Architect     │────▶│  Code Reviewer  │
│  (Mary)         │     │ (John)          │     │   (Winston)     │     │  (Amelia)       │
│                 │     │                 │     │   Story Writer  │     │  Testing Arch   │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       ▲                       ▲                       ▲
        └───────────────────────┴───────────────────────┴───────────────────────┘
                                    Challenger (cross-cutting review)
                                    O11y Engineer (observability, Phase 3-4)
```

## Documentation

Build and serve the docs locally:

```bash
pip install mkdocs-material
mkdocs serve
```

Then visit `http://127.0.0.1:8000`.

## O11y Engineer reference

The Observability Agent is based on the [bmad-observability-agent](https://github.com/henrikrexed/bmad-observability-agent/blob/main/agents/o11y-engineer.md) project.

## License

This template is provided as a community resource. See individual skill repositories for their respective licenses.
