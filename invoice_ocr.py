import sys
import os
import re
import json
import csv
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import pytesseract
import easyocr
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                            QTextEdit, QLineEdit, QComboBox, QTableWidget, 
                            QTableWidgetItem, QFileDialog, QMessageBox, 
                            QProgressBar, QTabWidget, QGroupBox, QSplitter,
                            QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon
import fitz  # PyMuPDF for PDF processing

class InvoiceProcessor:
    def __init__(self):
        self.easyocr_reader = easyocr.Reader(['en'])
        
    def preprocess_image(self, image_path):
        """Preprocess image for better OCR results"""
        image = cv2.imread(image_path)
        if image is None:
            return None
            
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        # Morphological operations to clean up
        kernel = np.ones((1,1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def extract_text_tesseract(self, image_path):
        """Extract text using Tesseract OCR"""
        try:
            processed_image = self.preprocess_image(image_path)
            if processed_image is None:
                return ""
            
            # Configure Tesseract for better results
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/()£$€@# '
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            return text.strip()
        except Exception as e:
            print(f"Tesseract OCR error: {e}")
            return ""
    
    def extract_text_easyocr(self, image_path):
        """Extract text using EasyOCR"""
        try:
            results = self.easyocr_reader.readtext(image_path)
            text_lines = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3:  # Filter low confidence results
                    text_lines.append(text)
            return '\n'.join(text_lines)
        except Exception as e:
            print(f"EasyOCR error: {e}")
            return ""
    
    def pdf_to_images(self, pdf_path):
        """Convert PDF pages to images"""
        try:
            doc = fitz.open(pdf_path)
            images = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                mat = fitz.Matrix(2, 2)  # Scale factor for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Save temporary image
                temp_path = f"temp_page_{page_num}.png"
                with open(temp_path, "wb") as f:
                    f.write(img_data)
                images.append(temp_path)
            doc.close()
            return images
        except Exception as e:
            print(f"PDF conversion error: {e}")
            return []
    
    def extract_invoice_fields(self, text):
        """Extract key invoice fields from text"""
        fields = {
            'invoice_number': '',
            'invoice_date': '',
            'due_date': '',
            'vendor_name': '',
            'vendor_address': '',
            'bill_to': '',
            'total_amount': '',
            'subtotal': '',
            'tax_amount': '',
            'currency': ''
        }
        
        text_lines = text.split('\n')
        text_upper = text.upper()
        
        # Extract Invoice Number
        invoice_patterns = [
            r'INVOICE\s*(?:NO|NUMBER|#)?\s*:?\s*([A-Z0-9\-]+)',
            r'INV\s*(?:NO|#)?\s*:?\s*([A-Z0-9\-]+)',
            r'INVOICE\s+([A-Z0-9\-]+)',
            r'#\s*([A-Z0-9\-]+)'
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, text_upper)
            if match:
                fields['invoice_number'] = match.group(1).strip()
                break
        
        # Extract Dates
        date_patterns = [
            r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})',
            r'(\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})'
        ]
        
        dates_found = []
        for pattern in date_patterns:
            dates_found.extend(re.findall(pattern, text))
        
        if dates_found:
            fields['invoice_date'] = dates_found[0] if len(dates_found) > 0 else ''
            fields['due_date'] = dates_found[1] if len(dates_found) > 1 else ''
        
        # Extract Vendor Information (first few lines usually contain vendor info)
        vendor_lines = []
        for i, line in enumerate(text_lines[:10]):
            if line.strip() and not any(keyword in line.upper() for keyword in ['INVOICE', 'BILL TO', 'DATE']):
                vendor_lines.append(line.strip())
                if len(vendor_lines) >= 3:
                    break
        
        if vendor_lines:
            fields['vendor_name'] = vendor_lines[0]
            fields['vendor_address'] = ' '.join(vendor_lines[1:])
        
        # Extract Bill To information
        bill_to_start = -1
        for i, line in enumerate(text_lines):
            if 'BILL TO' in line.upper():
                bill_to_start = i
                break
        
        if bill_to_start >= 0:
            bill_to_lines = []
            for i in range(bill_to_start + 1, min(bill_to_start + 6, len(text_lines))):
                if text_lines[i].strip():
                    bill_to_lines.append(text_lines[i].strip())
                else:
                    break
            fields['bill_to'] = ' '.join(bill_to_lines)
        
        # Extract Amounts
        amount_patterns = [
            r'TOTAL\s*(?:GBP|USD|EUR|\$|£|€)?:?\s*([£$€]?\s*[\d,]+\.?\d*)',
            r'AMOUNT\s+DUE\s*(?:GBP|USD|EUR|\$|£|€)?:?\s*([£$€]?\s*[\d,]+\.?\d*)',
            r'SUBTOTAL\s*:?\s*([£$€]?\s*[\d,]+\.?\d*)',
            r'TAX\s*(?:\d+%)?:?\s*([£$€]?\s*[\d,]+\.?\d*)'
        ]
        
        # Find currency
        currency_match = re.search(r'[£$€]|GBP|USD|EUR', text_upper)
        if currency_match:
            currency_symbols = {'£': 'GBP', '$': 'USD', '€': 'EUR'}
            fields['currency'] = currency_symbols.get(currency_match.group(), currency_match.group())
        
        # Extract total amount
        for pattern in amount_patterns[:2]:  # Total and Amount Due patterns
            match = re.search(pattern, text_upper)
            if match:
                amount = re.sub(r'[£$€,\s]', '', match.group(1))
                if amount.replace('.', '').isdigit():
                    fields['total_amount'] = amount
                    break
        
        # Extract subtotal
        match = re.search(amount_patterns[2], text_upper)
        if match:
            amount = re.sub(r'[£$€,\s]', '', match.group(1))
            if amount.replace('.', '').isdigit():
                fields['subtotal'] = amount
        
        # Extract tax amount
        match = re.search(amount_patterns[3], text_upper)
        if match:
            amount = re.sub(r'[£$€,\s]', '', match.group(1))
            if amount.replace('.', '').isdigit():
                fields['tax_amount'] = amount
        
        return fields

