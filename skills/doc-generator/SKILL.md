---
name: doc-generator
description: Generate technical documentation including API docs, architecture decision records (ADRs), runbooks, changelogs, and technical specifications. Use this skill whenever someone asks to write documentation, create an ADR, generate API docs, write a runbook, or says things like "document this API", "write an ADR for X", "create a runbook for Y", "generate the tech spec", "write the changelog entry", "update the docs", or "we need documentation for this feature". Also trigger when someone mentions architecture decision recording, technical specification writing, or operational runbook creation.
model: sonnet
context: fork
---

# Documentation Generator

## Supported Document Types

Seven templates, and a task needs exactly one. They live in references so that writing a changelog
does not also load the retrospective, the runbook, and the change-management procedure:

| You are writing | Read |
|---|---|
| Architecture Decision Record (ADR) | `references/design-docs.md` |
| Technical Specification | `references/design-docs.md` |
| API Endpoint Documentation | `references/operational-docs.md` |
| Runbook | `references/operational-docs.md` |
| Changelog Entry | `references/process-docs.md` |
| Sprint / Project Retrospective | `references/process-docs.md` |
| Change Management Procedure | `references/process-docs.md` |
| Model / table documentation | `references/doc-templates.md` |

## Generation Protocol

1. Identify the document type needed, and read **only** its reference from the table above.
2. Gather information by reading the relevant code files.
3. Apply that template.
4. Fill in details from code analysis — **cite the file you read for each claim**.
5. Highlight gaps and open questions explicitly.
6. Output the complete document.

## Do not document what you did not read

This applies to every document type, which is why it is here rather than in a reference.

Documentation is believed. That is its entire function, and it is why a plausible invention here is
more expensive than in code: a wrong endpoint parameter fails loudly the first time someone calls
it, but a wrong runbook step fails at 3am, and a fabricated ADR rationale is cited for years by
people who reasonably assume someone checked.

So: every statement of fact traces to a file you opened. If you could not determine something —
the retry policy, the error codes, who approves this change — write **"Unknown: <question>"** and
leave it. An explicit gap gets filled by the person who knows. A confident guess in the same slot
never gets questioned, because it does not look like a gap.

If the material would have to come from outside this repository (a vendor's SLA, a price, a
competitor's approach), you do not have it — say so and name who does.
