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

Source review is complete. The reviewer independently reran all 28 mocked tests
and Python compilation successfully. Initial source was published to
`pablowp3/homeassistant-tohmo` in commit
`e4e5c7994eefd74d21fcd9eab9ab3b709697eeda`.

The user subsequently authorized making the repository public so Marketplace can
install it. The coordinator owns the visibility change and publication of these
updated instructions. No credentials or personal account responses belong in
the public repository. Preferred installation is Marketplace **Add from link**;
manual copying remains a fallback.

## Remaining validation

1. Complete public visibility and documentation publication, then install through
   Marketplace as an Integration from `https://github.com/pablowp3/homeassistant-tohmo`.
2. Load on actual Home Assistant 2026.11, then enter account credentials in its
   UI. The local tests do not install or emulate the complete Home Assistant core.
3. Verify discovered entities and values against the mobile app. Check firmware
   availability with the read-only check button if desired.
4. Live writes remain untested. Any deliberate functional control test must be
   explicitly authorized and should use an agreed reversible control first.

Do not claim a physical charging command worked merely because mocked tests or
cloud discovery succeeded. A firmware check failure remains unknown rather than
being mislabeled "up to date"; the app itself conflates several failures here.

## Local checks

Run the README commands. Tests cover concurrent token expiry, one read retry,
no write retry, rate limiting, invalid credentials/expiry, request paths and
payloads, numeric-vs-alphanumeric IDs, owner/tenant/hardware capability gates,
current limits and active-but-suspended sessions.

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
