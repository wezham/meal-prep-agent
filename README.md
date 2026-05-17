# Meal Prep Agent

Meal Prep Agent is an open-source, cross-agent plugin for weekly meal prep
planning. It packages portable `SKILL.md` workflows so the same workflows can
be used from Claude Code and Codex without requiring users to install Python,
Node, Bash scripts, or any other helper runtime.

The plugin can:

- generate configurable breakfasts, lunches, and dinners from configured batch recipe counts
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
  .claude-plugin/plugin.json
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

Start Claude Code in any trusted project, then add this repository as a plugin
marketplace:

```text
/plugin marketplace add wezham/meal-prep-agent
```

Install the plugin from that marketplace:

```text
/plugin install meal-prep-agent@meal-prep-agent
```

Restart Claude Code, or run `/reload-plugins` if your Claude Code version
supports it. The plugin skills are then available with the plugin namespace:

```text
/meal-prep-agent:weekly-meal-prep
/meal-prep-agent:woolworths-cart-builder
```

You can also ask in plain language and let Claude Code choose the right skill:

```text
Generate this week's meal prep plan.
Build a Woolworths cart from this grocery list.
```

For local development, clone this repository, start Claude Code from the repo
root, and add the checkout as a local marketplace:

```text
/plugin marketplace add .
/plugin install meal-prep-agent@meal-prep-agent
```

To confirm the package is valid before installing from a checkout, run:

```bash
claude plugin validate .
claude plugin validate plugins/meal-prep-agent
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

Example configuration prompts:

```text
I want 3 breakfasts, 5 lunches, and 4 dinners each week.
```

```text
Use 1 breakfast recipe, 2 different lunch recipes, and 2 different dinner recipes.
```

### Meal Plan Settings

The profile stores meal counts in `meal_plan`:

```json
{
  "meal_plan": {
    "breakfast": {"servings": 0, "recipe_count": 0, "enabled": false},
    "lunch": {"servings": 3, "recipe_count": 1, "enabled": true},
    "dinner": {"servings": 3, "recipe_count": 1, "enabled": true},
    "servings_per_meal": 1
  }
}
```

- `breakfast`, `lunch`, and `dinner`: separate settings for each meal type.
- `enabled`: whether that meal type should be included in weekly planning.
- `servings`: how many portions of that meal type to prep for the week.
- `recipe_count`: how many distinct batch recipes should cover those servings.
- `servings_per_meal`: how many portions count as one meal for the user.

For example, 5 lunches with `recipe_count: 2` means the agent should plan 5
lunch portions spread across 2 different lunch recipes.

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
