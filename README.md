# Automatic Continue Detection System

An intelligent automation tool that automatically detects "Continue" messages on screen and performs clicks when found. This system uses advanced OCR (Optical Character Recognition) technology with multiple image enhancement techniques to reliably detect text patterns and execute automated responses.

## 🚀 Features

- **Automatic Screen Scanning**: Continuously monitors the screen for target text patterns
- **Advanced OCR Processing**: Multiple image enhancement techniques for improved text detection accuracy
- **Intelligent Click Automation**: Safe coordinate validation and automatic clicking with retry mechanisms
- **Robust Error Handling**: Comprehensive error recovery and retry logic
- **Performance Monitoring**: Real-time statistics and performance tracking
- **Configurable Settings**: Easily customizable scan intervals, retry limits, and detection patterns
- **Comprehensive Logging**: Detailed logging system with timestamps and performance metrics
- **Modular Architecture**: Clean, maintainable code structure with separated responsibilities

## 📋 Requirements

### System Requirements
- Windows 10/11 (primary support)
- Python 3.8 or higher
- Tesseract OCR installed
- Screen resolution: 1920x1080 or higher (recommended)

### Python Dependencies
- `pyautogui>=0.9.54` - Screen capture and mouse automation
- `pytesseract>=0.3.13` - OCR text extraction
- `Pillow>=10.0.0` - Image processing
- `opencv-python>=4.8.0` - Advanced image enhancement
- `numpy>=1.24.0` - Numerical operations for image processing

## 🛠️ Installation

### 1. Install Tesseract OCR

Download and install Tesseract OCR from the official repository:
- Visit: https://github.com/UB-Mannheim/tesseract/wiki
- Download the Windows installer
- Install to the default location: `C:\Program Files\Tesseract-OCR\`

### 2. Clone the Repository

```bash
git clone <repository-url>
cd detect-continue
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

Run the system validation:

```bash
python detect.py --validate
```

## ⚙️ Configuration

The system can be configured by modifying `config.py`:

### Key Configuration Options

```python
# Scanning interval (seconds)
SCAN_INTERVAL = 120  # Scan every 2 minutes

# Target text pattern (regex)
TARGET_PATTERN = r'continue'
TARGET_END_WORD = 'continue'

# Retry configurations
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Failure handling
MAX_CONSECUTIVE_FAILURES = 5
EXTENDED_WAIT_TIME = 300  # 5 minutes

# OCR confidence threshold
MIN_CONFIDENCE_THRESHOLD = 30
```

### Tesseract Path Configuration

If Tesseract is installed in a non-standard location, update the path in `config.py`:

```python
TESSERACT_CMD = r'C:\Your\Custom\Path\tesseract.exe'
```

## 🚀 Usage

### Basic Usage

Start the automatic detection system:

```bash
python detect.py
```

The system will:
1. Initialize all components
2. Start continuous screen monitoring
3. Scan for the target pattern every 2 minutes
4. Automatically click when the pattern is detected
5. Log all activities with timestamps

### Command Line Options

```bash
# Run with debug logging
python detect.py --debug

# Validate system requirements
python detect.py --validate

# Run single scan (for testing)
python detect.py --single-scan
```

### Stopping the System

- **Keyboard Interrupt**: Press `Ctrl+C` to gracefully stop
- **Emergency Stop**: Move mouse to top-left corner (failsafe)
- **System Shutdown**: The system will automatically stop on system shutdown

## 📊 Monitoring and Logs

### Log Files

The system creates detailed logs in:
- `automation_log.txt` - Main activity log with timestamps
- Console output - Real-time status updates

### Performance Statistics

The system tracks:
- Total scans performed
- Successful detections
- Click success rate
- Average scan time
- System uptime
- Error rates

### Status Reports

Automatic status reports are generated every 10 scans, including:
- System health status
- Performance metrics
- Recent activity summary

## 🏗️ Architecture

The system is built with a modular architecture:

```
detect.py              # Main entry point and orchestration
├── config.py          # Global configurations
├── logger.py          # Logging and statistics
├── scanner.py         # Main scanning logic
├── image_processing.py # Image capture and enhancement
├── ocr_engine.py      # Text extraction and processing
└── coordinate_manager.py # Click automation and validation
```

### Key Components

- **Scanner**: Orchestrates the scanning process and handles retries
- **Image Processing**: Captures screenshots and applies enhancement filters
- **OCR Engine**: Extracts text using multiple OCR configurations
- **Coordinate Manager**: Validates coordinates and performs safe clicks
- **Logger**: Comprehensive logging and performance monitoring

## 🔧 Troubleshooting

### Common Issues

**Tesseract not found**
```
Error: Tesseract not found
Solution: Verify Tesseract installation and update TESSERACT_CMD path
```

**Permission denied for screenshots**
```
Error: Screenshot capture failed
Solution: Run as administrator or check screen capture permissions
```

**High CPU usage**
```
Issue: Continuous high CPU usage
Solution: Increase SCAN_INTERVAL in config.py
```

**False positive detections**
```
Issue: Clicking on wrong elements
Solution: Adjust TARGET_PATTERN regex or increase MIN_CONFIDENCE_THRESHOLD
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
python detect.py --debug
```

This will provide:
- Detailed OCR results
- Image processing steps
- Coordinate validation details
- Performance timing information

## 🔒 Safety Features

- **Failsafe Protection**: Move mouse to corner to emergency stop
- **Coordinate Validation**: Ensures clicks are within screen bounds
- **Retry Limits**: Prevents infinite retry loops
- **Error Recovery**: Graceful handling of system errors
- **Performance Monitoring**: Automatic detection of system health issues

## 📈 Performance Optimization

### For Better Accuracy
- Ensure good screen contrast
- Use standard fonts when possible
- Avoid overlapping windows
- Maintain consistent screen resolution

### For Better Performance
- Increase scan intervals for less frequent checking
- Adjust OCR confidence thresholds
- Monitor system resource usage
- Use SSD storage for faster image processing

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Check code style
flake8 *.py
```

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section
2. Enable debug mode for detailed logs
3. Review the log files for error messages
4. Open an issue with detailed information about your setup

## 🔄 Version History

- **v1.0.0** - Initial release with core functionality
  - Automatic screen scanning
  - OCR-based text detection
  - Automated clicking
  - Comprehensive logging
  - Modular architecture

---

**Note**: This tool is designed for automation purposes. Please ensure you comply with the terms of service of any applications you use this with, and use responsibly.