import sys
from PyQt6.QtWidgets import *
import PyQt6.QtCore as QtCore

class ParameterWidget(QWidget):
    """Widget containing parameters for processing."""
    def __init__(self):
        super().__init__()
        self.parameters = {
            'r' : 2,
            'R' : 1.07,
            'gamma' : 1.7,
            'r1' : 10,
            'r2' : 15,
            't' : 1.
            }
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.value_lineedit_lambdas = []
        
        for key, value in self.parameters.items():
            # name
            line_layout = QHBoxLayout()
            parameter_label = QLabel(key)
            line_layout.addWidget(parameter_label)
            # value
            value_lineedit = QLineEdit(str(value), self)
            value_lineedit.key = key
            line_layout.addWidget(value_lineedit)
            # TODO lambda scope evaluates only for last iteration
            value_lineedit.textEdited.connect(lambda: self.parameter_lineedit_value_changed(value_lineedit.key))
            layout.addLayout(line_layout)
    
    @QtCore.pyqtSlot()
    def parameter_lineedit_value_changed(self, text, key):
        print(self)
            
        

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # core widget
        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)
        self.setWindowTitle("HaPy")
        main_layout = QVBoxLayout()
        centralWidget.setLayout(main_layout)
        
        # tabs
        setup_page = QWidget(self)
        view_page = QWidget(self)
        
        # setup page
        setup_layout = QVBoxLayout()
        # filename list
        self.files_to_process_listwidget = QListWidget(self)
        # files button
        load_files_button = QPushButton("Add files", self)
        load_files_button.clicked.connect(lambda: self.load_files_button_pressed(self.files_to_process_listwidget));
        # parameter widget
        parameter_widget = ParameterWidget()
        
        
        # add widgets to page layout
        setup_layout.addWidget(load_files_button)
        setup_layout.addWidget(self.files_to_process_listwidget)
        setup_layout.addWidget(parameter_widget)
        setup_page.setLayout(setup_layout)
        
        # view page
        view_layout = QVBoxLayout()
        label2 = QLabel("Widget in Tab 2.")
        view_layout.addWidget(label2)
        view_page.setLayout(view_layout)
        
        # create tab widget
        tabwidget = QTabWidget(self)
        tabwidget.addTab(setup_page, "Setup")
        tabwidget.addTab(view_page, "Viewer")
        
        main_layout.addWidget(tabwidget)
    
    @QtCore.pyqtSlot()
    def load_files_button_pressed(self, filename_list_widget: QListWidget):
        """Loads unique .fits file filepaths."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("FITS (*.fits)")
        file_dialog.exec()
        filenames = file_dialog.selectedFiles()
        
        for filename in filenames:
            if not filename_list_widget.findItems(filename, QtCore.Qt.MatchFlag.MatchExactly):
                filename_list_widget.addItem(filename)
        
        filename_list_widget.sortItems()
        

# create the QApplication
app = QApplication([])

# create the main window
window = MainWindow()

window.show()

# start the event loop
sys.exit(app.exec())