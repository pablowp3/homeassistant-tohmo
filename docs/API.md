# API evidence and scope

This integration uses the private mobile API, not the operator/admin web portal.
The API is undocumented and may change. No charger write was used to discover it.
The implementation was independently derived from the user-supplied Android app
3.252.2 and authenticated, read-only account responses on 2026-11-08.

Base: `https://chargeguru.eu-cg.charge.ampeco.tech/api/v1`.
JSON requests identify the official public mobile client. The embedded OAuth
client identifier/secret are shared app constants, not account credentials.
Password and refresh grants use `POST /app/oauth/token`. User passwords are not
persisted. Home Assistant stores access/refresh tokens in its local config entry.
The integration repository is intended for public Marketplace distribution;
personal account snapshots and credentials are never included. The public app
client constants do not grant access without the user's own account credentials.

## Implemented charger controls

All paths below are relative to the base. `{cp}` is the charge point's `id`;
`{evse}` is the internal EVSE `id`. The separate, potentially alphanumeric
`identifier` is **not** the numeric start-session argument.

| Control | Exact method, path and JSON | Capability/account evidence | HA surface | Evidence/test status |
|---|---|---|---|---|
| Start | `POST /app/session/start`, `{"evseId": <numeric internal id>}` | Owned personal charger; no active session; ready connector | Session switch and start button | APK 34441, 52585, 53191; mocked request; live write untested |
| Stop | `POST /app/session/{session}/end`, no body | Active embedded session, `isRemoteStopSupported` and `isRemoteStopEnabled` true | Session switch and stop button | APK 34447, 52586; account supports; mocked request; live write untested |
| Restart | `POST /app/personal/charge-points/{cp}/reboot`, no body | Owner menu; not already restarting | Button | APK 34636, 29892; mocked request; live write untested |
| Unlock cable | `POST /app/personal/charge-point/{cp}/unlock-connector/{evse}`, no body | Owner; `is_connector_lock_supported=true` | Button | APK 34708, 52587; mocked request; live write untested |
| Lock cable setting | `PATCH /app/personal/charge-points/{cp}`, `{"connector_lock": bool}` | `is_connector_lock_supported=true` | Switch | APK 53153; account supported; payload validation tested |
| Require authentication | Same PATCH, `{"requires_authorization": bool}` | Owner; tenant `enforceAuthentication=false` | Switch | APK 53080; account supported; payload validation tested |
| Maximum current | Same PATCH, power group below | `is_max_current_supported=true`; server supplies min/max | Number in A | APK 44739, 44740; account range 6–16 A; validation tested |
| Keep-awake current | Same PATCH, power group below | `min_charging_current` and server min/max present | Number in A | APK 29141, 44740; account supported; validation tested |
| Keep vehicle awake | Same PATCH, power group below | Owner; boolean `enable_keep_awake` present | Switch | APK 44740; account supported; validation tested |
| LED intensity | Same PATCH, `{"light_intensity": 5/20/50}` | `is_light_intensity_supported=true` | Select | APK 28934, 44572, 53081; account supported; validation tested |
| Rename | Same PATCH, `{"name": "..."}` | Owner | Text | APK 53156; account supported; payload validation tested |
| Check firmware | `GET /app/personal/charge-points/{cp}/firmware-updates/check` | `isFirmwareUpdatesSupported=true` | Button + result sensor | APK 34663, 52577; successful HTTP means available; live endpoint not yet exercised |
| Install firmware | `POST /app/personal/charge-points/{cp}/firmware-updates`, no body | Same flag; successful check; no current update or active charging session | Button | APK 34666; account supported; mocked only; live install deliberately untested |

Power group: `{"max_current_a": number, "min_charging_current": number,
"enable_keep_awake": bool}`. Changing one entity preserves the other two fields
from a fresh cloud read. The integration rejects fractional/out-of-range current
and keep-awake current above the maximum. It never changes unrelated settings.

The account returned LED intensity `100`. The app maps any value over 20 to
"high", but its save button sends 50. HA preserves the exact existing value in
the select; the writable app presets remain 5, 20, 50. Restoring 100 is not
advertised because no such app operation or API acceptance has been verified.

