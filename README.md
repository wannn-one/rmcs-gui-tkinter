# RMCS - Resistivity Multielectrode Control System

GUI application for controlling multielectrode resistivity measurement systems. Supports automatic and manual modes for geoelectrical surveys.

## Installation

1. **Install Python 3.10+** (if not already installed)

2. **Download/clone this project**

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python RMCS_App.py
   ```

## How to Use

### 1. Hardware Connection
- Connect multielectrode controller to computer via serial/USB
- Power on the controller
- In application: select COM port → set baud rate → click "Connect"
- Status changes to "Connected" (green)

### 2. Manual Mode (Individual Measurements)
- Select "Mode Manual"
- Enter electrode numbers A, B, M, N (1-64)
- Click "KIRIM MANUAL"
- Electrodes will activate according to settings

### 3. Automatic Mode (Sequence Measurements)
- Create command file (example: `test.txt`):
  ```
  1 4 2 3
  2 5 3 4
  3 6 4 5
  ```
- Click "Browse..." → select file → "Load CMD"
- Select "Mode Otomatis"
- Set timer (1-60 seconds)
- Click "START MEASUREMENT (AUTO)"

### 4. Measurement Results
- Data appears real-time in right table
- Columns: No, A, B, M, N, Current, Voltage, Resistivity, Status
- Progress bar shows sequence completion

## Command File Format

**Format per line: A B M N**
```
# Comments (ignored)
1 4 2 3    # Measurement 1
2 5 3 4    # Measurement 2
3 6 4 5    # Measurement 3
```

**Supported formats:**
- Space: `1 4 2 3`
- Comma: `1,4,2,3`
- Tab: `1	4	2	3`

## Important Controls

- **RESET SYSTEM**: Emergency button to stop all operations
- **Timer**: Measurement duration per electrode set
- **Progress bar**: Sequence completion status
- **Connection status**: Device connection indicator

## Array Configurations

- **Wenner**: General purpose, equal spacing
- **Schlumberger**: Vertical sounding, depth profiling  
- **Dipole-dipole**: High resolution, complex structures

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cannot connect | Check COM port, cable, device power |
| File won't load | Format must be 4 numbers per line (1-64) |
| GUI freezes | Click "RESET SYSTEM" |
| No data received | Check electrode connections and hardware compatibility |

---

**Requirements:**
- Python 3.10+
- Multielectrode controller with serial communication
- pyserial library 