# pair-programmer

A live, conversational technical collaborator for this repo, reachable from Telegram — the closest thing to this Claude Code / Cursor conversation, but running through Hermes in its own forum topic. Not a planning/dispatch pipeline like Builder OS: no Work Orders, no `claude -p` subprocess dispatch, no fixed branches. It reads and edits files directly, in the conversation, and commits after describing the change and getting confirmation — same as pairing with someone over chat.

Use Builder OS (`builder-os/`, "🔧 Builder OS" topic) instead when you want a structured, tracked, independently-verified Work Order with a paper trail. Use this when you want to explore the codebase, debate an approach, or make a change live without that ceremony.

## Setup

1. Create a new forum topic in the existing Telegram supergroup (e.g. "🧑‍💻 Pair Programmer").
2. Register it in Hermes's `telegram.extra.group_topics` config, alongside Venture Studio's and Builder OS's entries, with `skill: pair-programmer`.
3. Register `pair-programmer/skills` in Hermes's `skills.external_dirs`.
4. For the intended experience (Claude doing the actual reasoning, not a free/cheap default model), point this topic's model at your Claude Code subscription credentials: send `/model claude-code --session` in the new topic once it's live. This works if `claude` CLI on the machine running Hermes is already logged in via subscription (not an API key) — check `~/.claude/.credentials.json` exists and holds `claudeAiOauth` fields, not a bare key.

No Supabase table, no new scripts — this skill has no persistence needs beyond the repo's own git history and Hermes's own conversation history.

## Structure

```
pair-programmer/
└── skills/pair-programmer/
    └── SKILL.md    # grounding, editing, and git-confirmation rules
```