## Other discovered features

| Feature | Discovery | Account gate and disposition |
|---|---|---|
| Smart charging mode, schedules, solar, target charge | PATCH charger `smart_charging`; PATCH `/app/session/{session}` `smartCharging`; APK 53171 | `smart_charging_enabled=false`, `allowed_smart_charging_modes=[]`; no controls created |
| Boost active smart session | PATCH session `{"smartCharging":{"enabled":false}}`; APK 51215, 34468 | Smart charging unavailable; not exposed |
| Override randomized delay | POST `/app/session/{session}/boost`; APK 34459, 51215 | `randomised_delay_enabled=false`; not exposed |
| Start a new unscheduled boost session | POST start with `{"evseId": number,"smartCharging":{"enabled":false}}`; APK 52584 | Smart/boost mode unavailable; not exposed |
| Pause/resume | Names exist in telemetry SDK | Not charger endpoints; no fabricated pause/resume commands |
| Shared access, invitation links, pending requests | Personal charger shares/invitations routes | Owner menu APK 29892 gates on `sharing`; absent in account response. Disabled, not exposed |
| Automatic firmware toggle | `disable_automatic_firmware_updates` returned by server | No matching app string or setter found. Read-only evidence, no guessed PATCH |
| Reimbursement eligibility | GET `/app/personal/session/{session}/toggle-reimbursement-eligibility` | Mutation despite GET name. Tenant reimbursement false and session `canToggleReimbursementEligibility=false`; not called |
| AxleFlex enrollment | Personal charger AxleFlex endpoints | `smart_charging.flex.available=false`; unavailable |
| Remove charger | DELETE personal charger | Tenant `canRemoveCharger=false`; unavailable |
| Change PIN | Charger configuration | Tenant `isPinChangeEnabled=false`; unavailable |
| Wi-Fi provisioning | App Bluetooth setup flow | No cloud Wi-Fi flag/provisioning data in account. Bluetooth out of requested cloud access |
| Security event notifications/history | Owner menu gated on `isTamperDetectionNotifications` | False; unavailable |
| Location/time zone | Configuration screen hides location editing when `location_id` exists; tenant multiple time zones false | Account location is operator managed; no edit exposed |
| Photo, account profile, payments, subscriptions | App personalization/account management | Not charger operating controls; outside integration scope |
| Reservations and queues | Public-charging features | No private-charger reservation operation offered in account; queue disabled |

The enabled account controls above are the supported v0.1 scope. If a future
account enables a currently disabled feature, its unimplemented control must be
added with verified schemas before claiming support. No arbitrary HTTP or generic
unvalidated settings action is exposed.

## Read model and failure rules

`GET /app/personal/charge-points` returns `data` with embedded EVSE/session data.
Charger details GET returned the same fields. OPTIONS returned an empty array,
not a permission schema. `/app/session/active` returned 404 for this tenant;
the integration never depends on it.

A session remains active when the vehicle is suspended and power is zero. Stop
availability follows session status and stop-permission flags. Energy is Wh,
power W and duration seconds. Session energy has no accumulating HA state class
because it resets per session; it must not be mistaken for a lifetime meter.

Only GET/OPTIONS can replay once after an authentication failure. Commands are
never replayed after 401, timeout, malformed responses, or ambiguous results.
HTTP 200 with `success:false` is an error. Redirects are forbidden. Raw server
messages, tokens and URLs are not logged. Token renewal is serialized and rotated
tokens are persisted immediately. HTTP 429 pauses further calls for Retry-After.

## Development references

- [Home Assistant config flow](https://contributors.home-assistant.io/core/integrations/config-flow/)
- [Home Assistant reauthentication](https://contributors.home-assistant.io/core/integrations/reauth-reconfigure/)
- [Home Assistant fetching data](https://contributors.home-assistant.io/core/integrations/fetching-data/)
- [Marketplace installation](https://www.home-assistant.io/integrations/marketplace/): add the public repository URL as a custom integration.
- [Marketplace repository requirements](https://contributors.home-assistant.io/marketplace/reference/repository-structure/)
