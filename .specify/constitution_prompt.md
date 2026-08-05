---
description: Create or update the project specification guidelines and core principles (constitution.md).
---

The update action must be cautious and rigorous; update the file ONLY when absolutely necessary, otherwise keep the original file unchanged.

## Core Rules

1. **Scope Limit**: This command ONLY updates `specs/constitution.md` . Do NOT create, modify, or delete any application source code or tests.
2. **Writing Guidelines**:
   - Fill in or update all placeholders (e.g., `[PROJECT_NAME]`, `[PRINCIPLE_X_NAME]`) based on user input or existing repository context. Remove unused principle blocks.
   - Principles MUST be explicit, testable, and non-negotiable (use standard RFC 2119 terms like MUST, SHOULD, MUST NOT).
   - Provide a brief rationale for each principle.
   - Update `LAST_AMENDED_DATE` to today's date and increment `CONSTITUTION_VERSION` appropriately (default to 1.0.0 for new creations).
3. **Output**: Briefly summarize the amended principles, updated version, and suggested commit message after saving.