# Globird Energy Home Assistant Integration

Custom files from initial reverse engineering:
- find_key.py - Can be deleted (exploration script)
- globird_api.py - Can be deleted (converted to Home Assistant integration)

## Repository Structure

```
├── custom_components/
│   └── globird_energy/
│       ├── __init__.py          # Integration setup
│       ├── api.py               # API client
│       ├── config_flow.py       # UI configuration
│       ├── const.py             # Constants
│       ├── coordinator.py       # Data coordinator
│       ├── manifest.json        # Integration manifest
│       ├── sensor.py            # Sensor entities
│       ├── strings.json         # UI strings
│       └── translations/
│           └── en.json          # English translations
├── hacs.json                    # HACS configuration
├── LICENSE                      # MIT License
└── README.md                    # Documentation
```

## Development

To test locally:
1. Copy `custom_components/globird_energy` to your Home Assistant config folder
2. Restart Home Assistant
3. Add the integration via Settings → Devices & Services
