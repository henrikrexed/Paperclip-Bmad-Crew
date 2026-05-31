# Testing Quality Standard: Red/Green TDD + ReqNRoll BDD

Scope: company standard for new features, bug fixes, and behavior changes. Product-feature implementation is out of scope for this artifact.

Source alignment:
- `README.md`: BMAD ticket-driven handoffs and quality gates.
- `docs/agents/story-writer.md`: Story Writer uses Given/When/Then acceptance criteria.
- `docs/agents/testing-architect.md`: Testing Architect owns API/E2E/integration test generation and pass verification.
- `/home/cweber/BMAD-METHOD/src/bmm-skills/4-implementation/bmad-qa-generate-e2e-tests/SKILL.md`: QA workflow detects existing framework, writes API/E2E tests, runs tests, and records summary.

## Mandatory guardrails

1. **Red first**
   - Before any production code change for a feature or bug, create at least one failing automated test or failing ReqNRoll `.feature` scenario.
   - Run the narrow test command and capture failure output.
   - Failure must prove missing/incorrect behavior, not syntax, fixture, or environment error.

2. **Green minimal**
   - Change only enough production code to pass the failing test/scenario.
   - Run the same narrow command and capture passing output.
   - Run impacted suite(s) before handoff.

3. **Refactor after green only**
   - Refactor only while tests remain green.
   - Record refactor notes or `none`.

4. **No red evidence, no production diff**
   - If production code changed before red evidence exists, revert/delete that code and restart from a failing test/scenario.

## ReqNRoll BDD standard

1. ReqNRoll is required for behavior-level acceptance coverage on stories and SMART goals.
2. `.feature` files must use `Feature`, `Rule` when helpful, and `Scenario`/`Scenario Outline` with `Given`, `When`, `Then` steps.
3. Scenario wording must match story acceptance criteria intent. Keep product terms from the story.
4. Step definitions must exercise public behavior through application/API boundaries where feasible. Avoid asserting private implementation details.
5. Each acceptance criterion must map to at least one ReqNRoll scenario or to an explicit non-BDD automated test with rationale.

## Given/When/Then requirements

Required for:
- SMART goals.
- Story acceptance criteria.
- ReqNRoll `.feature` scenarios.
- Bug reproduction notes when a bug fix starts.

Template:

```gherkin
Feature: <capability>

  Scenario: <observable behavior>
    Given <precondition from story/customer context>
    When <user/system action>
    Then <observable outcome>
```

## Minimum test coverage per coding task

- Unit: domain rules, boundaries, validation, error cases.
- API/integration when endpoints/services exist: success status, `400`, `404`, and forced/controlled `500` path where practical; response shape; side effects.
- ReqNRoll BDD: acceptance criteria and primary user/system workflows.
- E2E/UI when UI exists: semantic locators only (`role`, `label`, visible text), user actions, visible outcome assertions.

## Coding handoff evidence template

Every implementation handoff must include:

```markdown
## Verification Evidence

Red evidence:
- Test/scenario: `<path>::<test-id>` or `<feature-file>:<scenario>`
- Command: `<exact command>`
- Result: expected failure captured before production code change
- Failure excerpt: `<error/assertion excerpt>`

Green evidence:
- Command: `<exact command>`
- Result: pass
- Output excerpt: `<pass summary>`

Impacted suite evidence:
- Command: `<exact command>`
- Result: pass
- Output excerpt: `<pass summary>`

ReqNRoll coverage:
- Feature file(s): `<path>`
- Scenario(s): `<scenario names>`
- Acceptance criteria mapped: `<AC ids>`

Refactor notes:
- `<notes>` or `none`

Known gaps / follow-ups:
- `<gap + owner + ticket>` or `none`
```

## Acceptance gate

A task may move to review only when:
- failing test/ReqNRoll scenario existed before production code changes;
- Given/When/Then acceptance criteria are present and mapped;
- red, green, impacted-suite command output is recorded;
- refactor notes are recorded;
- all generated and impacted tests pass.
