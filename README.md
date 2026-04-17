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
| `sensor.the_bird_*_usage` | Grid electricity imported | kWh |
| `sensor.the_bird_*_usage_cost` | Cost of grid usage | AUD |
| `sensor.the_bird_*_solar` | Solar energy exported | kWh |
| `sensor.the_bird_*_solar_credit` | Credit from solar export | AUD |
| `sensor.the_bird_*_super_export` | Super Export energy | kWh |
| `sensor.the_bird_*_super_export_credit` | Super Export credit | AUD |
| `sensor.the_bird_*_supply` | Daily supply charge | AUD |
| `sensor.the_bird_*_zerohero` | ZeroHero credit | AUD |
| `sensor.the_bird_*_net_cost` | Net daily cost (negative = credit) | AUD |

## Example Dashboard Card

```yaml
type: entities
title: The Bird Energy
entities:
  - entity: sensor.the_bird_qb121208805_usage
    name: Usage
  - entity: sensor.the_bird_qb121208805_solar
    name: Solar
  - entity: sensor.the_bird_qb121208805_net_cost
    name: Net Cost
```

## Energy Dashboard

You can add the grid usage and solar export sensors to the Home Assistant Energy Dashboard for tracking your electricity consumption and solar production over time.

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
