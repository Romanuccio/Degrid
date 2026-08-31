import sys
from PyQt6.QtWidgets import *
import PyQt6.QtCore as QtCore
import matplotlib
import pathlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from FFPS import ImageProcessorThread, gamma_correction
from astropy.io import fits


class DrawListWidgetItem(QListWidgetItem):
    def __init__(self):
        super().__init__()
        self.drawn = False


class ParameterWidget(QWidget):
    """Widget containing parameters for processing."""

    gamma_changed = QtCore.pyqtSignal()
    def __init__(self):
        super().__init__()
        self.parameters = {
            "gamma": 1.7,
            "r": 2,
            "R": 1.07,
            "r1": 10,
            "r2": 15,
            "t": 1.0,
            "n (pixels replaced, in percent)": 0.3
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
        self.sender().setStyleSheet("")
        # changes value of FFPS parameter in dictionary of parameters widget
        value = self.sender().text()
        key = self.sender().key
        
        try:
            parsed = float(value)
            self.parameters[key] = parsed
        except ValueError:
            self.sender().setStyleSheet("color: rgb(255, 0, 0);")
            return
        
        if key == 'gamma':
            self.gamma_changed.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.last_drawn_item = None

        # Core widget
        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)
        self.setWindowTitle("Degrid")

        main_layout = QVBoxLayout(centralWidget)

        setup_page = QWidget(self)

        columns_layout = QHBoxLayout(setup_page)

        # ============================================================
        # LEFT COLUMN - setup / parameters
        # ============================================================

        setup_column = QWidget()
        setup_column.setMaximumWidth(400)

        setup_layout = QVBoxLayout(setup_column)

        # Filename list
        files_label = QLabel("Files to process:")

        self.files_to_process_listwidget = QListWidget()
        self.files_to_process_listwidget.currentItemChanged.connect(
            lambda current, previous:
                self.listwidget_currentItem_Changed(
                    current,
                    previous,
                    self.files_to_process_listwidget
                )
        )
        self.files_to_process_listwidget.itemClicked.connect(
            lambda item: self.filelist_currentItem_clicked(item)
        )

        # Processed files list
        processed_label = QLabel("Processed files:")

        self.processed_files_listwidget = QListWidget()
        self.processed_files_listwidget.currentItemChanged.connect(
            lambda current, previous:
                self.listwidget_currentItem_Changed(
                    current,
                    previous,
                    self.processed_files_listwidget
                )
        )
        self.processed_files_listwidget.itemClicked.connect(
            lambda item: self.filelist_currentItem_clicked(item)
        )

        # Files button
        load_files_button = QPushButton("Add files")
        load_files_button.clicked.connect(
            self.load_files_button_pressed
        )

        # Parameter widget
        self.parameter_widget = ParameterWidget()
        self.parameter_widget.gamma_changed.connect(
            self.redraw_last_item
        )

        # Add widgets to setup layout
        setup_layout.addWidget(load_files_button)

        # Clear files button
        self.clear_button = QPushButton("Clear files")
        self.clear_button.pressed.connect(
            self.clear_button_pressed
        )
        setup_layout.addWidget(self.clear_button)

        setup_layout.addWidget(files_label)
        setup_layout.addWidget(self.files_to_process_listwidget)

        setup_layout.addWidget(processed_label)
        setup_layout.addWidget(self.processed_files_listwidget)

        setup_layout.addWidget(self.parameter_widget)

        # Process / progress
        process_progress_layout = QVBoxLayout()

        self.process_button = QPushButton("Process")
        self.process_button.clicked.connect(
            self.process_button_pressed
        )
        process_progress_layout.addWidget(self.process_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        process_progress_layout.addWidget(self.progress_bar)

        setup_layout.addLayout(process_progress_layout)

        # Add the LEFT COLUMN widget to the horizontal layout
        columns_layout.addWidget(setup_column)

        # ============================================================
        # RIGHT COLUMN - canvas
        # ============================================================

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)

        # Stretch factor = 1, so canvas takes remaining space
        columns_layout.addWidget(self.canvas, 1)

        # Add whole page to main layout
        main_layout.addWidget(setup_page)

    @QtCore.pyqtSlot()
    def clear_button_pressed(self):
        # clear plot
        self.figure.clear()
        self.canvas.draw()
        # clear items in file listwidget
        self.files_to_process_listwidget.clear()

    @QtCore.pyqtSlot()
    def filelist_currentItem_clicked(self, item):
        if item.drawn:
            item.drawn = False
            return

        self.draw_selected_item(item)

    @QtCore.pyqtSlot()
    def listwidget_currentItem_Changed(self, current, previous, selected_QListWidget):
        if selected_QListWidget.count() == 0:
            return

        if selected_QListWidget.currentItem() is None:
            return

        current.drawn = True

        if previous is not None:
            previous.drawn = False

        self.draw_selected_item(selected_QListWidget.currentItem())

    def draw_selected_item(self, selected_item):
        self.last_drawn_item = selected_item
        filepath = selected_item.text()
        with fits.open(filepath) as hdul:
            self.figure.clear()
            data = hdul[0].data
            data = gamma_correction(data, self.parameter_widget.parameters["gamma"])
            ax = self.figure.subplots()
            ax.imshow(data, cmap="gray")
            self.canvas.draw()

    def redraw_last_item(self):
        if self.last_drawn_item is None:
            return
        
        self.draw_selected_item(self.last_drawn_item)
        
        
    @QtCore.pyqtSlot()
    def load_files_button_pressed(self):
        """Loads unique .fits filepaths."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("FITS (*.fits *.fit *.fts)")
        if not file_dialog.exec():
            return
        
        filenames = file_dialog.selectedFiles()

        for filename in filenames:
            if not self.files_to_process_listwidget.findItems(
                filename, QtCore.Qt.MatchFlag.MatchExactly
            ):
                item = DrawListWidgetItem()
                item.setText(filename)
                self.files_to_process_listwidget.addItem(item)

        self.files_to_process_listwidget.sortItems()

    @QtCore.pyqtSlot()
    def process_button_pressed(self):
        self.processed_files_listwidget.clear()
        # load parameters
        try:
            r = self.parameter_widget.parameters["r"]
            R = self.parameter_widget.parameters["R"]
            gamma = self.parameter_widget.parameters["gamma"]
            r1 = self.parameter_widget.parameters["r1"]
            r2 = self.parameter_widget.parameters["r2"]
            t = self.parameter_widget.parameters["t"]
            n = self.parameter_widget.parameters["n (pixels replaced, in percent)"]
        except ValueError:
            error_dialog = QErrorMessage()
            error_dialog.showMessage("Invalid parameters.")
            return
        
        # load filepaths
        self.files_to_process = [
            self.files_to_process_listwidget.item(x).text()
            for x in range(self.files_to_process_listwidget.count())
        ]

        self.total_files_processing = len(self.files_to_process)
        # file_count = len(files_to_process)
        if len(self.files_to_process) == 0:
            return

        self.process_button.setEnabled(False)
        self.process_button.setText("Processing...")
        # create image processing thread
        filename = self.files_to_process.pop(0)
        self.image_processor = ImageProcessorThread(r, R, r1, r2, t, filename, n)
        self.image_processor.finished.connect(self.image_processer_finished)
        self.image_processor.start()

    @QtCore.pyqtSlot()
    def image_processer_finished(self):
        # add processed filename to processed listwidget
        item = DrawListWidgetItem()
        item.setText(str(self.image_processor.saved_filepath))
        self.processed_files_listwidget.addItem(item)
        # amount of remaining files to process
        filecount_left = len(self.files_to_process)

        if filecount_left == 0:
            # processed all
            self.progress_bar.setValue(0)
            self.process_button.setEnabled(True)
            del self.image_processor
            self.process_button.setText("Process")
            return

        # keep processing
        self.progress_bar.setValue(
            int((1.0 - filecount_left / self.total_files_processing) * 100)
        )
        filename = self.files_to_process.pop(0)
        self.image_processor.set_file(filename)
        self.image_processor.start()


# create the QApplication
app = QApplication([])

# create the main window
window = MainWindow()

window.show()

# start the event loop
sys.exit(app.exec())
