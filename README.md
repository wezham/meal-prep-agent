# Meal Prep Agent

Meal Prep Agent is an open-source, cross-agent plugin for weekly meal prep
planning. It packages portable `SKILL.md` workflows so the same workflows can
be used from Claude Code and Codex without requiring users to install Python,
Node, Bash scripts, or any other helper runtime.

The plugin can:

- generate 3 lunches and 3 dinners from 2 batch recipes
- combine ingredients into one grocery list
- produce concise batch-cooking instructions
- avoid recent repeats with private local meal history
- find Woolworths Australia product links with confidence notes
- prepare a Woolworths cart review workflow without checking out

## Repository Layout

```text
.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
plugins/meal-prep-agent/
  .codex-plugin/plugin.json
  data/
    profile.template.json
    history.template.json
  skills/
    weekly-meal-prep/SKILL.md
    woolworths-cart-builder/SKILL.md
```

## Install

### Claude Code

Add this repository as a Claude Code plugin marketplace:

```text
/plugin marketplace add wezham/meal-prep-agent
```

Then install the plugin:

```text
/plugin install meal-prep-agent@meal-prep-agent
```

### Codex

Install the plugin from GitHub with the Codex Marketplace CLI:

```bash
npx codex-marketplace add wezham/meal-prep-agent --plugins
```

To install only this plugin path:

```bash
npx codex-marketplace add wezham/meal-prep-agent/plugins/meal-prep-agent --plugin
```

Codex metadata also lives in this repo for repo-local marketplace usage:

- `.agents/plugins/marketplace.json`
- `plugins/meal-prep-agent/.codex-plugin/plugin.json`

After installing or enabling `meal-prep-agent`, ask:

```text
Generate this week's meal prep plan.
```

## Configure Private Data

Published data files are templates only. Normal users should not need to edit
JSON or run setup commands. After installing the plugin, ask Claude Code or
Codex:

```text
Set up my meal prep profile.
```

The agent will ask plain-language questions, then create private runtime files
from the templates:

```text
plugins/meal-prep-agent/data/local/
```

That directory is ignored by git. The agent reads the private profile and meal
history directly, summarizes recent meals to avoid repeats, and appends accepted
plans after explicit approval.

The skill should only append plans after explicit user approval.

## Woolworths Cart Builder

Ask:

```text
Use the woolworths-cart-builder skill to add this grocery list to my Woolworths cart.
```

The cart-builder workflow stops at cart review. It must not place an order,
choose payment details, or submit checkout.

## Release Checklist

- Confirm templates contain no personal data.
- Run the validation commands from `CONTRIBUTING.md`.
- Confirm `plugins/meal-prep-agent/.codex-plugin/plugin.json` has the intended version.
- Tag releases from `main` after the plugin has been tested in Claude Code and Codex.

## License

MIT
