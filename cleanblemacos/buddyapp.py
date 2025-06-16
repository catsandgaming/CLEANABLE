import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QSystemTrayIcon, QMenu, QDialog, QListWidget, QHBoxLayout, QMessageBox, QSpinBox, QCheckBox, QLineEdit, QFormLayout, QFileDialog, QAbstractItemView, QStyle, QComboBox # Import QStyle and QComboBox
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QTimer, QDateTime, pyqtSignal
import os
import shutil
from PIL import Image

# Define a dictionary to map animal types to their image filenames
# This makes it easy to manage and switch between different buddy images
BUDDY_IMAGES = {
    "Cat": "buddy_cat.png",
    "Dog": "buddy_dog.png",
    "Cow": "buddy_cow.png"
}

# --- Start of DesktopBuddyApp class ---
class DesktopBuddyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Buddy")
        self.setGeometry(100, 100, 300, 400) # Size and starting position

        # Initialize buddy type, will be loaded from settings or default
        self.current_buddy_type = "Cat"

        self.initUI()
        self.initSystemTray()
        self.loadSettings()
        self.startFileMonitor()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.buddy_label = QLabel(self)
        self.buddy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.buddy_label)

        # Load the buddy image based on current_buddy_type
        self._update_buddy_image()

        self.message_label = QLabel("Hello there! I'm your Desktop Buddy.", self)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("padding: 10px; border: 1px solid gray; border-radius: 5px;")
        layout.addWidget(self.message_label)

        self.settings_button = QPushButton("Settings", self)
        self.settings_button.clicked.connect(self.showSettings)
        layout.addWidget(self.settings_button)

        # These lines make the window look like a floating buddy
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # These lines make the window draggable with your mouse
        self.old_pos = None

    def _update_buddy_image(self):
        """Loads and sets the buddy image based on self.current_buddy_type."""
        image_filename = BUDDY_IMAGES.get(self.current_buddy_type, "buddy_cat.png") # Default to cat if type not found
        try:
            self.buddy_pixmap = QPixmap(image_filename)
            if self.buddy_pixmap.isNull():
                raise FileNotFoundError
            self.buddy_label.setPixmap(self.buddy_pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
        except FileNotFoundError:
            print(f"Buddy image '{image_filename}' not found. Using a default text icon.")
            self.buddy_label.setText("^_^")
            self.buddy_label.setStyleSheet("font-size: 100px; text-align: center;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None

    def initSystemTray(self):
        # This creates the icon in the bottom right corner of your screen
        self.tray_icon = QSystemTrayIcon(QIcon("buddy_icon.png" if os.path.exists("buddy_icon.png") else QApplication.instance().style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)), self)
        self.tray_icon.setToolTip("Desktop Buddy")

        # This makes the menu that pops up when you right-click the tray icon
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show Buddy")
        show_action.triggered.connect(self.show)
        hide_action = tray_menu.addAction("Hide Buddy")
        hide_action.triggered.connect(self.hide)
        settings_action = tray_menu.addAction("Settings")
        settings_action.triggered.connect(self.showSettings)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.closeApp)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.trayIconActivated)
        self.tray_icon.show()

    def trayIconActivated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()

    def closeApp(self):
        self.tray_icon.hide()
        QApplication.instance().quit()

    def loadSettings(self):
        # These are the folders your buddy will look in for old files
        self.monitor_paths = [
            os.path.expanduser("~/Downloads"), # Your Downloads folder
            os.path.expanduser("~/Desktop"),   # Your Desktop
            os.path.join(os.getenv('TEMP'), ''), # Your temporary files folder
            os.path.join(os.getenv('WINDIR'), 'Temp', '') # Windows system temporary files
        ]
        self.days_old_threshold = 30 # Files older than 30 days are "old"
        self.auto_delete_enabled = False # Don't auto-delete yet
        self.ignored_file_types = ['.lnk', '.ini', '.dll', '.exe'] # Don't touch these files!
        self.current_buddy_type = "Cat" # Default buddy type

        print("Settings loaded (default for now).")
        print(f"Monitoring paths: {self.monitor_paths}")

    def saveSettings(self):
        # In a real app, you'd save these settings to a file so they remember
        print("Settings saved (dummy function for now).")

    def showSettings(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.settings_saved.connect(self.applySettings)
        self.settings_window.exec()

    def applySettings(self, new_settings):
        self.monitor_paths = new_settings['monitor_paths']
        self.days_old_threshold = new_settings['days_old_threshold']
        self.auto_delete_enabled = new_settings['auto_delete_enabled']
        self.ignored_file_types = new_settings['ignored_file_types']
        self.current_buddy_type = new_settings['buddy_type'] # Update the buddy type
        self.saveSettings()
        self.message_label.setText("Settings updated!")
        self._update_buddy_image() # Update the buddy image
        self.startFileMonitor()

    def startFileMonitor(self):
        # This makes your buddy check for files every hour
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.checkForOldFiles)
        self.monitor_timer.start(60 * 60 * 1000) # Checks every 60 minutes (60 seconds * 60 minutes * 1000 milliseconds)
        self.checkForOldFiles() # Check once right when the app starts

    def checkForOldFiles(self):
        print("Checking for old files...")
        old_files_found = []
        now = QDateTime.currentDateTime()

        for path in self.monitor_paths:
            if not os.path.isdir(path):
                print(f"Warning: Monitor path does not exist: {path}")
                continue

            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        if os.path.islink(file_path): # Skip special links
                            continue

                        if any(filename.lower().endswith(ext) for ext in self.ignored_file_types): # Skip files we don't want to touch
                            continue

                        mod_time = QDateTime.fromSecsSinceEpoch(int(os.path.getmtime(file_path)))
                        days_diff = mod_time.daysTo(now)

                        if days_diff >= self.days_old_threshold:
                            old_files_found.append(file_path)
                    except Exception as e:
                        # If we can't look at a file, we'll just skip it
                        if "Access is denied" in str(e) or "Permission denied" in str(e):
                            print(f"Permission denied for {file_path}. Skipping.")
                        else:
                            print(f"Error checking file {file_path}: {e}")

        if old_files_found:
            self.message_label.setText(f"Hey! I found {len(old_files_found)} old files.")
            self.promptToDeleteFiles(old_files_found)
        else:
            self.message_label.setText("All clear! No old files found.")
        # Reset buddy image (useful if you have different images for different states)
        self._update_buddy_image() # Ensure correct image is displayed after check

    def promptToDeleteFiles(self, files_to_delete):
        if self.auto_delete_enabled:
            self.message_label.setText("Automatically deleting old files...")
            self.deleteFiles(files_to_delete, auto=True)
            return

        self.hide() # Hide the main buddy window while the prompt is open
        dialog = FileDeletionDialog(files_to_delete, self)
        dialog.delete_confirmed.connect(self.deleteFiles)
        dialog.exec() # Show the delete dialog
        self.show() # Show buddy again after dialog closes

    def deleteFiles(self, files_to_delete, auto=False):
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                if os.path.isdir(file_path): # If it's a folder
                    shutil.rmtree(file_path) # Delete the whole folder
                else:
                    os.remove(file_path) # Delete just the file
                deleted_count += 1
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

        if deleted_count > 0:
            self.message_label.setText(f"Deleted {deleted_count} files for you!")
        else:
            self.message_label.setText("No files were deleted.")
        self._update_buddy_image() # Ensure correct image is displayed after deletion


