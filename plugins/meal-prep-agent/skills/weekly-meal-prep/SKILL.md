---
name: weekly-meal-prep
description: Generate a configurable weekly meal prep plan with any enabled mix of breakfasts, lunches, and dinners, distinct recipe counts per meal type, a combined ingredient list, batch cooking instructions, meal memory, optional profile constants, and Woolworths product links. Use when the user asks to create, plan, refresh, configure, or generate weekly meal prep.
---

# Weekly Meal Prep

Use this skill to run a parent-agent workflow that generates a weekly meal prep plan. The workflow is manual in v1 and uses private local JSON files for user preferences and meal history. Do not require the user to install or run Python, Node, Bash, or any helper script.

## Local Files

- Templates: `plugins/meal-prep-agent/data/profile.template.json` and `plugins/meal-prep-agent/data/history.template.json`
- Default private runtime data: `~/.meal-prep-agent/profile.json` and `~/.meal-prep-agent/history.json`
- Legacy private runtime data: `plugins/meal-prep-agent/data/local/profile.json` and `plugins/meal-prep-agent/data/local/history.json`

On first run, create missing private runtime files in `~/.meal-prep-agent/` by copying the template JSON content. The agent should do this with its normal file tools.

If legacy `data/local/` files exist and the matching `~/.meal-prep-agent/` file is missing, migrate the legacy file to `~/.meal-prep-agent/` before planning. Do not overwrite an existing `~/.meal-prep-agent/` file with legacy data unless the user explicitly asks.

If the user asks to set up or change their meal prep profile, ask plain-language questions and then update `~/.meal-prep-agent/profile.json`. Useful setup questions include how many breakfasts, lunches, and dinners they want, how many distinct recipes for each meal type, dietary rules, allergies, dislikes, preferred cuisines, equipment, budget notes, and recurring optional staples.

## Meal Type Configuration

Use `profile.meal_plan` as the source of truth for meal counts:

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

Rules:

- `servings` means how many meals of that type to prep for the week.
- `recipe_count` means how many distinct batch recipes should cover that meal type.
- If `servings` is `0` or `enabled` is `false`, do not plan that meal type.
- If a user says "N breakfasts", set `meal_plan.breakfast.servings` to `N` and enable breakfast.
- If a user says "2 different lunch meals" or "2 lunch recipes", set `meal_plan.lunch.recipe_count` to `2`.
- If a user says "5 lunches" or "5 lunch portions", set `meal_plan.lunch.servings` to `5`.
- Keep `recipe_count` between `0` and `servings` for each meal type. If the user asks for more recipes than servings, set recipes equal to servings and mention the adjustment.
- Default to the template values if the user has not configured meal counts: 3 lunches from 1 lunch recipe and 3 dinners from 1 dinner recipe.

Always read the private profile and history before planning. Summarize recent meal names, primary proteins, core ingredients, cuisine tags, and sauce profiles from `history.json` directly before choosing recipes.

## Parent Agent Responsibilities

The parent agent owns orchestration and final review. It must:

1. Create or migrate missing private runtime files in `~/.meal-prep-agent/` from templates or legacy `data/local/` files if needed, then read `~/.meal-prep-agent/profile.json` and `~/.meal-prep-agent/history.json`.
2. If the private profile is still a mostly empty template, offer to set it up conversationally before planning.
3. If the active profile has `optional_constants`, ask the user which constants they need this week before planning the grocery list.
4. Ask a recipe-planning sub-agent to propose exactly the configured recipe counts for each enabled meal type, covering exactly the configured servings.
5. Ask an instruction sub-agent to convert the recipes into one practical batch-cooking sequence.
6. Ask an ingredient-combiner sub-agent to merge all recipe ingredients plus only the user-selected optional constants into one concise grocery list.
7. Pass each grocery-list ingredient to a Woolworths lookup sub-agent, one ingredient at a time.
8. Present the full plan to the user before treating it as complete.
9. Append the accepted plan to the active private `history.json` after user acceptance, an explicit request to save it, or any user request to proceed to the Woolworths cart from that plan.

Do not save a generated plan to memory before the user accepts it. A request to build, prepare, add to, or proceed to a Woolworths cart using the generated grocery list counts as acceptance of the meal plan for memory purposes.

## Optional Constants Prompt

Before creating the final grocery list, ask the user whether they need any optional constants from the active private profile.

Use a concise prompt such as:

```text
Do you need any of these recurring items this week: rolled oats, frozen berries, 5 bananas?
```

Rules:

- Do not decide optional constants on the user's behalf.
- Include only constants the user explicitly selects or asks for.
- If the user says no, skip all optional constants.
- If the user does not answer, pause for the answer before final ingredient combining.
- De-duplicate constants by ingredient name before prompting.
- Preserve configured quantities, such as `5 bananas` or `1 kg frozen berries`.
- Optional constants are grocery add-ons, not extra meal recipes.

## Recipe-Planning Sub-Agent Brief

Ask the recipe-planning sub-agent to produce the configured number of batch recipes for each enabled meal type. The plan must cover the exact configured serving counts from `profile.meal_plan`.

For the default template, this means:

- 0 breakfasts
- 3 lunches from 1 lunch recipe
- 3 dinners from 1 dinner recipe

