# BMAD Skills Manifest

This template **references** skills by their canonical keys in each agent's
`agents/<slug>/AGENTS.md` frontmatter — it does **not** vendor (copy) any skill
content into this repo.

The `bmad-*` skill bodies are installed from the upstream
[BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) repo at setup time by
`setup.sh` (step 1: `npx paperclipai skills import <BMAD-METHOD>`). The
`paperclipai/paperclip/*` skills ship with the Paperclip platform itself.

> **Why no vendoring?** Copying upstream skill payloads would create an IP /
> licensing surface and a staleness risk (the in-repo copy drifts from upstream).
> Installing from upstream at setup time keeps the source of truth singular and
> current. This manifest exists purely for **discoverability** — so the repo no
> longer looks "empty" — while keeping the source of truth upstream.

The tables below are the authoritative list, derived directly from the
`agents/*/AGENTS.md` frontmatter and validated against the company skills catalog
(0 invalid keys across all 10 agents).

---

## BMAD skills installed from upstream

Every `bmad-*` skill referenced by an agent. All are installed by `setup.sh` from
upstream `bmad-code-org/bmad-method`.

| Skill key | Purpose |
|-----------|---------|
| `bmad-code-org/bmad-method/bmad-brainstorming` | Facilitate interactive brainstorming sessions using diverse creative techniques and ideation methods. |
| `bmad-code-org/bmad-method/bmad-market-research` | Conduct market research on competition and customers. |
| `bmad-code-org/bmad-method/bmad-domain-research` | Conduct domain and industry research for a topic or industry. |
| `bmad-code-org/bmad-method/bmad-technical-research` | Conduct technical research on technologies and architecture; produce a technical research report. |
| `bmad-code-org/bmad-method/bmad-product-brief` | Create or update product briefs through guided or autonomous discovery. |
| `bmad-code-org/bmad-method/bmad-prfaq` | Working Backwards PRFAQ challenge to forge product concepts. |
| `bmad-code-org/bmad-method/bmad-document-project` | Document brownfield projects for AI context. |
| `bmad-code-org/bmad-method/bmad-create-prd` | Create a PRD from scratch. |
| `bmad-code-org/bmad-method/bmad-validate-prd` | Validate a PRD against standards. |
| `bmad-code-org/bmad-method/bmad-edit-prd` | Edit an existing PRD. |
| `bmad-code-org/bmad-method/bmad-create-epics-and-stories` | Break requirements into epics and user stories. |
| `bmad-code-org/bmad-method/bmad-create-story` | Create a dedicated story file with all the context needed to implement it later. |
| `bmad-code-org/bmad-method/bmad-correct-course` | Manage significant changes during sprint execution ("correct course" / "propose sprint change"). |
| `bmad-code-org/bmad-method/bmad-check-implementation-readiness` | Validate that PRD, UX, Architecture and Epics specs are complete. |
| `bmad-code-org/bmad-method/bmad-create-architecture` | Create architecture solution design decisions for AI agent consistency. |
| `bmad-code-org/bmad-method/bmad-code-review` | Review code changes adversarially using parallel review layers, with structured triage into actionable categories. |
| `bmad-code-org/bmad-method/bmad-qa-generate-e2e-tests` | Generate end-to-end automated tests for existing features. |
| `bmad-code-org/bmad-method/bmad-review-adversarial-general` | Perform a cynical review and produce a findings report. |
| `bmad-code-org/bmad-method/bmad-review-edge-case-hunter` | Walk every branching path and boundary condition; report only unhandled edge cases. |
| `bmad-code-org/bmad-method/bmad-editorial-review-prose` | Clinical copy-editor that reviews text for communication issues. |
| `bmad-code-org/bmad-method/bmad-editorial-review-structure` | Structural editor that proposes cuts, reorganization, and simplification while preserving comprehension. |

**Source:** [github.com/bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)
(installed by `setup.sh`, overridable with `--skills-repo`).

---

## Per-agent skill mapping

Which skills each agent declares, taken verbatim from `agents/<slug>/AGENTS.md`
frontmatter. Every agent also gets the two platform `paperclipai/paperclip/*`
skills (`paperclip`, `para-memory-files`); only the role-specific additions are
listed in the "Additional skills" column.

| Agent (slug) | Title | Additional skills (beyond `paperclip` + `para-memory-files`) |
|--------------|-------|--------------------------------------------------------------|
| `brainstormer` | BMAD Brainstormer (Mary) | `bmad-brainstorming`, `bmad-market-research`, `bmad-domain-research`, `bmad-technical-research`, `bmad-product-brief`, `bmad-prfaq`, `bmad-document-project` |
| `product-manager` | BMAD Product Manager (John) | `bmad-create-prd`, `bmad-validate-prd`, `bmad-edit-prd`, `bmad-create-epics-and-stories`, `bmad-check-implementation-readiness`, `bmad-correct-course` |
| `architect` | BMAD Architect (Winston) | `bmad-create-architecture`, `bmad-check-implementation-readiness` |
| `story-writer` | BMAD Story Writer | `bmad-create-story`, `bmad-create-epics-and-stories` |
| `code-reviewer` | BMAD Code Reviewer (Amelia) | `bmad-code-review` |
| `testing-architect` | BMAD Testing Architect | `bmad-qa-generate-e2e-tests` |
| `challenger` | BMAD Challenger | `bmad-review-adversarial-general`, `bmad-review-edge-case-hunter`, `bmad-editorial-review-prose`, `bmad-editorial-review-structure` |
| `cto` | BMAD Crew Manager | `paperclipai/paperclip/paperclip-create-agent` |
| `devops-engineer` | BMAD DevOps Engineer | _(platform skills only)_ |
| `o11y-engineer` | BMAD O11y Engineer | _(platform skills only)_ |

> Skill keys above are shown short (e.g. `bmad-brainstorming`); the AGENTS.md
> frontmatter uses the fully-qualified key
> `bmad-code-org/bmad-method/bmad-brainstorming`. The `cto` adds the platform
> skill `paperclipai/paperclip/paperclip-create-agent` (not a `bmad-*` skill).

---

## How installation works

`setup.sh` runs two ordered steps against your company:

1. **Install skill content** — `npx paperclipai skills import <BMAD-METHOD>` pulls
   every `bmad-*` skill body from upstream into your company, so the references
   below resolve with no missing-skill warnings.
2. **Import the crew** — `npx paperclipai company import ./ --include agents`
   creates the 10 agents with the per-agent skill references listed here.

Running the skill install first means every reference resolves on the first pass.
See the repo [README](README.md) and the
[Getting Started guide](https://henrikrexed.github.io/Paperclip-Bmad-Crew/getting-started/)
for the full onboarding flow.
