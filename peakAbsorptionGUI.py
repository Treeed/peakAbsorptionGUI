from PyQt4 import QtGui
import sys
import absorbergui

def main():
    app = QtGui.QApplication(sys.argv)
    vd = absorbergui.ViewData()
    vd.show()
    app.exec_()


if __name__ == '__main__':
    main()
