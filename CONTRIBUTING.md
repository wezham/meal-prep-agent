# Contributing

Thanks for improving Meal Prep Agent.

## Development

This repository packages agent skills. Keep changes portable across Claude Code
and Codex unless a file is explicitly product specific.

Before opening a pull request, ask your agent to verify that the JSON files are
valid, the skill can initialize from a clean checkout with no `data/local/`
directory, and no user-private data is tracked.

## Data Privacy

Do not commit personal meal history, grocery preferences, account details, or
Woolworths session data. Runtime data belongs in
`plugins/meal-prep-agent/data/local/`, which should stay private.

## Skill Changes

Keep `SKILL.md` files concise and focused on behavior the agent must follow.
Normal users should not need Python, Node, Bash, or command-line setup scripts.
