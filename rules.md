# Development Rules

## Question Prefix

When a message starts with "question:" or contains "question:", it means:
- **DO NOT implement code yet**
- The user is looking for alternatives, discussion, or options
- Provide explanations, pros/cons, and recommendations
- Wait for explicit approval before implementing

## Component Usage

Always try to use an existing component first. If a component does not exist, ask if one should be created.

### Guidelines:
- **Check for existing components** before writing inline HTML/JSX
- **Ask before creating** - if a component doesn't exist, discuss whether it should be created
- **Consistency over optimization** - even if a component is only used twice in the application, it's worth using for consistency
- **Centralized styling** - components allow color schemes and styles to be managed in one place
- **Reusability** - components make it easier to maintain and update UI elements across the application

### Benefits of using components:
- Consistent styling and behavior
- Easier maintenance (change once, update everywhere)
- Better code organization
- Reduced duplication

## Svelte `$effect` Usage

Use `$effect` sparingly. It should only be used when absolutely necessary.

### When to use `$effect`:
- Side effects that need to run when reactive state changes (e.g., API calls, DOM manipulation)
- Cleanup operations that need to run when a component is destroyed
- Synchronizing with external systems or libraries

### When NOT to use `$effect`:
- Simple reactive computations (use `$derived` instead)
- Conditional rendering based on state (use reactive statements or `{#if}` blocks)
- Event handlers (use regular functions with `onclick`, `onchange`, etc.)
- Initialization that can be done in component setup or `onMount`

### Best Practices:
- Prefer `$derived` for computed values
- Use `onMount` for one-time initialization
- Use event handlers for user interactions
- Only use `$effect` when you need to react to state changes with side effects

