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
npx paperclipai company import ./ --include company,agents,skills --target existing --company-id <your-company-id>
```

Or manually create each agent through the Paperclip CLI:

```bash
npx paperclipai agent create \
  --company-id <your-company-id> \
  --name "Brainstormer" \
  --title "BMAD Brainstormer" \
  --role engineer \
  --adapter-type hermes_local \
  --instructions-path agents/brainstormer/AGENTS.md
```

### 2. Install BMAD skills

Each agent needs specific BMAD skills installed. The skill mappings are defined in each agent's `AGENTS.md` file under the Capabilities table.

Current Paperclip/BMAD guidance is to **reuse BMAD as skills** rather than reimplementing BMAD behavior inside every Paperclip agent:

1. Link or copy the official BMAD Method repository into Paperclip as a skill source.
2. Create specialized Paperclip agents from this template.
3. Attach the relevant BMAD skills to each agent. Paperclip filters available skills by each agent's capability list.
4. Refresh the Paperclip skill source manually or with auto-sync when the BMAD Method repository changes.

Recommended local layout:

```text
<workspace>/BMAD-METHOD/                 # official BMAD Method checkout
<workspace>/Paperclip-Bmad-Crew/         # this Paperclip organization template
<workspace>/Paperclip-Bmad-Crew/_bmad/   # project-level BMAD config and overrides
```

!!! note "Source guidance"
    GitHub discussion [paperclipai/paperclip#4972](https://github.com/paperclipai/paperclip/discussions/4972) recommends linking BMAD Method as skills, letting Paperclip filter skills automatically, refreshing skills when BMAD updates, and adding a config file for paths, language preferences, and output directories. This template includes that project config under `_bmad/bmm/config.yaml`.

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

### 4. Configure BMAD paths and customization

BMAD agents write output to standardized directories. Configure these in `_bmad/bmm/config.yaml`:

- `{planning_artifacts}/` — PRDs, architecture docs, research, epics
- `{implementation_artifacts}/` — Story files, test summaries
- `{implementation_artifacts}/infra/` — Infrastructure code, CI/CD configs
- `{project_knowledge}/` — Long-lived docs, research, and references

This template provides the expected BMAD project structure:

```text
_bmad/bmm/config.yaml                    # project paths, languages, Paperclip IDs
_bmad/scripts/resolve_customization.py   # merges skill + project custom TOML
_bmad/custom/                            # team/personal skill overrides
_bmad-output/planning-artifacts/         # Phase 1-3 outputs
_bmad-output/implementation-artifacts/   # Phase 4 outputs
```

Update `_bmad/bmm/config.yaml` after cloning if your company ID, agent IDs, preferred language, or output folders differ. Keep secrets out of this file; use Paperclip secrets or environment variables for API keys.

If you also want BMAD CLI-managed local skills for an IDE, run the official installer against this repository and point it at the same folders:

```bash
npx bmad-method install \
  --directory . \
  --modules bmm \
  --tools claude-code,codex \
  --user-name "Paperclip team" \
  --communication-language English \
  --set core.project_name=Paperclip-Bmad-Crew \
  --set core.output_folder=_bmad-output \
  --set bmm.planning_artifacts=_bmad-output/planning-artifacts \
  --set bmm.implementation_artifacts=_bmad-output/implementation-artifacts \
  --set bmm.project_knowledge=docs
```

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
