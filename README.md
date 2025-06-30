# Invoice OCR Processor

A professional-grade application for extracting and processing invoice data using Optical Character Recognition (OCR). This tool supports multiple file formats, dual OCR engines, and advanced field extraction with a modern, user-friendly interface.

## System Requirements

### Python Dependencies
The following Python packages are required. Install them using the provided `requirements.txt`.

```
PyQt5==5.15.10
pytesseract==0.3.10
easyocr==1.7.0
opencv-python==4.8.1.78
PyMuPDF==1.23.10
Pillow==10.1.0
numpy==1.24.4
```

## Installation Instructions

### 1. System Dependencies

#### Windows
1. **Install Tesseract OCR**:
   - Download from: [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
   - Install and add to system PATH (default: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
2. **Install Visual C++ Redistributable** (if not already installed)

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng python3-tk libgl1-mesa-glx
```

#### macOS
```bash
brew install tesseract
```

### 2. Python Environment Setup
```bash
# Create a virtual environment
python -m venv invoice_ocr_env

# Activate the virtual environment
# Windows:
invoice_ocr_env\Scripts\activate
# Linux/macOS:
source invoice_ocr_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Application
```bash
python invoice_ocr_app.py
```

## Features

### Core Functionality
- **Multi-format Support**: Processes JPG, PNG, PDF, TIFF, and BMP files
- **Dual OCR Engines**: Utilizes Tesseract and EasyOCR for robust text extraction
- **Intelligent Field Extraction**: Automatically identifies key invoice fields
- **Professional UI**: Modern PyQt5 interface with tabbed navigation and real-time updates
- **Export Capabilities**: Supports CSV and JSON formats with complete data retention

### Extracted Fields
- Invoice Number
- Invoice Date and Due Date
- Vendor Name and Address
- Bill To Information
- Currency Detection (£, $, €, GBP, USD, EUR)
- Financial Details (Subtotal, Tax Amount, Total Amount)
- Full Raw Text

### User Interface Components
1. **Control Panel**: File selection, OCR engine selection, and processing controls
2. **Current Extraction Tab**: Real-time view of extracted fields and full text
3. **All Results Tab**: Table view of all processed invoices
4. **Export Data Tab**: Preview and export options for processed data

## Usage Instructions
1. **Select File**: Click "Select Invoice File" to choose an invoice (image or PDF)
2. **Choose OCR Engine**: Select Tesseract or EasyOCR
3. **Process Invoice**: Click "Process Invoice" to initiate extraction
4. **Review Results**: View extracted data in the "Current Extraction" tab
5. **Export Data**: Save results as CSV or JSON from the "Export Data" tab

## Troubleshooting

### Common Issues
- **"Tesseract not found" Error**:
  - Verify Tesseract is installed and added to the system PATH
  - For Windows, configure pytesseract explicitly:
    ```python
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    ```
- **Suboptimal OCR Results**:
  - Switch between Tesseract and EasyOCR for better performance
  - Use high-resolution, well-lit images
  - PDFs are automatically converted to high-resolution images
- **Memory Issues with Large PDFs**:
  - The application processes only the first page of multi-page PDFs
  - Convert large PDFs to images externally for improved performance

### Performance Optimization
- Use high-resolution, clear images for optimal OCR accuracy
- EasyOCR is recommended for noisy or low-quality images
- Tesseract is faster but performs best with clean inputs

## Project Structure
```
invoice_ocr_processor/
├── invoice_ocr_app.py       # Main application script
├── requirements.txt         # Python dependencies
├── README.md               # Documentation
└── temp_page_*.png         # Temporary image files (auto-deleted)
```

## Advanced Configuration

### Tesseract Settings
- **OCR Engine Mode (OEM)**: 3 (Default + LSTM)
- **Page Segmentation Mode (PSM)**: 6 (Uniform text block)
- **Character Whitelist**: Configured for enhanced accuracy

### Image Preprocessing
- Grayscale conversion
- Non-local Means Denoising for noise reduction
- Adaptive thresholding for improved text contrast
- Morphological operations for text cleanup

## Support
For assistance:
1. Refer to the troubleshooting section
2. Verify dependency installation
3. Test with high-quality invoice images
4. Review console output for detailed error messages

## License
This software is provided as-is for professional use under the MIT License.

## Technical Highlights
- **Threaded Processing**: Ensures a responsive UI during OCR operations
- **Memory Efficiency**: Automatically cleans up temporary files
- **Cross-platform Compatibility**: Supports Windows, Linux, and macOS
- **Robust Error Handling**: Gracefully manages various file formats and OCR errors
- **Professional Codebase**: Modular, maintainable, and well-documented

## Supported Invoice Types
The application processes:
- Professional service invoices (e.g., car repair invoices)
- Template-based invoices (e.g., purchasing invoices)
- Standard business invoices (e.g., company invoices)