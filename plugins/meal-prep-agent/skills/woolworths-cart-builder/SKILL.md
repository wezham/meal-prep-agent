---
name: woolworths-cart-builder
description: Create a Woolworths browser cart from a grocery list using a parent browser-session agent and an item-adder sub-agent. Use when the user asks to add meal-prep groceries to Woolworths, build a Woolworths cart, prepare an online grocery order, or create a Woolworths order from ingredients.
---

# Woolworths Cart Builder

Use this skill to create a Woolworths Australia cart from a grocery list. The workflow uses a parent agent to own the browser session and a sub-agent to add one item at a time.

This skill prepares a cart only. Do not place an order, choose delivery/pickup windows, submit payment, or confirm checkout unless the user explicitly asks in a later step and the environment supports safe confirmation.

## Inputs

Accept grocery items from:

- the `Combined Ingredients` output of the `weekly-meal-prep` skill
- a pasted grocery list
- a JSON ingredient list with `ingredient`, `quantity`, `notes`, and optional Woolworths product links

Before opening the browser, confirm that the list is the intended cart source if there is more than one plausible list in the conversation.

## Parent Agent Responsibilities

The parent agent owns orchestration, browser state, and user confirmation. It must:

1. Normalize the grocery list into individual cart items.
2. Ask the user to confirm any optional constants that were not already selected.
3. Start or reuse a browser session and navigate to Woolworths Australia.
4. Ensure the user is logged in if required, pausing for the user to complete login manually.
5. For each item, call the item-adder sub-agent with exactly one target item and any known product URL.
6. Track added, substituted, skipped, unavailable, and uncertain items.
7. Present a cart summary to the user.
8. Stop at the cart review stage.

Do not ask the item-adder sub-agent to manage login, checkout, payment, account settings, addresses, delivery windows, or substitutions across multiple items.

## Browser Session Rules

- Use the host agent's available browser automation. In Codex, prefer the in-app browser when available.
- Start at `https://www.woolworths.com.au/`.
- If Woolworths asks for login, location, store, or fulfillment mode, pause and ask the user to complete or confirm it.
- Do not enter credentials, payment details, or personal information on behalf of the user.
- If the site blocks automation, summarize what was completed and give the remaining items.

## Item-Adder Sub-Agent Brief

Call the item-adder sub-agent once per grocery item. The sub-agent owns only that item.

Input shape:

```json
{
  "ingredient": "chicken breast",
  "quantity": "900 g",
  "notes": "",
  "preferred_url": "https://www.woolworths.com.au/...",
  "acceptable_substitutions": true
}
```

The sub-agent must:

- use `preferred_url` first when provided and credible
- otherwise search Woolworths for the ingredient
- choose the closest practical product match
- set quantity to satisfy the requested amount when the site supports it
- avoid adding excessive quantity when pack sizes do not align
- report uncertainty rather than guessing silently
- return control to the parent after one item

The sub-agent must not:

- add unrelated products
- replace a dietary-sensitive item without parent/user confirmation
- remove existing cart items unless explicitly instructed
- proceed to checkout

Output shape:

```json
{
  "ingredient": "chicken breast",
  "requested_quantity": "900 g",
  "status": "added",
  "product_name": "Woolworths Chicken Breast Fillets",
  "product_url": "https://www.woolworths.com.au/...",
  "cart_quantity": "1 kg",
  "confidence": "high",
  "note": ""
}
```

Allowed `status` values:

- `added`
- `added_substitute`
- `already_in_cart`
- `skipped_needs_user_choice`
- `unavailable`
- `failed`

Confidence rules:

- `high`: exact or near-exact item and quantity.
- `medium`: acceptable substitute, brand difference, or pack-size mismatch.
- `low`: uncertain product match or user choice required.

## Substitution Policy

The parent may allow obvious substitutions without asking, such as:

- Woolworths brand versus another brand
- loose produce versus equivalent packaged produce
- closest larger pack size when quantity cannot be exact

The parent must ask the user before adding substitutions that change:

- protein type
- dietary/allergen characteristics
- fresh versus frozen form
- flavor profile
- materially higher price or bulk quantity

## Final Response Format

After the cart-building attempt, present:

1. `Cart Added`
2. `Substitutions`
3. `Needs Review`
4. `Unavailable or Failed`
5. `Next Step`

Keep it concise. The next step should be a cart review prompt, not checkout.

Example:

```text
Cart Added
- Chicken breast, 1 kg
- Brown rice, 1 kg

Needs Review
- Greek yoghurt: several sizes available; choose one in the cart.

Next Step
Review the Woolworths cart before checkout.
```
