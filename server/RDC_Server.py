####################################################################################
#                                                                                  #
#  RDC_Server.py                                                                   #
#                                                                                  #
#  This module is installed in computers to be managed by Remote Administrator.    #
#  This is server program for remote desktop connection through RDP protocol.      #
#  Function:                                                                       #
#     1. Server configuration GUI   (IP, port, password)                           #
#     2. Send protocol message to client                                           #
#     3. Receive protocol message from client                                      #
#     4. Send live screen data of computer to client (using RFB protocol)          #
#     5. Process action operation responding to mouse and keyboard event of client #
#                                                                                  #
####################################################################################

import sys
import os

from PyQt5.QtCore import QObject, pyqtSignal, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import  QPixmap, QIcon
from PyQt5.QtWidgets import (QApplication, QLabel, QStyleFactory, QDialog, QGridLayout, QHBoxLayout, QPushButton,
  QLineEdit, QGroupBox, QFormLayout)

from twisted.internet.protocol import Factory, Protocol

from getIPAddr import getIP
import input_event as input
import qt5reactor
import RDC_ServerProtocol as serverProtocol

app = QApplication(sys.argv)
qt5reactor.install( )

class rdcProtocol(serverProtocol.RDCServerProtocol):
    """
    this class is inheritance from RDCServerProtocol,
    the class be responsible for achieve some of functions
    include (
    making screen pixel,
    execute:
    mouse event,
    keyboard event,
    copy text,
    send cut text ) etc...
    """
    def __init__(self):
        serverProtocol.RDCServerProtocol.__init__(self)
        self._array     = QByteArray( )
        self._buffer    = QBuffer(self._array)
        self._buffer.open(QIODevice.WriteOnly)
        self._clipboard = QApplication.clipboard( )
        self._maxWidth  = QApplication.desktop( ).size( ).width( ) 
        self._maxHeight = QApplication.desktop( ).size( ).height( )
        self.keyboard   = input.Keyboard( )
        self.mouse      = input.Mouse( )

    def handleKeyEvent(self, key, flag=None):
        '''
        if flag == 6:
            self.keyboard.press(key)
        else flag == 7:
            self.keyboard.release(key)
        '''
        self.keyboard.press(key)
        self.keyboard.release(key)

    def handleMouseEvent(self, x, y, buttonmask=0, flag=None):
        print(x, y, buttonmask, flag)
        if flag == 5:   # move mouse event 
            self.mouse.move(x, y)
        
        elif flag == 2: # mouse button down
            self.mouse.press(x, y, buttonmask)

        elif flag == 3: # mouse button up
            self.mouse.release(x, y, buttonmask)

        elif flag == 4: # mouse button duble clicked
            self.mouse.press(x, y, buttonmask)
            self.mouse.release(x, y, buttonmask)

    def handleClientCopyText(self, text):
        """
        copy text from client, and then set the text in clipboard
        """
        self._clipboard.setText(text)

    def cutTextToClient(self):
        """
        cut text to client
        """
        text = self._clipboard.text( )
        self.sendCutTextToClient(text)

    def _makeFramebuffer(self, width, height):
        screen = QApplication.primaryScreen()
        pix = screen.grabWindow(QApplication.desktop( ).winId( ))
        pix = pix.scaled(width, height)
        if width >= self._maxWidth or height >= self._maxHeight:
            width  = self._maxWidth
            height = self._maxHeight
        pix.save(self._buffer, 'jpeg')
        pixData = self._buffer.data( )
        self._array.clear( )
        self._buffer.close( )
        temp = "%s" % pixData
        result = temp[2:len(temp)-1]
        return result   # return "%s" % pixData
        
class RDCFactory(serverProtocol.RDCFactory):
    def __init__(self, password=None):
        serverProtocol.RDCFactory.__init__(self, password)
        self.protocol = rdcProtocol

    def buildProtocol(self, addr):
        return serverProtocol.RDCFactory.buildProtocol(self, addr)

    def readyConnection(self, server):
        self.server = server 


#-----------------------#
## myDesktopServer GUI ##
#-----------------------#
class RDCServerGUI(QDialog):
    """
    The PyRDCServerGUI responsible provide GUI interface, operate
    the PyRDCServer.
    """
    def __init__(self, reactor, parent=None):
        super(RDCServerGUI, self).__init__(parent)
       
        self.setupUI( )

        mainLayout = QGridLayout( )
        mainLayout.addWidget(self.groupbox,  0, 0)
        mainLayout.addWidget(self.hostLab,   1, 0)
        mainLayout.addLayout(self.butLayout, 2, 0)
        # mainLayout.setMargin(10)
        self.setLayout(mainLayout)

        self.reactor    = reactor
        self.running    = False

        self.startStopBut.clicked.connect(self.onStartStop)
        self.quitBut.clicked.connect(self.quit)

    def setupUI(self):
        #self.resize(300, 200)
        self.setFixedSize(300, 200)
        self.setWindowTitle('Coinpaign:RDCServer')
        self.setWindowIcon(QIcon('logo.ico'))

        # Setting style
        QApplication.setStyle(QStyleFactory.create('cleanlooks'))
        QApplication.setPalette(QApplication.style().standardPalette())
        #self.setStyleSheet(open(os.path.dirname(__file__) + '/styleSheet.qss', 'r').read( ))
        self.setStyleSheet(open('styleSheet.qss', 'r').read( ))
        # Label
        self.hostLab  = QLabel('')

        self.groupbox = QGroupBox( )
        formLayout    = QFormLayout( )

        # LineEdit
        self.portEdit   = QLineEdit( )
        self.portEdit.setText('5000')
        self.portEdit.setEnabled(False)
        self.addrEdit   = QLineEdit( )
        self.addrEdit.setText( getIP())
        self.addrEdit.setEnabled(False)
        self.passwdEdit = QLineEdit( )
        formLayout.addRow(QLabel('Address'),  self.addrEdit)
        formLayout.addRow(QLabel('Port'),     self.portEdit)
        formLayout.addRow(QLabel('Password'), self.passwdEdit)
        self.groupbox.setLayout(formLayout)

        # Create Button
        self.butLayout     = QHBoxLayout( )
        self.startStopBut  = QPushButton('Start')
        self.quitBut       = QPushButton('Quit')
        self.butLayout.addWidget(self.startStopBut)
        self.butLayout.addWidget(self.quitBut)

    def onStartStop(self):
        if not self.running:
            self._start( )
        else:
            self._stop( )

    def _start(self):
        port = int(self.portEdit.text( ))
        pwd  = str(self.passwdEdit.text( ))
        self.startStopBut.setText('Close')
        self.reactor.listenTCP(port, RDCFactory(password=pwd))
        self.running = True

    def _stop(self):
        self.startStopBut.setText('Start')
        self.reactor.stop( )
        self.running = False

    def quit(self):
        # call reactor of stop method
        self.reactor.stop( )
        # call QDialog of method to close the gui window
        self.close( )

    def closeEvent(self, event):
        self.quit( )

if __name__ == '__main__':
    from twisted.internet import reactor
    rdcServerGUI = RDCServerGUI(reactor)
    rdcServerGUI.show( )
    reactor.run( )
    