class OCRWorker(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, file_path, ocr_engine):
        super().__init__()
        self.file_path = file_path
        self.ocr_engine = ocr_engine
        self.processor = InvoiceProcessor()
    
    def run(self):
        try:
            self.progress.emit("Starting OCR processing...")
            
            if self.file_path.lower().endswith('.pdf'):
                self.progress.emit("Converting PDF to images...")
                images = self.processor.pdf_to_images(self.file_path)
                if not images:
                    self.error.emit("Failed to convert PDF to images")
                    return
                
                # Process first page for now
                image_path = images[0]
            else:
                image_path = self.file_path
            
            self.progress.emit(f"Extracting text using {self.ocr_engine}...")
            
            if self.ocr_engine == "Tesseract":
                full_text = self.processor.extract_text_tesseract(image_path)
            else:  # EasyOCR
                full_text = self.processor.extract_text_easyocr(image_path)
            
            self.progress.emit("Extracting invoice fields...")
            fields = self.processor.extract_invoice_fields(full_text)
            
            result = {
                'full_text': full_text,
                'fields': fields,
                'file_path': self.file_path
            }
            
            self.progress.emit("OCR processing completed!")
            self.finished.emit(result)
            
            # Clean up temporary files
            if self.file_path.lower().endswith('.pdf'):
                for img_path in images:
                    try:
                        os.remove(img_path)
                    except:
                        pass
                        
        except Exception as e:
            self.error.emit(f"OCR processing failed: {str(e)}")

class InvoiceOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processed_invoices = []
        self.current_result = None
        self.initUI()
        self.setStyleSheet(self.get_stylesheet())
    
    def initUI(self):
        self.setWindowTitle("Professional Invoice OCR Processor")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to process invoices")
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        main_layout.addWidget(self.status_label)
        
        # Main content area with tabs
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_extraction_tab()
        self.create_results_tab()
        self.create_export_tab()
        
        # Initialize worker thread
        self.worker = None
    
    def create_header(self):
        header = QFrame()
        header.setFrameStyle(QFrame.Box)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #3498db);
                border: none;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout()
        
        title = QLabel("Invoice OCR Processor")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
                background: transparent;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Professional OCR solution for invoice data extraction")
        subtitle.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                font-size: 14px;
                background: transparent;
            }
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        header.setLayout(layout)
        
        return header
    
    def create_control_panel(self):
        panel = QGroupBox("Control Panel")
        layout = QHBoxLayout()
        
        # File selection
        self.file_label = QLabel("No file selected")
        self.file_label.setMinimumWidth(300)
        self.select_file_btn = QPushButton("Select Invoice File")
        self.select_file_btn.clicked.connect(self.select_file)
        
        # OCR engine selection
        ocr_label = QLabel("OCR Engine:")
        self.ocr_combo = QComboBox()
        self.ocr_combo.addItems(["Tesseract", "EasyOCR"])
        
        # Process button
        self.process_btn = QPushButton("Process Invoice")
        self.process_btn.clicked.connect(self.process_invoice)
        self.process_btn.setEnabled(False)
        
        # Clear button
        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self.clear_results)
        
        layout.addWidget(QLabel("File:"))
        layout.addWidget(self.file_label)
        layout.addWidget(self.select_file_btn)
        layout.addWidget(ocr_label)
        layout.addWidget(self.ocr_combo)
        layout.addWidget(self.process_btn)
        layout.addWidget(self.clear_btn)
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def create_extraction_tab(self):
        tab = QWidget()
        layout = QHBoxLayout()
        
        # Left side - Extracted fields
        fields_group = QGroupBox("Extracted Invoice Fields")
        fields_layout = QGridLayout()
        
        # Create field inputs
        self.field_inputs = {}
        fields = [
            ("Invoice Number:", "invoice_number"),
            ("Invoice Date:", "invoice_date"),
            ("Due Date:", "due_date"),
            ("Vendor Name:", "vendor_name"),
            ("Vendor Address:", "vendor_address"),
            ("Bill To:", "bill_to"),
            ("Currency:", "currency"),
            ("Subtotal:", "subtotal"),
            ("Tax Amount:", "tax_amount"),
            ("Total Amount:", "total_amount")
        ]
        
        for i, (label, field_key) in enumerate(fields):
            label_widget = QLabel(label)
            input_widget = QLineEdit()
            input_widget.setReadOnly(True)
            self.field_inputs[field_key] = input_widget
            
            fields_layout.addWidget(label_widget, i, 0)
            fields_layout.addWidget(input_widget, i, 1)
        
        fields_group.setLayout(fields_layout)
        
        # Right side - Full extracted text
        text_group = QGroupBox("Full Extracted Text")
        text_layout = QVBoxLayout()
        
        self.full_text_display = QTextEdit()
        self.full_text_display.setReadOnly(True)
        self.full_text_display.setFont(QFont("Consolas", 10))
        
        text_layout.addWidget(self.full_text_display)
        text_group.setLayout(text_layout)
        
        # Add to splitter for resizing
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(fields_group)
        splitter.addWidget(text_group)
        splitter.setSizes([400, 500])
        
        layout.addWidget(splitter)
        tab.setLayout(layout)
        
        self.tab_widget.addTab(tab, "Current Extraction")
    
    def create_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setHorizontalHeaderLabels([
            "File", "Invoice #", "Date", "Vendor", "Bill To", 
            "Currency", "Subtotal", "Tax", "Total", "Status"
        ])
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(QLabel("Processed Invoices:"))
        layout.addWidget(self.results_table)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "All Results")
    
    def create_export_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        export_group = QGroupBox("Export Options")
        export_layout = QVBoxLayout()
        
        # Export buttons
        button_layout = QHBoxLayout()
        
        self.export_csv_btn = QPushButton("Export to CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        
        self.export_json_btn = QPushButton("Export to JSON")
        self.export_json_btn.clicked.connect(self.export_json)
        
        button_layout.addWidget(self.export_csv_btn)
        button_layout.addWidget(self.export_json_btn)
        button_layout.addStretch()
        
        # Export preview
        self.export_preview = QTextEdit()
        self.export_preview.setReadOnly(True)
        self.export_preview.setPlaceholderText("Export preview will appear here...")
        
        export_layout.addLayout(button_layout)
        export_layout.addWidget(QLabel("Export Preview:"))
        export_layout.addWidget(self.export_preview)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Export Data")
    
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Invoice File", "", 
            "Image and PDF files (*.jpg *.jpeg *.png *.bmp *.tiff *.pdf)"
        )
        
        if file_path:
            self.file_label.setText(os.path.basename(file_path))
            self.file_path = file_path
            self.process_btn.setEnabled(True)
    
    def process_invoice(self):
        if not hasattr(self, 'file_path'):
            QMessageBox.warning(self, "Warning", "Please select a file first!")
            return
        
        # Disable UI elements
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start OCR processing
        self.worker = OCRWorker(self.file_path, self.ocr_combo.currentText())
        self.worker.finished.connect(self.on_ocr_finished)
        self.worker.progress.connect(self.update_status)
        self.worker.error.connect(self.on_ocr_error)
        self.worker.start()
    
    def on_ocr_finished(self, result):
        self.current_result = result
        
        # Update extracted fields
        for field_key, value in result['fields'].items():
            if field_key in self.field_inputs:
                self.field_inputs[field_key].setText(str(value))
        
        # Update full text display
        self.full_text_display.setPlainText(result['full_text'])
        
        # Add to results table
        self.add_to_results_table(result)
        
        # Add to processed invoices list
        self.processed_invoices.append(result)
        
        # Update export preview
        self.update_export_preview()
        
        # Reset UI
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        self.status_label.setText("Processing completed successfully!")
        
        # Switch to extraction tab
        self.tab_widget.setCurrentIndex(0)
    
    def on_ocr_error(self, error_msg):
        QMessageBox.critical(self, "OCR Error", f"An error occurred during processing:\n{error_msg}")
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        self.status_label.setText("Processing failed!")
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def add_to_results_table(self, result):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        fields = result['fields']
        items = [
            os.path.basename(result['file_path']),
            fields.get('invoice_number', ''),
            fields.get('invoice_date', ''),
            fields.get('vendor_name', ''),
            fields.get('bill_to', ''),
            fields.get('currency', ''),
            fields.get('subtotal', ''),
            fields.get('tax_amount', ''),
            fields.get('total_amount', ''),
            "Processed"
        ]
        
        for col, item in enumerate(items):
            self.results_table.setItem(row, col, QTableWidgetItem(str(item)))
    
    def clear_results(self):
        # Clear field inputs
        for input_widget in self.field_inputs.values():
            input_widget.clear()
        
        # Clear text display
        self.full_text_display.clear()
        
        # Clear results table
        self.results_table.setRowCount(0)
        
        # Clear processed invoices
        self.processed_invoices.clear()
        
        # Clear export preview
        self.export_preview.clear()
        
        # Reset status
        self.status_label.setText("Results cleared. Ready to process invoices.")
    
    def export_csv(self):
        if not self.processed_invoices:
            QMessageBox.warning(self, "Warning", "No data to export!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV File", f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['file_name', 'invoice_number', 'invoice_date', 'due_date',
                                'vendor_name', 'vendor_address', 'bill_to', 'currency',
                                'subtotal', 'tax_amount', 'total_amount']
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for result in self.processed_invoices:
                        row = result['fields'].copy()
                        row['file_name'] = os.path.basename(result['file_path'])
                        writer.writerow(row)
                
                QMessageBox.information(self, "Success", f"Data exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{str(e)}")
    
    def export_json(self):
        if not self.processed_invoices:
            QMessageBox.warning(self, "Warning", "No data to export!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save JSON File", f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )
        
        if file_path:
            try:
                export_data = []
                for result in self.processed_invoices:
                    data = {
                        'file_name': os.path.basename(result['file_path']),
                        'extraction_timestamp': datetime.now().isoformat(),
                        'fields': result['fields'],
                        'full_text': result['full_text']
                    }
                    export_data.append(data)
                
                with open(file_path, 'w', encoding='utf-8') as jsonfile:
                    json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "Success", f"Data exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export JSON:\n{str(e)}")
    
    def update_export_preview(self):
        if not self.processed_invoices:
            return
        
        # Show preview of the last processed invoice
        result = self.processed_invoices[-1]
        preview_data = {
            'file_name': os.path.basename(result['file_path']),
            'fields': result['fields']
        }
        
        preview_text = json.dumps(preview_data, indent=2, ensure_ascii=False)
        self.export_preview.setPlainText(preview_text)
    
    def get_stylesheet(self):
        return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 10px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QPushButton {
            background-color: #3498db;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #2980b9;
        }
        
        QPushButton:pressed {
            background-color: #21618c;
        }
        
        QPushButton:disabled {
            background-color: #bdc3c7;
        }
        
        QLineEdit {
            padding: 8px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
        }
        
        QLineEdit:focus {
            border-color: #3498db;
        }
        
        QTextEdit {
            border: 2px solid #ddd;
            border-radius: 4px;
            background-color: white;
            font-family: 'Consolas', 'Monaco', monospace;
        }
        
        QComboBox {
            padding: 8px;
            border: 2px solid #ddd;
            border-radius: 4px;
            min-width: 100px;
        }
        
        QTableWidget {
            border: 1px solid #ddd;
            background-color: white;
            alternate-background-color: #f9f9f9;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
        
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #e1e1e1;
            border: 1px solid #c0c0c0;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
        }
        
        QProgressBar {
            border: 2px solid #ddd;
            border-radius: 4px;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 2px;
        }
        """

def main():
    app = QApplication(sys.argv)
    
    # Check if required packages are available
    try:
        import pytesseract
        import easyocr
        import cv2
        import fitz
    except ImportError as e:
        QMessageBox.critical(None, "Missing Dependencies", 
                           f"Required package not found: {e}\n\n"
                           "Please install the required packages:\n"
                           "pip install pytesseract easyocr opencv-python PyMuPDF pillow")
        sys.exit(1)
    
    # Check if Tesseract is installed
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        QMessageBox.warning(None, "Tesseract Not Found", 
                          "Tesseract OCR not found. Please install Tesseract:\n\n"
                          "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
                          "Linux: sudo apt-get install tesseract-ocr\n"
                          "macOS: brew install tesseract\n\n"
                          "EasyOCR will still work without Tesseract.")
    
    # Set application properties
    app.setApplicationName("Invoice OCR Processor")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Professional OCR Solutions")
    
    # Create and show main window
    window = InvoiceOCRApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()