If the user configures breakfast, include breakfast recipes and breakfast meal slots. If there is a strong preservation or crossover reason, the sub-agent may map a recipe across meal types, but it must still respect the configured total servings and distinct recipe counts as closely as practical and explain any deviation.

The recipes must optimize for:

- low-effort batch cooking
- meals that preserve and reheat well
- the available equipment only: oven, stove, air fryer, rice cooker
- ingredient crossover where it saves effort without making meals feel repetitive
- reduced similarity to prior meals in the active private history

Avoid:

- raw seafood, fragile salads, or meals that become soggy quickly
- recipes that require a blender, food processor, slow cooker, pressure cooker, grill, or stand mixer
- repeating the same cuisine, sauce profile, or primary protein too often
- niche ingredients that are hard to buy at Woolworths unless the profile explicitly prefers them
- creating more recipes than configured

Require this shape from the sub-agent:

```json
{
  "meal_plan": {
    "breakfast": {"servings": 0, "recipe_count": 0, "enabled": false},
    "lunch": {"servings": 3, "recipe_count": 1, "enabled": true},
    "dinner": {"servings": 3, "recipe_count": 1, "enabled": true}
  },
  "recipes": [
    {
      "name": "",
      "meal_slots": ["lunch", "lunch", "lunch"],
      "servings": 3,
      "short_description": "",
      "core_ingredients": [],
      "cuisine_tags": [],
      "preservation_notes": "",
      "crossover_notes": ""
    },
    {
      "name": "",
      "meal_slots": ["dinner", "dinner", "dinner"],
      "servings": 3,
      "short_description": "",
      "core_ingredients": [],
      "cuisine_tags": [],
      "preservation_notes": "",
      "crossover_notes": ""
    }
  ],
  "lunches": [
    {
      "recipe_name": "",
      "serving_number": 1
    }
  ],
  "dinners": [
    {
      "recipe_name": "",
      "serving_number": 1
    }
  ],
  "breakfasts": [],
  "total_servings": 6,
  "total_recipes": 2,
  "repeat_avoidance_note": ""
}
```

## Instruction Sub-Agent Brief

Ask the instruction sub-agent for one concise batch-cooking plan for the configured recipes, not disconnected meals.

The plan must:

- sequence rice cooker, oven, stove, and air fryer work efficiently
- group chopping, seasoning, roasting, simmering, and portioning steps
- include safe cooling and storage guidance
- avoid assuming any equipment outside the profile
- be concise enough to follow while cooking

## Ingredient-Combiner Sub-Agent Brief

Ask the ingredient-combiner sub-agent to create one grocery list from all configured recipes and only the optional constants the user selected after being prompted.

The list must:

- merge duplicate ingredients
- normalize units where practical
- group items under short headings such as `Protein`, `Produce`, `Pantry`, `Dairy`, and `Frozen`
- keep pantry staples in the list if they are needed, but mark them as `check pantry`
- include selected optional constants, marking them as `optional constant`
- exclude optional constants the user did not select
- de-duplicate optional constants, including repeated entries in the profile
- avoid per-recipe ingredient lists unless needed for clarity

Require this shape:

```json
{
  "combined_ingredients": [
    {
      "group": "Protein",
      "items": [
        {
          "ingredient": "chicken breast",
          "quantity": "900 g",
          "notes": "",
          "source": "recipe"
        },
        {
          "ingredient": "bananas",
          "quantity": "5",
          "notes": "optional constant",
          "source": "optional_constant"
        }
      ]
    }
  ]
}
```

## Woolworths Lookup Sub-Agent Brief

Pass each ingredient to the Woolworths lookup sub-agent one at a time.

For each ingredient, ask the sub-agent to search Google for Woolworths Australia product pages. Prefer product pages on `woolworths.com.au`; if no product page is credible, return a Woolworths search result or Google search URL.

Return:

```json
{
  "ingredient": "",
  "query": "",
  "best_url": "",
  "product_name": "",
  "confidence": "high",
  "note": ""
}
```

Confidence rules:

- `high`: exact or near-exact Woolworths product match.
- `medium`: useful Woolworths substitute or broader product category.
- `low`: uncertain match, generic search result, unavailable product, or non-Woolworths fallback.

Keep notes short. Mention substitutions only when confidence is not `high`.

## Final Response Format

Before completing, present the plan back to the user in this order:

1. `Meals`
2. `Combined Ingredients`
3. `Cook Plan`
4. `Woolworths Links`
5. `Memory Note`

Keep the response concise. The user should be able to scan the plan, cook from it, and shop from it.

End by asking whether to save the plan to memory. Save it only if the user approves, unless the user asks to proceed to the Woolworths cart, which counts as approval to save the plan before cart building starts.

## Memory Update

When saving a plan, append a new entry to the active private history with:

- `generated_at`
- `meal_plan`
- `recipes`
- `breakfasts`
- `lunches`
- `dinners`
- `core_ingredients`
- `cuisine_tags`
- `repeat_avoidance_note`

The accepted plan JSON should include the fields above. Preserve the top-level `version` and append to `generated_plans`. Do not write private meal history back to template files. If the JSON file is invalid or cannot be updated cleanly, stop and explain the issue instead of guessing.

If the user proceeds to the Woolworths cart from a generated meal plan, write the meal history before opening the browser or starting the cart-builder workflow. Mention briefly that the plan was saved because the user proceeded to cart building.
