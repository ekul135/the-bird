# Globird Energy for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ekul135/globird-energy-hass.svg)](https://github.com/ekul135/globird-energy-hass/releases)

A Home Assistant custom integration for [Globird Energy](https://globirdenergy.com.au/) that fetches your daily electricity usage and cost data.

## Features

- **Daily Usage (kWh)**: Total electricity consumption for the previous day
- **Daily Usage Cost**: Cost of electricity usage (excluding supply charge)
- **Daily Supply Charge**: The daily supply/service charge
- **Daily Total Cost**: Total cost (usage + supply charge)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots menu in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/ekul135/globird-energy-hass`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "Globird Energy" and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/globird_energy` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Globird Energy"
4. Enter your Globird Energy account email and password
5. Select your meter from the list (or enter manually if needed)

## Sensors

After setup, the following sensors will be available:

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.globird_energy_*_daily_usage` | Yesterday's total electricity usage | kWh |
| `sensor.globird_energy_*_daily_usage_cost` | Yesterday's usage cost | AUD |
| `sensor.globird_energy_*_daily_supply_charge` | Daily supply charge | AUD |
| `sensor.globird_energy_*_daily_total_cost` | Total daily cost | AUD |

## Example Dashboard Card

```yaml
type: entities
title: Globird Energy
entities:
  - entity: sensor.globird_energy_qb121208805_daily_usage
    name: Daily Usage
  - entity: sensor.globird_energy_qb121208805_daily_total_cost
    name: Daily Cost
```

## Energy Dashboard

You can add the daily usage sensor to the Home Assistant Energy Dashboard for tracking your electricity consumption over time.

## Troubleshooting

### Authentication Failed
- Ensure your email and password are correct
- Try logging into the [Globird Energy portal](https://myaccount.globirdenergy.com.au/) to verify your credentials

### No Data
- Data is typically available after 6 AM for the previous day
- Smart meter data may have a delay of 1-2 days

## Privacy & Security

- Your credentials are stored locally in Home Assistant
- Password is encrypted using RSA-OAEP before being sent to the Globird API
- No data is sent to any third parties

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This is an unofficial integration and is not affiliated with Globird Energy. Use at your own risk.
