# AGENTS.md

## Required Repository Instructions

Before working in this repository, read and follow
[`.github/copilot-instructions.md`](.github/copilot-instructions.md) in full. It is
the detailed source of truth for the project's architecture, conventions,
workflows, validation, and response expectations.

Keep this file as the repository entry point for agents. Keep detailed project
guidance in `.github/copilot-instructions.md` so the instructions do not drift
between multiple files.

## Repository Skills

Repository-specific skills live under `.github/skills/`. Before taking action,
check whether the task matches a skill. When it does:

1. Read the matching `SKILL.md` completely before changing or reviewing code.
2. Follow any references that the skill identifies as relevant to the task.
3. State briefly that the skill is being used and why.

Use skills together with the repository instructions. If generic skill guidance
conflicts with this project's established architecture or conventions, follow
`.github/copilot-instructions.md` and the existing codebase unless the user
explicitly requests a change in direction.

### FastAPI Skill (Required)

You **must** load and use [`.github/skills/fastapi/SKILL.md`](.github/skills/fastapi/SKILL.md)
for any task that creates, changes, reviews, debugs, or advises on:

- FastAPI applications, routers, path operations, or API behavior
- Pydantic request/response models or API validation
- FastAPI dependencies, authentication dependencies, or dependency injection
- Response models, serialization, errors, streaming, or Server-Sent Events
- Serving frontend/static applications through FastAPI
- Tests or refactors involving any of the FastAPI concerns above

This requirement applies even when the FastAPI-related change is small or is
only one part of a larger task.

### Other Skills

Use other skills under `.github/skills/` whenever their `name` and `description`
match the task. For example, load
`.github/skills/multi-stage-dockerfile/SKILL.md` when creating or revising a
multi-stage Dockerfile.
