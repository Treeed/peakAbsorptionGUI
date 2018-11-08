from PyQt5 import QtGui
import sys
import absorbergui
import qdarkstyle


def main():
    app = QtGui.QApplication(sys.argv)
    # This has a deprecation warning but doesn't provide the function replacing the deprecated one yet. Seems we have to live with it.
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    vd = absorbergui.MainWindow()
    vd.show()
    app.exec_()


if __name__ == '__main__':
    main()
