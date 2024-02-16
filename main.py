import sys
from PyQt6.QtWidgets import *
import PyQt6.QtCore as QtCore
import FFPS
from astropy.io import fits

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
            value_lineedit.textEdited.connect(self.parameter_lineedit_value_changed)
            layout.addLayout(line_layout)
    
    @QtCore.pyqtSlot()
    def parameter_lineedit_value_changed(self):
        # changes value of FFPS parameter in dictionary of parameters widget
        self.parameters[self.sender().key] = self.sender().text()
            
        

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
        load_files_button.clicked.connect(lambda: self.load_files_button_pressed());
        # parameter widget
        self.parameter_widget = ParameterWidget()
        
        
        # add widgets to page layout
        setup_layout.addWidget(load_files_button)
        setup_layout.addWidget(self.files_to_process_listwidget)
        setup_layout.addWidget(self.parameter_widget)
        
        process_button = QPushButton("Process", self)
        process_button.clicked.connect(self.process_button_pressed)
        setup_layout.addWidget(process_button)
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
    def load_files_button_pressed(self):
        """Loads unique .fits file filepaths."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("FITS (*.fits)")
        file_dialog.exec()
        filenames = file_dialog.selectedFiles()
        
        for filename in filenames:
            if not self.files_to_process_listwidget.findItems(filename, QtCore.Qt.MatchFlag.MatchExactly):
                self.files_to_process_listwidget.addItem(filename)
        
        self.files_to_process_listwidget.sortItems()
        
    @QtCore.pyqtSlot()
    def process_button_pressed(self):
        r = self.parameter_widget.parameters['r']
        R = self.parameter_widget.parameters['R']
        gamma = self.parameter_widget.parameters['gamma']
        r1 = self.parameter_widget.parameters['r1']
        r2 = self.parameter_widget.parameters['r2']
        t = self.parameter_widget.parameters['t']
        processed_images = []
        
        files_to_process = [self.files_to_process_listwidget.item(x).text() for x in range(self.files_to_process_listwidget.count())]
        for file_to_process in files_to_process:
            # TODO change asdf to filepath in folder where program was run
            processed_image = FFPS.process_image_and_save(filename= file_to_process, r=r, R=R, gamma=gamma, r1=r1, r2=r2, t=t, save_filepath="asdf")

# create the QApplication
app = QApplication([])

# create the main window
window = MainWindow()

window.show()

# start the event loop
sys.exit(app.exec())