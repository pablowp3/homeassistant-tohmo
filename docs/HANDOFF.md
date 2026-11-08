# Maintainer handoff

## Implemented

- Async OAuth client: no password retention, refresh-token rotation persistence,
  serialized refresh, reauthentication, redirect rejection, sanitized errors,
  Retry-After handling and no automatic command replay.
- Native config flow; owner/capability-gated switch, button, number, select, text
  and sensor entities; dynamic addition of discovered devices/entities.
- Fresh state before command validation; no optimistic charger state.
- API inventory and English/Spanish interface strings.

## Evidence

The maintainer's local analysis was performed outside this repository. Only
non-personal protocol facts were transcribed. APK version 3.252.2, application
`com.chargeguru.app`, Hermes bytecode v98. `docs/API.md` references function IDs
so another analyst can reproduce payload tracing against that version.

Read-only account inspection confirmed one owned charger, supported current
range 6–16 A, connector lock, LED adjustment and firmware updates. Tenant smart
charging, sharing, reimbursement and AxleFlex are not enabled for this charger.
The active session was suspended at zero power, which is still an active session.

## Publication and validation status

The public repository `pablowp3/homeassistant-tohmo` and Marketplace installation
are complete. The user explicitly authorized public visibility. Version 0.1.1
was published in commit `36be3fa2622c0240f2db8e36ed4bd5354e2222f8` and downloaded
through Marketplace. No credentials or personal account responses were published.

The native config flow, account authentication and cloud reads were verified on
Home Assistant 2026.11.0 / Python 3.14.10. The initial deployment created 21 entities;
the two firmware diagnostic sensors exposed a missing unit-attribute error.
Version 0.1.1 initializes that unit to `None`. Its regression test reproduced both
failures before the fix and passes afterward, while preserving the measured and
currency units. The reviewer independently passed all 30 tests and compilation.

After the 0.1.1 restart, the integration loaded successfully and all 23 entities
were present: 6 buttons, 2 numbers, 1 select, 9 sensors, 4 switches and 1 text.
Units, current bounds, LED values and the existing active-but-suspended session
were correct. Firmware version was available; firmware-update availability was
unknown, as expected before an explicit check. No Tohmo errors remained in the
system log after restart. No physical charger command was executed.

## Untested operations

The optional firmware-availability endpoint was not exercised during installation.
Live writes remain untested. Any deliberate functional control test must be
explicitly authorized and should use an agreed reversible control first.

Do not claim a physical charging command worked merely because mocked tests or
cloud discovery succeeded. A firmware check failure remains unknown rather than
being mislabeled "up to date"; the app itself conflates several failures here.

## Local checks

Run the README commands. Tests cover concurrent token expiry, one read retry,
no write retry, rate limiting, invalid credentials/expiry, request paths and
payloads, numeric-vs-alphanumeric IDs, owner/tenant/hardware capability gates,
current limits, active-but-suspended sessions and diagnostic sensor units.

On this Windows workspace, restricted execution stalls Python's asyncio loop
even for `asyncio.sleep(0)`. Mock tests finish immediately outside that restriction.
This environment issue is separate from the integration and involves no network
or real charger requests.

## Sources

- [Config flow](https://contributors.home-assistant.io/core/integrations/config-flow/)
- [Reauthentication](https://contributors.home-assistant.io/core/integrations/reauth-reconfigure/)
- [Coordinator data fetching](https://contributors.home-assistant.io/core/integrations/fetching-data/)
- [Marketplace installation](https://www.home-assistant.io/integrations/marketplace/)
- [Repository requirements](https://contributors.home-assistant.io/marketplace/reference/repository-structure/)
