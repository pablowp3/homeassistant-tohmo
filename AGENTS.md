# Agent handoff rules

Read `docs/API.md` and `docs/HANDOFF.md` before changing behavior.

- Repository is private. Keep account credentials, tokens and personal account
  snapshots out of commits, issues, logs and test fixtures.
- `const.py` contains shared public mobile-client identification from the official
  APK; it is not a user credential. Do not replace it with account tokens.
- Derive endpoint verbs and payloads from evidence. Whitelist supported settings.
  Do not add arbitrary URL/HTTP/payload passthrough services.
- Preserve charge point IDs, session IDs and alphanumeric EVSE identifiers.
  Start uses the distinct internal EVSE ID converted to a JSON number, as the app does.
- Never replay charger writes automatically, even after 401 or timeout.
- Keep ownership, live session flags and server-provided current bounds enforced
  at the command boundary, not just in entity visibility.
- Do not change a real charger as a test. Obtain explicit authorization for a
  concrete live control test; firmware updates are especially disruptive.
- Run `python -m unittest discover -s tests -v` and compile Python files after
  changes. Report mocked checks separately from real HA loading and live writes.
- Preserve the existing user's work. Do not publish, install or operate the
  charger merely because a previous agent prepared those steps.