# --- End of DesktopBuddyApp class ---

# --- Start of FileDeletionDialog class (the pop-up that asks about deleting files) ---
class FileDeletionDialog(QDialog):
    delete_confirmed = pyqtSignal(list) # This sends info back to the main app

    def __init__(self, files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Files to Delete?")
        self.setGeometry(200, 200, 500, 400)
        self.files = files

        layout = QVBoxLayout()

        self.message_label = QLabel("I found these files that haven't been used in a while. Would you like to delete them?")
        layout.addWidget(self.message_label)

        self.file_list_widget = QListWidget()
        for f in self.files:
            self.file_list_widget.addItem(f) # Add each file to the list
        layout.addWidget(self.file_list_widget)

        button_layout = QHBoxLayout()
        # Changed button text to "Delete All"
        self.delete_button = QPushButton("Delete All")
        self.delete_button.clicked.connect(self.confirmDelete)
        button_layout.addWidget(self.delete_button)

        self.keep_button = QPushButton("Keep All")
        self.keep_button.clicked.connect(self.reject) # Closes dialog without deleting
        button_layout.addWidget(self.keep_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def confirmDelete(self):
        # Now, instead of selected items, we take ALL files from self.files
        files_to_delete = self.files
        if files_to_delete:
            reply = QMessageBox.question(self, 'Confirm Deletion',
                                         f"Are you sure you want to delete all {len(files_to_delete)} listed files?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.delete_confirmed.emit(files_to_delete)
                self.accept() # Close the dialog
        else:
            QMessageBox.information(self, "No Files", "No files to delete.")

# --- End of FileDeletionDialog class ---

# --- Start of SettingsWindow class ---
class SettingsWindow(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desktop Buddy Settings")
        self.setGeometry(300, 300, 400, 300)
        self.parent_app = parent # This connects to the main buddy app

        self.initUI()
        self.loadCurrentSettings()

    def initUI(self):
        layout = QFormLayout()

        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(7, 365) # You can choose between 7 and 365 days
        layout.addRow("Delete files older than (days):", self.days_spinbox)

        self.paths_list_widget = QListWidget()
        # Ensure correct selection mode
        self.paths_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # Corrected drag-drop mode to InternalMove
        self.paths_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.paths_list_widget.setDropIndicatorShown(True)
        self.paths_list_widget.setDragEnabled(True)

        add_path_button = QPushButton("Add Path")
        add_path_button.clicked.connect(self.addMonitorPath)
        remove_path_button = QPushButton("Remove Selected Paths")
        remove_path_button.clicked.connect(self.removeMonitorPaths)

        path_buttons_layout = QHBoxLayout()
        path_buttons_layout.addWidget(add_path_button)
        path_buttons_layout.addWidget(remove_path_button)

        layout.addRow("Folders to monitor:", self.paths_list_widget)
        layout.addRow("", path_buttons_layout)

        self.auto_delete_checkbox = QCheckBox("Enable automatic deletion without prompt")
        layout.addRow("", self.auto_delete_checkbox)

        self.ignored_types_lineedit = QLineEdit()
        self.ignored_types_lineedit.setPlaceholderText(".lnk, .ini, .log (comma-separated)")
        layout.addRow("Ignore file types (e.g., .txt, .log):", self.ignored_types_lineedit)

        # Add QComboBox for buddy type selection
        self.buddy_type_combobox = QComboBox()
        self.buddy_type_combobox.addItems(BUDDY_IMAGES.keys()) # Add "Cat", "Dog", "Cow"
        layout.addRow("Choose your buddy:", self.buddy_type_combobox)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.saveAndApplySettings)
        layout.addRow(save_button)

        self.setLayout(layout)

    def loadCurrentSettings(self):
        if self.parent_app:
            self.days_spinbox.setValue(self.parent_app.days_old_threshold)
            for path in self.parent_app.monitor_paths:
                self.paths_list_widget.addItem(path)
            self.auto_delete_checkbox.setChecked(self.parent_app.auto_delete_enabled)
            self.ignored_types_lineedit.setText(", ".join(self.parent_app.ignored_file_types))
            # Set the current buddy type in the combobox
            index = self.buddy_type_combobox.findText(self.parent_app.current_buddy_type)
            if index != -1:
                self.buddy_type_combobox.setCurrentIndex(index)


    def addMonitorPath(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Monitor")
        if folder:
            # Add path only if it's not already in the list
            current_paths = [self.paths_list_widget.item(i).text() for i in range(self.paths_list_widget.count())]
            if folder not in current_paths:
                self.paths_list_widget.addItem(folder)

    def removeMonitorPaths(self):
        # Remove selected items from the list
        for item in self.paths_list_widget.selectedItems():
            self.paths_list_widget.takeItem(self.paths_list_widget.row(item))

    def saveAndApplySettings(self):
        new_settings = {
            'days_old_threshold': self.days_spinbox.value(),
            'monitor_paths': [self.paths_list_widget.item(i).text() for i in range(self.paths_list_widget.count())],
            'auto_delete_enabled': self.auto_delete_checkbox.isChecked(),
            'ignored_file_types': [ext.strip() for ext in self.ignored_types_lineedit.text().split(',') if ext.strip()],
            'buddy_type': self.buddy_type_combobox.currentText() # Save the selected buddy type
        }
        self.settings_saved.emit(new_settings)
        self.accept() # Close the settings dialog

# --- End of SettingsWindow class ---

# --- Main part of the app that runs everything ---
if __name__ == "__main__":
    # These lines create little dummy image files for your buddy if they don't exist
    # Later, you can replace these with your own cool cat or dog pictures!

    # Use the uploaded image for buddy_cat.png
    if not os.path.exists("buddy_cat.png"):
        # Assuming the uploaded image is the cat, save it as buddy_cat.png
        # For demonstration, creating a simple image if it doesn't exist
        try:
            img = Image.new('RGB', (200, 200), color = (150, 150, 150)) # Grey square
            img.save("buddy_cat.png")
            print("Created dummy 'buddy_cat.png'. You can replace this with your own picture!")
        except Exception as e:
            print(f"Could not create buddy_cat.png: {e}")

    if not os.path.exists("buddy_dog.png"):
        img = Image.new('RGB', (200, 200), color = (0, 100, 0)) # Green square for dog
        img.save("buddy_dog.png")
        print("Created dummy 'buddy_dog.png'. You can replace this with your own picture!")

    if not os.path.exists("buddy_cow.png"):
        img = Image.new('RGB', (200, 200), color = (100, 0, 100)) # Purple square for cow
        img.save("buddy_cow.png")
        print("Created dummy 'buddy_cow.png'. You can replace this with your own picture!")

    if not os.path.exists("buddy_icon.png"):
        # Creates a simple blue square image for the system tray icon
        img = Image.new('RGB', (64, 64), color = (0, 0, 255)) # Blue square
        img.save("buddy_icon.png")
        print("Created dummy 'buddy_icon.png'. You can replace this with your own icon!")

    app = QApplication(sys.argv)
    # This makes sure the app doesn't close completely if you just hide the buddy window
    app.setQuitOnLastWindowClosed(False)
    window = DesktopBuddyApp()
    window.show() # Show your buddy!
    sys.exit(app.exec())
