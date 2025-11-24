## Review Philosophy

- Only comment when you have HIGH CONFIDENCE (>80%) that an issue exists
- Be concise: one sentence per comment when possible
- Focus on actionable feedback, not observations
- When reviewing text, only comment on clarity issues if the text is genuinely confusing or could lead to errors.

## Skip These (Low Value)
 
Do not comment on:

- **Style/formatting** - CI handles this (rustfmt, prettier)
- **Test failures** - CI handles this (full test suite)
- **Missing dependencies** - CI handles this (mypy will fail)
- **Minor naming suggestions** - unless truly confusing
- **Suggestions to add comments** - for self-documenting code
- **Multiple issues in one comment** - choose the single most critical issue
- **Pedantic accuracy in text** - unless it would cause actual confusion or errors. No one likes a reply guy
