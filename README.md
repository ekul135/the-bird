<p align="center">
  <img src="custom_components/the_bird/brand/logo.png" alt="The Bird" width="200">
</p>

# The Bird for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ekul135/the-bird.svg)](https://github.com/ekul135/the-bird/releases)

A Home Assistant custom integration that fetches your daily electricity usage and cost data from your energy provider portal.

## Features

- **Grid Usage (kWh)**: Daily grid electricity imported
- **Grid Usage Cost**: Cost of grid usage
- **Solar Export (kWh)**: Daily solar energy exported
- **Solar Export Credit**: Credit from solar export
- **Super Export (kWh)**: Super Export energy
- **Super Export Credit**: Credit from Super Export
- **Supply Charge**: Daily supply/service charge
- **ZeroHero Credit**: ZeroHero credit
- **Net Cost**: Net daily cost (negative = credit)
- **Account Balance**: Current account balance
- **Unbilled Amount**: Unbilled usage since last invoice
- **Estimated Balance**: Account balance + unbilled amount
- **Historical Data**: Automatically imports 14 days of history on first setup
- **Correct Date Attribution**: Statistics are correctly dated to match the actual usage date

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots menu in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/ekul135/the-bird`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "The Bird" and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/the_bird` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "The Bird"
4. Enter your account email and password
5. Select your meter from the list (or enter manually if needed)

## Sensors

After setup, the following sensors will be available (where `<NMI>` is your meter identifier):

### Daily Data Sensors

These sensors display the most recent daily data. Use the external statistics (see Energy Dashboard section) for charts and rollups.

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.the_bird_<NMI>_usage` | Grid electricity imported | kWh |
| `sensor.the_bird_<NMI>_usage_cost` | Cost of grid usage | AUD |
| `sensor.the_bird_<NMI>_solar` | Solar energy exported | kWh |
| `sensor.the_bird_<NMI>_solar_credit` | Credit from solar export | AUD |
| `sensor.the_bird_<NMI>_super_export` | Super Export energy | kWh |
| `sensor.the_bird_<NMI>_super_export_credit` | Super Export credit | AUD |
| `sensor.the_bird_<NMI>_supply` | Daily supply charge | AUD |
| `sensor.the_bird_<NMI>_zerohero` | ZeroHero credit | AUD |
| `sensor.the_bird_<NMI>_net_cost` | Net daily cost (negative = credit) | AUD |

### Account Snapshot Sensors

These sensors show current account status.

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.the_bird_<NMI>_account_balance` | Current account balance | AUD |
| `sensor.the_bird_<NMI>_unbilled_amount` | Unbilled usage since last invoice | AUD |
| `sensor.the_bird_<NMI>_estimated_balance` | Balance + unbilled amount | AUD |

## Example Dashboard Cards

### Entities Card
```yaml
type: entities
title: The Bird Energy
entities:
  - entity: sensor.the_bird_qb121208805_usage
    name: Usage
  - entity: sensor.the_bird_qb121208805_usage_cost
    name: Usage Cost
  - entity: sensor.the_bird_qb121208805_solar
    name: Solar Export
  - entity: sensor.the_bird_qb121208805_solar_credit
    name: Solar Credit
  - entity: sensor.the_bird_qb121208805_net_cost
    name: Net Cost
```

### Statistics Graph
```yaml
type: statistics-graph
title: Daily Usage
chart_type: line
period: day
stat_types:
  - state
entities:
  - the_bird:usage
  - the_bird:solar
```

## Energy Dashboard

The Bird automatically imports statistics with the **correct historical date**. Since energy data from your provider represents yesterday's usage (but is fetched today), the integration imports statistics timestamped for the actual date the energy was used.

### Historical Data Import

On first setup, The Bird automatically fetches and imports **14 days of historical data**. This means your Energy Dashboard and statistics graphs will have data immediately, not just from the day you installed the integration.

### Using Statistics in Charts

The Bird creates external statistics that can be used in statistics graphs:

```yaml
type: statistics-graph
title: Usage
chart_type: line
period: day
stat_types:
  - state
entities:
  - the_bird:usage
```

### Available Statistics

| Statistic ID | Description |
|--------------|-------------|
| `the_bird:usage` | Grid electricity consumption (kWh) |
| `the_bird:usage_cost` | Grid usage cost (AUD) |
| `the_bird:solar` | Solar export (kWh) |
| `the_bird:solar_credit` | Solar export credit (AUD) |
| `the_bird:super_export` | Super export (kWh) |
| `the_bird:super_export_credit` | Super export credit (AUD) |
| `the_bird:supply` | Daily supply charge (AUD) |
| `the_bird:zerohero` | ZeroHero credit (AUD) |
| `the_bird:net_cost` | Net daily cost (AUD) |

> **Tip:** Use `state` stat type for daily values. The `sum` type shows cumulative totals.

> **Note:** The sensors (e.g., `sensor.the_bird_*_usage`) show the current day's data and include a `data_date` attribute indicating which date the data is for. The external statistics (e.g., `the_bird:usage`) are correctly backdated for historical accuracy.

## Troubleshooting

### Authentication Failed
- Ensure your email and password are correct
- Try logging into your energy provider portal to verify your credentials

### No Data
- Data is typically available after 6 AM for the previous day
- Smart meter data may have a delay of 1-2 days

## Privacy & Security

- Your credentials are stored locally in Home Assistant
- Password is encrypted using RSA-OAEP before being sent to the API
- No data is sent to any third parties

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This is an unofficial integration and is not affiliated with any energy company. Use at your own risk.
