# UPS HAT (C) Monitor

A terminal-based monitoring script for the [Waveshare UPS HAT (C)](https://www.waveshare.com/wiki/UPS_HAT_(C)) on Raspberry Pi. Reads real-time data from the onboard INA219 sensor via I²C and displays a live-updating panel with battery status, power metrics, runtime estimate, and automatic safe shutdown.

![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- Live-updating terminal panel — refreshes in place, no scrolling
- Color-coded display using ANSI escape codes (amber/blue scheme)
- Battery level progress bar
- Charging / On battery status detection
- Remaining runtime estimate based on current draw
- Automatic safe shutdown when battery reaches a critical level
- Configurable thresholds, capacity, and refresh interval

## Preview

```
╔═════════════════════╗
║   Waveshare UPS HAT (C) Monitor   ║
╠═════════════════════╣
║  PSU Voltage             4.023 V  ║
║  Shunt Voltage        0.001240 V  ║
║  Load Voltage            4.021 V  ║
║  Current               -0.3420 A  ║
║  Power                   1.358 W  ║
╠═════════════════════╣
║  █████████░░░░░░    76.3%  ║
║  Status               On battery  ║
║  Runtime                  9h 28m  ║
╚═════════════════════╝
```

---

## Requirements

### Hardware

- Raspberry Pi (any model with I²C support)
- [Waveshare UPS HAT (C)](https://www.waveshare.com/wiki/UPS_HAT_(C))
- LiPo/Li-Ion battery connected to the HAT

### Software

- Python 3.7+
- `smbus` library

```bash
sudo apt install python3-smbus
```

### Enable I²C

```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

---

## Installation

```bash
git clone https://github.com/your-username/ups-hat-c-monitor.git
cd ups-hat-c-monitor
```

No additional dependencies beyond `smbus`, which is available in the default Raspberry Pi OS repositories.

---

## Usage

```bash
python3 UPS_HAT_C.py
```

The panel updates in place every 2 seconds. Press `Ctrl+C` to exit.

> **Note:** The auto-shutdown feature requires `sudo` privileges to call `systemctl poweroff`. Run with `sudo` or configure passwordless sudo for that command.

---

## Configuration

All user-adjustable settings are at the top of the `if __name__ == '__main__':` block:

| Setting | Default | Description |
|---|---|---|
| `BATTERY_CAPACITY_MAH` | `1000` | Total battery capacity in mAh. Set this to match your cell — the default is for a single LiPo 803040 3.7V 1000mAh |
| `SHUTDOWN_THRESHOLD` | `10` | Battery percentage that arms the shutdown sequence |
| `SHUTDOWN_GRACE` | `7` | Number of consecutive readings below the threshold required to confirm shutdown (avoids false triggers from voltage spikes) |
| `READ_INTERVAL` | `2` | Seconds between each sensor reading |
| `BLOCK_LINES` | `13` | Number of lines in the display panel. Update this if you add or remove fields |

---

## How It Works

### Sensor

The UPS HAT (C) uses an **INA219** current/power monitor IC connected via I²C at address `0x43`. The script communicates with it directly through the `smbus` library without any additional abstraction layer.

### Battery percentage

Estimated using a linear interpolation of the load voltage against the Li-Ion discharge curve:

```
p = (load_voltage - 3.0) / 1.2 * 100
```

This maps `3.0 V → 0%` and `4.2 V → 100%`, which covers the safe operating range of standard Li-Ion and LiPo cells.

### Charging detection

The INA219 reports **negative current** when the system is drawing from the battery and **positive current** when the battery is being charged by an external supply. The `Status` field is derived directly from this sign.

### Runtime estimate

Calculated as:

```
runtime = (capacity_mAh × battery_%) / |current_mA|
```

Accuracy depends on `BATTERY_CAPACITY_MAH` being correctly set and on a reasonably stable load. Treat it as an order-of-magnitude estimate rather than a precise countdown.

### Auto shutdown

When the battery percentage stays at or below `SHUTDOWN_THRESHOLD` for `SHUTDOWN_GRACE` consecutive readings, the script prints a warning and calls:

```bash
sudo systemctl poweroff
```

The grace counter prevents a spurious shutdown caused by momentary voltage dips.

---

## License

MIT — feel free to use, modify, and distribute.

---

## Author

**PP5KX** — Amateur radio operator, Mafra, Santa Catarina, Brazil  
[pp5kx.net](https://pp5kx.net)
