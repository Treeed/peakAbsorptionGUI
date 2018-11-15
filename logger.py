from PyQt5 import QtWidgets, QtGui, QtCore
import logging


class LogStatusMonitor(logging.Handler):
    def __init__(self):
        super().__init__()
        self.widget = OneLinePlainTextEdit()
        self.widget.setReadOnly(True)
        self.widget.setLineWrapMode(self.widget.NoWrap)
        self.widget.setMaximumBlockCount(1000)
        self.widget.setMinimumHeight(33)
        self.widget.setCenterOnScroll(1)
        self.font_format = QtGui.QTextCharFormat()

        self.font_format.setFontPointSize(11)
        self.widget.setCurrentCharFormat(self.font_format)

        self.highlight = QtWidgets.QTextEdit.ExtraSelection()
        self.highlight.cursor = self.widget.textCursor()
        self.highlight_format = QtGui.QTextCharFormat()

    def emit(self, record):
        message = self.format(record)
        self.widget.appendPlainText(message)
        self.highlight.cursor.select(QtGui.QTextCursor.LineUnderCursor)

        if record.levelno >= 40:
            self.highlight_format.setBackground(QtGui.QColor("red"))
        elif record.levelno >= 30:
            self.highlight_format.setBackground(QtGui.QColor("orange"))
        elif record.levelno >= 20:
            self.highlight_format.setBackground(QtGui.QColor("green"))
        elif record.levelno >= 10:
            self.highlight_format.setBackground(QtGui.QColor("blue"))

        self.highlight.format = self.highlight_format
        self.widget.setExtraSelections([self.highlight])
        self.widget.ensureCursorVisible()


class OneLinePlainTextEdit(QtWidgets.QPlainTextEdit):
    def sizeHint(self):
        return QtCore.QSize(0, 33)


def init_logger():
    lg = logging.getLogger("main")
    lg.setLevel(logging.DEBUG)

    # these values should be configurable, but then we would need to load the config before being able to log that config loading failed...
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)-40s: %(message)s')

    file_handler = logging.FileHandler("absorber.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    status_monitor_handler = LogStatusMonitor()
    status_monitor_handler.setFormatter(formatter)
    status_monitor_handler.setLevel(logging.INFO)

    lg.addHandler(file_handler)
    lg.addHandler(console_handler)
    lg.addHandler(status_monitor_handler)

    lg.info("initialized logger")
    return status_monitor_handler.widget
