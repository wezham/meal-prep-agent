# Contributing

Thanks for improving Meal Prep Agent.

## Development

This repository packages agent skills and a small Python helper. Keep changes
portable across Claude Code and Codex unless a file is explicitly product
specific.

Before opening a pull request:

```bash
python3 plugins/meal-prep-agent/scripts/memory.py summary
python3 -m json.tool plugins/meal-prep-agent/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/meal-prep-agent/data/profile.template.json >/dev/null
python3 -m json.tool plugins/meal-prep-agent/data/history.template.json >/dev/null
```

## Data Privacy

Do not commit personal meal history, grocery preferences, account details, or
Woolworths session data. Runtime data belongs in
`plugins/meal-prep-agent/data/local/` or in a directory configured by
`MEAL_PREP_AGENT_DATA_DIR`; both should stay private.

## Skill Changes

Keep `SKILL.md` files concise and focused on behavior the agent must follow.
Prefer scripts for deterministic file updates and references only when the
workflow needs additional context.
