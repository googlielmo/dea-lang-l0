# Gemini Instructions

## Core Directives

- **Primary Source of Truth:** Refer to [CLAUDE.md](./CLAUDE.md) for all project-specific rules, coding standards, and
  constraints.
- **Language:** Use English for all reasoning, variable names, comments, and documentation.
- **Tone:** Be concise and technical. Do not explain basic programming concepts or patterns.

## Contextual Guardrails

- **Workspace Awareness:** Use integrated tools to validate changes against the codebase structure defined in the
  primary docs.
- **Agentic Behavior:** When in `--yolo` mode, ensure all actions align with the "Definition of Done" in `CLAUDE.md`.
- **Testing:** Always run relevant tests after making changes, following the guidelines in [CLAUDE.md](./CLAUDE.md).
