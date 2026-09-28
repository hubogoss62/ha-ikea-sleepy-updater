<p align="center">
  <img src="icon.png" alt="IKEA Sleepy Device Firmware Updater" width="200">
</p>

# IKEA Sleepy Device Firmware Updater (HACS)

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom repository"></a>
  <a href="https://github.com/GITHUB_USER/ha-ikea-sleepy-updater/actions/workflows/validate.yml"><img src="https://github.com/GITHUB_USER/ha-ikea-sleepy-updater/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=GITHUB_USER&repository=ha-ikea-sleepy-updater&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.">
  </a>
  <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=ikea_sleepy_updater">
    <img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Add Integration">
  </a>
</p>

> **Fork of [CaelanBorowiec/ha-bilresa-updater](https://github.com/CaelanBorowiec/ha-bilresa-updater).**
> The original only handles the IKEA BILRESA remote. This fork applies the same
> keep-awake mechanism to **any battery-powered IKEA Matter-over-Thread device
> that falls asleep during firmware updates** (MYGGBETT, MYGGSPRAY,
> TIMMERFLOTTE, KLIPPBOK, BILRESA...) and optionally to other vendors' devices.

Home Assistant's built-in Matter integration already exposes a **Firmware**
update entity and downloads the OTA image from the CSA DCL. On sleepy
battery-powered devices the transfer usually stalls because the device goes
back to sleep mid-download, and the usual workaround is to keep pressing a
button on the device for the whole update. This integration does that for you:
it notices an update starting (from HA, Apple Home, Google Home...) and keeps
the device awake with Matter `StayActiveRequest` commands until the update
finishes.

## Supported devices

A Matter node is picked up when **all** of these are true:

| Criterion | Why |
|---|---|
| Vendor is IKEA (`0x117C`), or any vendor if selected in the options | Safe default |
| Exposes the **OTA Software Update Requestor** cluster | It can be updated |
| Exposes the **ICD Management** cluster (`0x0046`) on endpoint 0 | It is a sleepy *Intermittently Connected Device* |
| Product name contains one of the configured filters (optional) | Restrict to e.g. `MYGGBETT, MYGGSPRAY` |

Mains-powered devices (bulbs, plugs, the Dirigera bridge...) do not implement
ICD Management and are therefore never touched.

| Device | Type | Status |
|---|---|---|
| BILRESA (buttons / scroll wheel) | Remote | Verified upstream (LIT, `StayActiveRequest` supported) |
| MYGGBETT | Door/window sensor | Expected to work, please report |
| MYGGSPRAY | Motion sensor | Expected to work, please report |
| TIMMERFLOTTE | Temperature/humidity sensor | Expected to work, please report |
| KLIPPBOK | Water leak sensor | Expected to work, please report |

`StayActiveRequest` is optional in the Matter spec. If a device does not
advertise it in its ICD `AcceptedCommandList`, the integration logs a warning
with the device's `UserActiveModeTriggerInstruction` (which button to press) and
you are back to the manual method for that device. The **ICD operating mode**
and **Last promised active duration** diagnostic sensors show how a given device
behaves; please open an issue with those values for any device you test.

## How it works

```
You press the native "Firmware" Update button (or any controller starts an OTA)
        │
        ▼
Matter Server runs the OTA Provider + BDX transfer
        │  OTA UpdateState → querying / downloading / applying
        ▼
this integration (watching UpdateState) ──► StayActiveRequest loop ──► sleepy device
                                            (re-armed until state returns to idle)
```

The integration connects to your Matter Server as a second websocket client,
watches the OTA `UpdateState` of every matching device, and while an update is
in progress re-sends `StayActiveRequest` (ICD Management `0x0046`) before each
`PromisedActiveDuration` expires (at 50 % of it, or at the configured fallback
interval when the device does not report one).

## Requirements

- Home Assistant 2024.12 or newer
- The official **Matter** integration set up and working, with a Thread border
  router and IPv6 enabled on the Home Assistant host
- The devices must be **commissioned to Home Assistant's Matter fabric**

## Installation

1. **Remove the original *IKEA BILRESA Firmware Updater* if you use it**: both
   would otherwise send keep-awake requests to your BILRESA at the same time.
2. In HACS, add `https://github.com/GITHUB_USER/ha-ikea-sleepy-updater` as a
   **custom repository** (category: *Integration*).
3. Install **IKEA Sleepy Device Firmware Updater** and restart Home Assistant.
4. **Settings → Devices & Services → Add Integration →** *IKEA Sleepy Device
   Firmware Updater*, and confirm the Matter Server URL (pre-filled).

The log lists the devices being watched at start-up
(`Watching N sleepy Matter device(s) for firmware updates: ...`).

## Configuration

**Configure** on the integration offers:

| Option | Default | Description |
|---|---|---|
| Vendors | IKEA only | *Any Matter vendor* extends keep-awake to every OTA-capable ICD on your fabric (experimental) |
| Product name filter | *(empty = all)* | Comma-separated, case-insensitive fragments, e.g. `MYGGBETT, MYGGSPRAY` |
| Keep-awake re-send interval | 15 s (4–60) | Used when the device does not report a `PromisedActiveDuration` |

Changing an option reloads the integration. Newly commissioned devices are
picked up on the next reload or HA restart.

## Usage

Update firmware with the **Firmware** update entity of the official Matter
integration. On each matching device this integration adds:

- **Keep-awake active** binary sensor: on while the device is held awake
- Diagnostic sensors: OTA update state, ICD operating mode (SIT/LIT), last
  promised active duration (disabled by default)
- **Keep awake now** button: sends a single `StayActiveRequest`

### Tip: stay close to the parent Thread router

For large downloads over Thread, place the device within a metre or two of its
parent router during the update (the **Thread** tab of the Matter Server web UI
shows it). A strong direct link means fewer hops and fewer dropouts, which can
otherwise restart the download from 0 %.

## Limitations

- Only one firmware update runs at a time (Matter Server limitation).
- A Thread dropout mid-transfer can still abort a download; keep-awake greatly
  reduces but cannot eliminate this.
- Entities of devices removed or excluded by a new filter stay in the entity
  registry until you delete them.

## Credits & license

Based on the work of [Caelan Borowiec](https://github.com/CaelanBorowiec/ha-bilresa-updater).
Licensed under the [MIT License](LICENSE).

## Disclaimer

Firmware updates carry inherent risk. This is a community project, not
affiliated with or endorsed by IKEA or the Connectivity Standards Alliance. Use
at your own risk.
