from PySide2 import QtCore, QtWidgets, QtGui
from table import BitPos
from bitstream import *
import mmap
import weakref

class DataViewer:
    def __init__(self, editor):
        self.editor = editor

    def to_data_pos(self, cursor_pos):
        pass

    def moveto(self, pos:BitPos):
        pass
    
    def highlight(self,begin: BitPos,end: BitPos):
        pass

    def clear_higlight(self):
        self.editor.setExtraSelections([])

class ByteViewer(DataViewer):
    def __init__(self, editor:QtWidgets.QPlainTextEdit):
        super(ByteViewer, self).__init__(editor)

    def __to_cursor_pos(self, pos:BitPos):
        return pos.byte * 3 + (1 if pos.bit >= 4 else 0)

    def to_data_pos(self, cursor_pos):
        byte = int(cursor_pos / 3)
        bit =  cursor_pos % 3
        if bit == 1:
            bit = 4
        elif bit == 2: #空格处处理为下一个字节
            bit = 0
            byte += 1
        return BitPos(byte, bit)

    def moveto(self, pos:BitPos):
        cursor = self.editor.textCursor()
        cursor.setPosition(self.__to_cursor_pos(pos))
        self.editor.setTextCursor(cursor)

    def highlight(self,begin: BitPos,end: BitPos):
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.cursor = self.editor.textCursor()
        selection.cursor.setPosition(self.__to_cursor_pos(begin))
        selection.cursor.setPosition(self.__to_cursor_pos(end) + (0 if end.bit in [0,4] else 1), QtGui.QTextCursor.KeepAnchor)
        selection.format.setBackground(QtGui.QColor(0,255,0))
        self.editor.setExtraSelections([selection])
    
    def load(self,data):
        self.editor.clear()
        bytestr = []
        for b in data:
            bytestr.append(format(b, '02x'))
        self.editor.setPlainText(' '.join(bytestr)+' ')
    
class BitViewer(DataViewer):
    def __init__(self, editor:QtWidgets.QPlainTextEdit):
        super(BitViewer, self).__init__(editor)

    def __to_cursor_pos(self, pos:BitPos):
        return pos.byte * 9 + pos.bit

    def to_data_pos(self, cursor_pos):
        byte = int(cursor_pos / 9)
        bit =  cursor_pos % 9
        if bit == 8: #空格位置处理为下一个字节开始
            byte += 1
            bit = 0
        return BitPos(byte, bit)

    def moveto(self, pos:BitPos):
        cursor = self.editor.textCursor()
        cursor.setPosition(self.__to_cursor_pos(pos))
        self.editor.setTextCursor(cursor)

    def highlight(self,begin: BitPos,end: BitPos):
        print("highlight %s=>%s "%(str(begin),str(end)))
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.cursor = self.editor.textCursor()
        selection.cursor.setPosition(self.__to_cursor_pos(begin))
        selection.cursor.setPosition(self.__to_cursor_pos(end), QtGui.QTextCursor.KeepAnchor)
        selection.format.setBackground(QtGui.QColor(0,255,0))
        self.editor.setExtraSelections([selection])
    
    def load(self,data):
        self.editor.clear()
        bitstr = []
        for b in data:
            bitstr.append(format(b, '08b'))
        self.editor.setPlainText(' '.join(bitstr)+' ')

class MemoryViewer(DataViewer):
    def __init__(self, mem):
        super(MemoryViewer, self).__init__(DataViewerEditor(self))
        self._highlight = []
        self._impl = ByteViewer(self.editor)
        self._bitstream = BitStream(mem)
        self.valid_range = [0, len(mem)] # end pos not include
        self.mem = mem
        self.limit_range(0, 1024)

    def get_pos(self):
        return self._from_impl_pos(self._impl.to_data_pos(self.editor.textCursor().position()))

    def is_bit_mode(self):
        return type(self._impl) == BitViewer

    def _to_impl_pos(self, pos):
        return BitPos(pos.byte - self.valid_range[0], pos.bit)

    def _from_impl_pos(self, pos):
        return BitPos(pos.byte + self.valid_range[0], pos.bit)

    def set_bit_mode(self,bit = False):
        if self.is_bit_mode() == bit:
            return

        pos = self.get_pos()
        self._impl = BitViewer(self.editor) if bit else ByteViewer(self.editor)

        self.__load_to_impl()
        self._impl.moveto(self._to_impl_pos(pos))
        if len(self._highlight) > 0:
            self._impl.highlight(self._to_impl_pos(self._highlight[0]), self._to_impl_pos(self._highlight[1]))

    def moveto(self, pos:BitPos):
        self._impl.moveto(self._to_impl_pos(pos))

    def highlight(self, begin:BitPos, end:BitPos):
        self._highlight = [begin, end]
        self._impl.highlight(self._to_impl_pos(begin), self._to_impl_pos(end))

    def get_bitstream(self):
        cursor = self.editor.textCursor()
        begin = cursor.selectionStart()
        pos = self._from_impl_pos(self._impl.to_data_pos(begin))
        self._bitstream.moveto(pos.byte, pos.bit)
        if cursor.hasSelection():
            end = cursor.selectionEnd()
            pos = self._from_impl_pos(self._impl.to_data_pos(end))
            self._bitstream.set_end_pos(pos.byte, pos.bit)
        else:
            self._bitstream.set_end_pos(self.valid_range[1], 0)

        return self._bitstream

    def __load_to_impl(self):
        self._impl.load(self.mem[self.valid_range[0]:self.valid_range[1]])

    def limit_range(self, from_include, to_exclude):
        if to_exclude > len(self.mem):
            to_exclude = len(self.mem)
        if from_include < 0:
            from_include = 0

        self.valid_range = [from_include, to_exclude]
        self.__load_to_impl()

