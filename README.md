# Tohmo for Home Assistant

Custom integration for an Alfen charger managed through Tohmo's Spanish cloud
(formerly ChargeGuru). It uses the same account as the Android app. No connection
to the charger's local network is required.

## Controls

- Start/stop a charging session; restart charger; unlock cable.
- Maximum charging current and keep-awake current, within server limits.
- Keep vehicle awake, require authentication and connector-lock settings.
- LED presets, charger name, firmware check and explicit firmware installation.
- Connector/session status, charging power, session energy, duration and cost,
  firmware version and previous-month energy.

Controls appear only for capabilities present in the account. Smart charging,
solar, schedules, sharing, reimbursement and AxleFlex are disabled in the tested
account and are not advertised as working features. See [API evidence](docs/API.md)
for the complete inventory, exact scope and validation status.

An active session can report **0 W / suspended** while the vehicle is full or
paused. The session switch stays on until the cloud reports that the session ends.
Session energy is per session, not a lifetime energy meter.

The app offers LED values 5/20/50. An existing value such as 100 is displayed
unchanged; selecting another preset does not promise the app can restore 100.

## Install through Marketplace

The repository is published for public installation and contains no user account
data. Add it as a custom repository; inclusion in the default catalog is not
required. See the [official Marketplace guide](https://www.home-assistant.io/integrations/marketplace/).

1. Open **Settings → Marketplace → Add from link**.
2. Enter `https://github.com/pablowp3/homeassistant-tohmo` and select
   **Integration** if asked for its category.
3. Open **Tohmo**, install it, then restart Home Assistant when prompted.
4. Open **Settings → Devices & services → Add integration → Tohmo**.
5. Enter the email/password from the Tohmo Android app.

On older Home Assistant versions with HACS, add the same URL under
**Custom repositories**, category **Integration**, then download it and restart.

### Manual alternative

Download the repository and copy `custom_components/tohmo` into Home Assistant's
`/config/custom_components/tohmo` directory. Restart Home Assistant, then complete
steps 4–5 above.

The password is used once and is not saved. Access and refresh tokens are stored
in Home Assistant's config entry and are renewed automatically. If Tohmo revokes
the session, Home Assistant asks you to sign in again. Treat HA backups as private.

Data refreshes every 60 seconds and before explicit commands. Cloud commands may
take time to reach the charger. A timeout leaves the result unknown; the integration
does not automatically resend commands. Refresh state before deciding to retry.
Firmware installation is explicit and blocked while a charging session is active.

## Status and limits

Initial version, developed for Home Assistant 2026.11. The account discovery and
capability reads have succeeded. Automated tests cover request payloads, token
renewal, error handling and capability validation without modifying the charger.
Live start/stop/settings/firmware commands have not been tested yet. See
[handoff](docs/HANDOFF.md) for the precise remaining validation.

This is an unofficial integration using an undocumented mobile API. Tohmo can
change or withdraw that API. It is separate from the French customer website and
the operator administration portal.

## Development

Python 3.12+ can run the independent client/model tests; the actual integration
uses the Python version supplied by Home Assistant.

```sh
python -m pip install aiohttp
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

Tests use synthetic data only. Never commit a real account response, password,
access token, refresh token, charger identifier, billing detail, APK or XAPK.
