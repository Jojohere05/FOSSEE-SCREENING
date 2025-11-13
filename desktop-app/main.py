import sys
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QMessageBox, QTabWidget, QGroupBox,
    QGridLayout, QTextEdit, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from config import API_BASE_URL

# Global token storage
AUTH_TOKEN = None


class UploadThread(QThread):
    """Background thread for file upload to avoid UI freezing"""
    upload_complete = pyqtSignal(dict)
    upload_error = pyqtSignal(str)
    
    def __init__(self, file_path, token):
        super().__init__()
        self.file_path = file_path
        self.token = token
    
    def run(self):
        try:
            with open(self.file_path, 'rb') as f:
                files = {'file': (os.path.basename(self.file_path), f, 'text/csv')}
                headers = {'Authorization': f'Token {self.token}'}
                
                response = requests.post(
                    f'{API_BASE_URL}/datasets/upload/',
                    files=files,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 201:
                    self.upload_complete.emit(response.json())
                else:
                    self.upload_error.emit(f"Upload failed: {response.text}")
        except Exception as e:
            self.upload_error.emit(str(e))


class MatplotlibCanvas(FigureCanvas):
    """Matplotlib canvas for embedding charts"""
    def __init__(self, parent=None, width=8, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)


class LoginWindow(QWidget):
    """Login window for authentication"""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Chemical Equipment Visualizer - Login')
        self.setGeometry(100, 100, 400, 250)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
            }
            QLineEdit {
                padding: 10px;
                border: 2px solid #cbd5e0;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QLabel {
                font-size: 14px;
                color: #2d3748;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel('🔬 Equipment Visualizer')
        title_font = QFont('Arial', 20, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1e40af; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Username
        username_label = QLabel('Username:')
        layout.addWidget(username_label)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Enter your username')
        layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel('Password:')
        layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Enter your password')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.login)
        layout.addWidget(self.password_input)
        
        # Login button
        login_btn = QPushButton('Login')
        login_btn.clicked.connect(self.login)
        login_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(login_btn)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #dc2626; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def login(self):
        global AUTH_TOKEN
        
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setText('Please enter both username and password')
            return
        
        try:
            self.status_label.setText('Logging in...')
            self.status_label.setStyleSheet("color: #2563eb;")
            QApplication.processEvents()
            
            response = requests.post(
                f'{API_BASE_URL}/auth/login/',
                json={'username': username, 'password': password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                AUTH_TOKEN = data['token']
                self.status_label.setText('Login successful!')
                self.status_label.setStyleSheet("color: #16a34a;")
                
                # Show main window
                self.main_window.show()
                self.main_window.load_history()
                self.close()
            else:
                self.status_label.setText('Invalid credentials')
                self.status_label.setStyleSheet("color: #dc2626;")
                
        except requests.exceptions.ConnectionError:
            self.status_label.setText('Cannot connect to server')
            self.status_label.setStyleSheet("color: #dc2626;")
        except Exception as e:
            self.status_label.setText(f'Error: {str(e)}')
            self.status_label.setStyleSheet("color: #dc2626;")


class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.current_dataset = None
        self.upload_thread = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Chemical Equipment Visualizer')
        self.setGeometry(50, 50, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cbd5e0;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #e2e8f0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #3b82f6;
                color: white;
            }
        """)
        
        # Dashboard tab
        self.dashboard_tab = self.create_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        
        # History tab
        self.history_tab = self.create_history_tab()
        self.tabs.addTab(self.history_tab, "📜 History")
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.statusBar().showMessage('Ready')
        self.statusBar().setStyleSheet("background-color: #f0f4f8; padding: 5px;")
    
    def create_header(self):
        """Create header section"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #2563eb);
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        title = QLabel('🔬 Chemical Equipment Parameter Visualizer')
        title.setFont(QFont('Arial', 18, QFont.Bold))
        layout.addWidget(title)
        
        layout.addStretch()
        
        logout_btn = QPushButton('Logout')
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)
        
        return header
    
    def create_dashboard_tab(self):
        """Create dashboard tab with upload and visualization"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Upload section
        upload_group = QGroupBox("📁 Upload CSV File")
        upload_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #cbd5e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                color: #1e40af;
            }
        """)
        upload_layout = QHBoxLayout(upload_group)
        
        self.file_label = QLabel('No file selected')
        self.file_label.setStyleSheet("color: #64748b; padding: 5px;")
        upload_layout.addWidget(self.file_label, 1)
        
        browse_btn = QPushButton('Browse')
        browse_btn.setStyleSheet(self.button_style())
        browse_btn.clicked.connect(self.browse_file)
        upload_layout.addWidget(browse_btn)
        
        self.upload_btn = QPushButton('Upload & Analyze')
        self.upload_btn.setStyleSheet(self.button_style('#16a34a', '#15803d'))
        self.upload_btn.clicked.connect(self.upload_file)
        self.upload_btn.setEnabled(False)
        upload_layout.addWidget(self.upload_btn)
        
        layout.addWidget(upload_group)
        
        # Summary cards
        summary_group = QGroupBox("📈 Summary Statistics")
        summary_group.setStyleSheet(upload_group.styleSheet())
        summary_layout = QGridLayout(summary_group)
        
        self.total_label = self.create_stat_card("Total Equipment", "0", "#3b82f6")
        self.flowrate_label = self.create_stat_card("Avg Flowrate", "0", "#10b981")
        self.pressure_label = self.create_stat_card("Avg Pressure", "0", "#8b5cf6")
        self.temp_label = self.create_stat_card("Avg Temperature", "0", "#f59e0b")
        
        summary_layout.addWidget(self.total_label, 0, 0)
        summary_layout.addWidget(self.flowrate_label, 0, 1)
        summary_layout.addWidget(self.pressure_label, 0, 2)
        summary_layout.addWidget(self.temp_label, 0, 3)
        
        layout.addWidget(summary_group)
        
        # Chart
        chart_group = QGroupBox("📊 Equipment Type Distribution")
        chart_group.setStyleSheet(upload_group.styleSheet())
        chart_layout = QVBoxLayout(chart_group)
        
        self.canvas = MatplotlibCanvas(self, width=10, height=4)
        chart_layout.addWidget(self.canvas)
        
        layout.addWidget(chart_group)
        
        # Table
        table_group = QGroupBox("📋 Equipment Details")
        table_group.setStyleSheet(upload_group.styleSheet())
        table_layout = QVBoxLayout(table_group)
        
        # PDF button
        pdf_btn_layout = QHBoxLayout()
        pdf_btn_layout.addStretch()
        self.pdf_btn = QPushButton('📄 Download PDF Report')
        self.pdf_btn.setStyleSheet(self.button_style('#16a34a', '#15803d'))
        self.pdf_btn.clicked.connect(self.download_pdf)
        self.pdf_btn.setEnabled(False)
        pdf_btn_layout.addWidget(self.pdf_btn)
        table_layout.addLayout(pdf_btn_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Name', 'Type', 'Flowrate', 'Pressure', 'Temperature'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #cbd5e0;
                gridline-color: #e2e8f0;
            }
            QHeaderView::section {
                background-color: #3b82f6;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        table_layout.addWidget(self.table)
        
        layout.addWidget(table_group)
        
        return tab
    
    def create_history_tab(self):
        """Create history tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Refresh button
        refresh_btn = QPushButton('🔄 Refresh History')
        refresh_btn.setStyleSheet(self.button_style())
        refresh_btn.clicked.connect(self.load_history)
        layout.addWidget(refresh_btn, alignment=Qt.AlignRight)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            'ID', 'Filename', 'Upload Time', 'Count', 'Avg Flowrate', 'Actions'
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #cbd5e0;
                gridline-color: #e2e8f0;
            }
            QHeaderView::section {
                background-color: #3b82f6;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.history_table)
        
        return tab
    
    def button_style(self, bg='#3b82f6', hover='#2563eb'):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:disabled {{
                background-color: #9ca3af;
            }}
        """
    
    def create_stat_card(self, title, value, color):
        """Create statistics card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color}20;
                border-left: 4px solid {color};
                border-radius: 5px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        layout.addWidget(value_label)
        
        # Store value label for updates
        card.value_label = value_label
        
        return card
    
    def browse_file(self):
        """Browse for CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Select CSV File',
            '',
            'CSV Files (*.csv);;All Files (*)'
        )
        
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setStyleSheet("color: #16a34a; padding: 5px; font-weight: bold;")
            self.upload_btn.setEnabled(True)
    
    def upload_file(self):
        """Upload file to server"""
        if not hasattr(self, 'selected_file'):
            return
        
        self.upload_btn.setEnabled(False)
        self.upload_btn.setText('Uploading...')
        self.statusBar().showMessage('Uploading file...')
        
        # Use thread for upload
        self.upload_thread = UploadThread(self.selected_file, AUTH_TOKEN)
        self.upload_thread.upload_complete.connect(self.on_upload_complete)
        self.upload_thread.upload_error.connect(self.on_upload_error)
        self.upload_thread.start()
    
    def on_upload_complete(self, data):
        """Handle successful upload"""
        self.upload_btn.setText('Upload & Analyze')
        self.upload_btn.setEnabled(True)
        self.statusBar().showMessage('Upload successful!', 3000)
        
        dataset_id = data['id']
        self.load_dataset_summary(dataset_id)
        self.load_history()
    
    def on_upload_error(self, error):
        """Handle upload error"""
        self.upload_btn.setText('Upload & Analyze')
        self.upload_btn.setEnabled(True)
        self.statusBar().showMessage('Upload failed', 3000)
        QMessageBox.warning(self, 'Upload Error', f'Failed to upload file:\n{error}')
    
    def load_dataset_summary(self, dataset_id):
        """Load and display dataset summary"""
        try:
            headers = {'Authorization': f'Token {AUTH_TOKEN}'}
            response = requests.get(
                f'{API_BASE_URL}/datasets/{dataset_id}/summary/',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.current_dataset = data
                self.update_dashboard(data)
                self.pdf_btn.setEnabled(True)
            else:
                QMessageBox.warning(self, 'Error', 'Failed to load dataset summary')
                
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to load summary:\n{str(e)}')
    
    def update_dashboard(self, data):
        """Update dashboard with data"""
        # Update summary cards
        self.total_label.value_label.setText(str(data['total_count']))
        self.flowrate_label.value_label.setText(f"{data['averages']['flowrate']:.2f}")
        self.pressure_label.value_label.setText(f"{data['averages']['pressure']:.2f}")
        self.temp_label.value_label.setText(f"{data['averages']['temperature']:.2f}")
        
        # Update chart
        self.canvas.axes.clear()
        types = list(data['type_distribution'].keys())
        counts = list(data['type_distribution'].values())
        
        bars = self.canvas.axes.bar(types, counts, color='#3b82f6', alpha=0.7, edgecolor='#1e40af')
        self.canvas.axes.set_xlabel('Equipment Type', fontweight='bold')
        self.canvas.axes.set_ylabel('Count', fontweight='bold')
        self.canvas.axes.set_title('Equipment Type Distribution', fontweight='bold', fontsize=14)
        self.canvas.axes.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            self.canvas.axes.text(
                bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontweight='bold'
            )
        
        plt.setp(self.canvas.axes.xaxis.get_majorticklabels(), rotation=45, ha='right')
        self.canvas.fig.tight_layout()
        self.canvas.draw()
        
        # Update table
        equipments = data['equipments']
        self.table.setRowCount(len(equipments))
        
        for i, eq in enumerate(equipments):
            self.table.setItem(i, 0, QTableWidgetItem(eq['name']))
            self.table.setItem(i, 1, QTableWidgetItem(eq['type']))
            self.table.setItem(i, 2, QTableWidgetItem(f"{eq['flowrate']:.1f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{eq['pressure']:.1f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{eq['temperature']:.1f}"))
    
    def load_history(self):
        """Load dataset history"""
        try:
            headers = {'Authorization': f'Token {AUTH_TOKEN}'}
            response = requests.get(
                f'{API_BASE_URL}/datasets/history/',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                datasets = response.json()
                self.history_table.setRowCount(len(datasets))
                
                for i, ds in enumerate(datasets):
                    self.history_table.setItem(i, 0, QTableWidgetItem(str(ds['id'])))
                    self.history_table.setItem(i, 1, QTableWidgetItem(ds['name']))
                    self.history_table.setItem(i, 2, QTableWidgetItem(ds['uploaded_at'][:19]))
                    self.history_table.setItem(i, 3, QTableWidgetItem(str(ds['total_count'])))
                    self.history_table.setItem(i, 4, QTableWidgetItem(f"{ds['avg_flowrate']:.2f}"))
                    
                    # View button
                    view_btn = QPushButton('View')
                    view_btn.setStyleSheet(self.button_style('#8b5cf6', '#7c3aed'))
                    view_btn.clicked.connect(lambda checked, ds_id=ds['id']: self.view_dataset(ds_id))
                    self.history_table.setCellWidget(i, 5, view_btn)
                
        except Exception as e:
            self.statusBar().showMessage(f'Failed to load history: {str(e)}', 5000)
    
    def view_dataset(self, dataset_id):
        """View dataset from history"""
        self.tabs.setCurrentIndex(0)  # Switch to dashboard tab
        self.load_dataset_summary(dataset_id)
    
    def download_pdf(self):
        """Download PDF report"""
        if not self.current_dataset:
            return
        
        try:
            dataset_id = self.current_dataset['id']
            headers = {'Authorization': f'Token {AUTH_TOKEN}'}
            response = requests.get(
                f'{API_BASE_URL}/datasets/{dataset_id}/generate_pdf/',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # Save PDF
                save_path, _ = QFileDialog.getSaveFileName(
                    self,
                    'Save PDF Report',
                    f'equipment_report_{dataset_id}.pdf',
                    'PDF Files (*.pdf)'
                )
                
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    QMessageBox.information(self, 'Success', 'PDF report downloaded successfully!')
                    self.statusBar().showMessage('PDF downloaded', 3000)
            else:
                QMessageBox.warning(self, 'Error', 'Failed to generate PDF report')
                
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to download PDF:\n{str(e)}')
    
    def logout(self):
        """Logout and return to login screen"""
        global AUTH_TOKEN
        AUTH_TOKEN = None
        self.close()
        
        login_window = LoginWindow(self)
        login_window.show()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    # Create main window (hidden initially)
    main_window = MainWindow()
    
    # Show login window
    login_window = LoginWindow(main_window)
    login_window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()