class FileViewer(MemoryViewer):
    def __init__(self, path):
        with open(path, 'rb') as f:
            mem = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)
        super(FileViewer, self).__init__(mem)
    
    def __del__(self):
        self.mem.close()

class DataNav(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.viewer = None

        scope_layout = QtWidgets.QHBoxLayout()
        self.begin = QtWidgets.QLineEdit()
        scope_layout.addWidget(self.begin)
        scope_layout.addWidget(QtWidgets.QLabel('-'))
        self.end = QtWidgets.QLineEdit()
        scope_layout.addWidget(self.end)
        btn = QtWidgets.QPushButton('加载')
        btn.clicked.connect(self.__load)
        scope_layout.addWidget(btn)

        nav_layout = QtWidgets.QVBoxLayout()
        self.curpos = QtWidgets.QLabel('当前位置: ')
        nav_layout.addWidget(self.curpos)
        self.size = QtWidgets.QLabel('大小: ')
        nav_layout.addWidget(self.size)
        nav_layout.addLayout(scope_layout)

        self.setLayout(nav_layout)
    
    def __load(self):
        if self.viewer == None:
            return

        begin = int(self.begin.text())
        if self.end.text() != '':
            end = int(self.end.text())
        else:
            end = begin+1024

        self.viewer.limit_range(begin, end)

        self.__update_pos()
        self.__update_size()

    def __update_size(self):
        self.size.setText('大小: [%d => %d) / %d'%(self.viewer.valid_range[0], self.viewer.valid_range[1], len(self.viewer.mem)))

    def __update_pos(self):
        pos = self.viewer.get_pos()
        self.curpos.setText('当前位置: '+str(pos))

    def set_data_viewer(self,viewer):
        self.viewer = viewer
        self.viewer.editor.cursorPositionChanged.connect(self.__update_pos)
        self.viewer.editor.cursorPositionChanged.connect(self.__update_size)
        self.__update_pos()
        self.__update_size()

class DataViewerEditor(QtWidgets.QPlainTextEdit):
    analyse_requested = QtCore.Signal(BitStream)
    default_analyse_requested = QtCore.Signal(BitStream)

    def __init__(self, viewer: MemoryViewer):
        super(DataViewerEditor, self).__init__();
        
        self.setFont(QtGui.QFont('monospace'))
        self.__viewer = weakref.ref(viewer)
        self.setCursorWidth(6)

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.__actions = []
        self.__add_action('执行默认解析器', 'Ctrl+D', self.default_analyse)
        self.__add_action('解析...', 'Ctrl+P', self.analyse)
        self.__add_action('查找...', 'Ctrl+F', self.search)
        self.__add_action('切换二进制/十六机制', 'Ctrl+M', self.switch_mode)

    def __add_action(self, name, key, proc):
       action = QtWidgets.QAction(name)
       action.setShortcut(QtGui.QKeySequence(key))
       action.triggered.connect(proc)
       self.__actions.append(action)
       self.addAction(action)

    def search(self):
        (text, ok) = QtWidgets.QInputDialog.getText(self, '请输入', '要搜索的字符串')
        if ok:
            self.find(text)

    def set_default_parser(self,name):
        self.__actions[0].setText('执行'+name)

    def default_analyse(self):
        self.default_analyse_requested.emit(self.__viewer().get_bitstream())

    def analyse(self):
        self.analyse_requested.emit(self.__viewer().get_bitstream())

    def switch_mode(self):
        self.__viewer().set_bit_mode(not self.__viewer().is_bit_mode())
    