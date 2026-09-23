---
name: frontend-design
description: Use for a new or substantially reshaped UI that needs a distinctive visual direction grounded in its subject.
license: Complete terms in LICENSE.txt
---

# Frontend design

Existing product and design-system contracts win. For a new surface, ground the direction in the subject, audience,
real content, and the page's single job. Do not use a fashionable default merely because the brief leaves room.

Before building, define a compact direction:

- **Thesis:** the one visual idea that expresses this subject.
- **Palette:** a small named color system with explicit values and roles.
- **Type:** deliberate display, body, and utility roles with a clear scale.
- **Structure:** layout devices that encode real content relationships rather than decorate them.
- **Signature:** one memorable, justified visual or interactive element.
- **Restraint:** what stays quiet so the signature can lead.

Critique the direction against the brief. Replace anything that could be reused unchanged for an unrelated product.
Spend boldness in one place, match complexity to the vision, and use motion only when it improves meaning or
feedback.

Build from the chosen direction, then inspect wide and mobile layouts. Require semantic structure, readable
contrast, visible keyboard focus, useful empty/error states, and reduced-motion behavior. Check CSS specificity and
remove decoration that does not serve the task.

Write interface copy from the user's perspective with plain active verbs. Controls name their result; errors say
what happened and what to do next; terminology remains consistent through the flow.
