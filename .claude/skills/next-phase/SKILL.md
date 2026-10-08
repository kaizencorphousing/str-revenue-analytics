---
name: next-phase
description: Build one phase of the STR analytics project from docs/SPEC.md, verify it, log progress, commit, and teach the concept
disable-model-invocation: true
---
Build phase $ARGUMENTS of this project.

1. Read `docs/PROGRESS.md` and the "Phase $ARGUMENTS" section of `docs/SPEC.md`. If an earlier phase isn't marked done, stop and tell me.
2. Write a short plan: files you'll create or change, how you'll verify it, and anything in the spec you think is wrong or risky. Wait for my approval before writing code.
3. Build it. Run everything you write.
4. Prove the phase's "Done when" criteria with real command output.
5. Use the spec-reviewer subagent to check the work against the phase's section of the spec. Fix gaps that affect correctness or the spec; list the rest as optional.
6. Update `docs/PROGRESS.md` (status, decisions, open issues) and add this phase's section to `docs/LEARNING_NOTES.md`.
7. Commit with a clear message (the PII guard hook runs automatically).
8. End with: what was built, the evidence it works, the main concept in 3 to 5 plain sentences, and one question I should be able to answer about it in an interview. Then stop and tell me to run `/clear` before the next phase.
