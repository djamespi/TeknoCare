# Step 0 manual visual checklist

The user checks the running local app and confirms in chat. No screenshots or
Computer Use are required. This folder retains its earlier name only. Start with
[the confirmation steps](../../README.md#confirm-step-0-works) and a fictional account.

Check these results:

- Dashboard has Dashboard, Profile, Settings and Sign out in the
  top navigation; no SQL joins entry.
- Profile form opens with the same updated navigation.
- Settings form opens with the same updated navigation.
- `/joins/` returns 404 / Page not found. Local debug mode
  may show Django's URL list; this is expected, not a broken clinic feature.

Check a narrow browser window too: navigation should wrap without overlap and
Sign out should still work. Sign in/out and the pages above were verified through
real local HTTP requests, but that does not establish visual layout quality.

Reply with whether all checks pass, or identify the page and unexpected behavior.
Visual review stays pending until you confirm. Do not add PNGs for this checklist.
