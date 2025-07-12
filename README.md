# RMCS App - Resistivity Measurement Control System

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

**RMCS App** is a professional desktop application for controlling and managing geoelectrical resistivity measurements. It supports various electrode array configurations and provides a user-friendly interface for field data acquisition.

## 🚀 Key Features

- **📡 Serial Communication**: COM port connectivity with various baud rates
- **⚡ Multi-Array Support**: Wenner, Schlumberger, and Dipole-dipole configurations
- **🎛️ Dual Mode**: Automatic and Manual operation modes
- **📊 Real-time Data**: Live data table and plotting
- **💾 Data Export**: Export to CSV and plot images
- **🔧 Project Management**: Manage projects with names and timestamps

## 📋 System Requirements

### Hardware
- Windows 10/11 (32-bit or 64-bit)
- Serial port (COM) for hardware communication
- Minimum 4GB RAM (recommended)
- 100MB disk space

### Software
- Python 3.8+ (for running source code)
- Or use the pre-built executable file

## 🛠️ Installation and Build

### Method 1: Running from Source Code

1. **Clone or download this project**
```bash
git clone <repository-url>
cd rmcs-gui-tkinter
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python RMCS_App.py
```

### Method 2: Build Executable (.exe)

To create an executable file that can run without Python installed:

#### 🔧 Using Batch File (Recommended)

This project includes an `install.bat` file to simplify the build process:

```batch
# Contents of install.bat
pyinstaller --onefile --windowed --name "RMCS_App" RMCS_App.py
```

**How to use:**

1. **Ensure dependencies are installed**
```bash
pip install -r requirements.txt
```

2. **Run the batch file**
   - Double-click the `install.bat` file, or
   - Open Command Prompt/PowerShell in the project folder and run:
```bash
install.bat
```

3. **Find the executable file**
   - The `RMCS_App.exe` file will be created in the `dist/` folder
   - Copy this file to your desired location
   - Now it can be run with a double-click

#### 🔧 Manual Build (Alternative)

If you want to build manually without the batch file:

```bash
# Build with console (for debugging)
pyinstaller --onefile RMCS_App.py

# Build without console (for distribution)
pyinstaller --onefile --windowed RMCS_App.py

# Build with custom name
pyinstaller --onefile --windowed --name "RMCS_App" RMCS_App.py
```

### PyInstaller Parameters Used

- `--onefile`: Creates a single executable file
- `--windowed`: Runs without console window (GUI only)
- `--name "RMCS_App"`: Specifies the executable file name

## 📁 Project Structure

```
geolistrik/
├── RMCS_App.py          # Main source code
├── install.bat          # Batch file for building executable
├── README.md            # This documentation file
├── build/               # Temporary build folder (auto-generated)
├── dist/                # Output executable folder (auto-generated)
│   └── RMCS_App.exe    # Built executable file
└── RMCS_App.spec       # PyInstaller spec file (auto-generated)
```

## 🎯 Usage Guide

### Quick Start

1. **Hardware Connection**
   - Connect RMCS hardware via serial cable
   - Ensure serial port drivers are installed

2. **Launch Application**
   - Double-click `RMCS_App.exe` (if using executable)
   - Or run `python RMCS_App.py` (if from source)

3. **Setup Communication**
   - Select appropriate COM port
   - Set baud rate (default: 9600)
   - Click "Connect"

4. **Choose Measurement Configuration**
   - Wenner: for resistivity profiling
   - Schlumberger: for vertical sounding
   - Dipole-dipole: for high-resolution imaging

5. **Measurement Mode**
   - **Automatic Mode**: Load command file, set timer, start sequence
   - **Manual Mode**: Individual electrode control in real-time

### File Formats

#### Command File (.txt)
```
# Format: A, B, M, N (electrode positions)
1, 4, 2, 3
2, 5, 3, 4
3, 6, 4, 5
# Can use comma, space, or tab as delimiter
```

#### Data Export (.csv)
- Format: semicolon-delimited
- Headers: No, A, B, M, N, Current (mA), Voltage (mV), Resistivity (Ωm), Status
- Decimal separator: comma (,)

## 🔧 Troubleshooting

### Build Issues

1. **PyInstaller not found**
```bash
pip install pyinstaller
```

2. **Module not found during build**
```bash
pip install --upgrade setuptools wheel
pip install tkinter serial matplotlib
```

3. **Executable doesn't run**
   - Try building with `--onedir` instead of `--onefile` for debugging
   - Check antivirus (sometimes blocks executables)
   - Ensure all dependencies are properly installed

### Runtime Issues

1. **COM Port not detected**
   - Check Device Manager
   - Install appropriate serial port drivers
   - Restart application

2. **Connection timeout**
   - Check baud rate settings
   - Try different baud rates
   - Verify serial cable connections

3. **Data not received**
   - Verify hardware compatibility
   - Check electrode connections
   - Ensure proper command format

## 📦 Distribution

### For End Users
1. Use the `install.bat` to build the executable
2. Distribute only the `RMCS_App.exe` file from the `dist/` folder
3. No Python installation required on target machines

### For Developers
1. Include the source code (`RMCS_App.py`)
2. Include the `install.bat` for easy building
3. Provide this README for setup instructions

## 🔄 Array Configurations

### Wenner Array
- Equal electrode spacing
- Geometric factor: K = 2πa (where a = electrode spacing)
- Best for: General resistivity profiling

### Schlumberger Array
- Variable current electrode spacing
- Geometric factor: K = π[(AB/2)² - (MN/2)²]/MN
- Best for: Vertical electrical sounding

### Dipole-Dipole Array
- Separated current and potential dipoles
- Geometric factor: K = πn(n+1)(n+2)a (where n = separation factor)
- Best for: High-resolution subsurface imaging

## 📞 Support

For technical support, bug reports, or feature requests:
- Open an issue in this repository
- Contact the development team

## 📄 License

This project is developed for geophysical research purposes.

## 🔄 Version History

- **v1.0.1** (January 2025): Language localization update
  - Converted all Indonesian user interface text to English
  - Standardized error messages and dialog boxes
  - Improved international accessibility
- **v1.0.0** (January 2025): Initial release with full features

## 🌐 Recent Updates

### Language Translation (v1.0.1)
This version includes a complete language translation update:
- **User Interface**: All messagebox titles and content converted from Indonesian to English
- **Error Messages**: Standardized error reporting in English
- **File Dialogs**: Updated dialog titles for better international support
- **Debug Output**: All debug print statements already in English (no changes needed)

The translation covers:
- Warning/Error dialogs (e.g., "Peringatan" → "Warning")
- Success messages (e.g., "Sukses" → "Success") 
- Connection status messages
- File operation feedback
- Measurement status updates

This makes the application more accessible to international users while maintaining all original functionality.

---

**Thank you for using RMCS App v1.0.0!**
*Empowering geophysical research with professional measurement control.* 