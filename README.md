# The Bird for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ekul135/the-bird.svg)](https://github.com/ekul135/the-bird/releases)

A Home Assistant custom integration that fetches your daily electricity usage and cost data from your energy provider portal.

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

After setup, the following sensors will be available:

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.the_bird_*_daily_usage` | Yesterday's total electricity usage | kWh |
| `sensor.the_bird_*_daily_usage_cost` | Yesterday's usage cost | AUD |
| `sensor.the_bird_*_daily_supply_charge` | Daily supply charge | AUD |
| `sensor.the_bird_*_daily_total_cost` | Total daily cost | AUD |

## Example Dashboard Card

```yaml
type: entities
title: The Bird Energy
entities:
  - entity: sensor.the_bird_qb121208805_daily_usage
    name: Daily Usage
  - entity: sensor.the_bird_qb121208805_daily_total_cost
    name: Daily Cost
```

## Energy Dashboard

You can add the daily usage sensor to the Home Assistant Energy Dashboard for tracking your electricity consumption over time.

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
