import sys
import random
import markdown2 as mk
import plugin
from viewdata import *
from table import *
import time
import traceback
from PySide2.QtWidgets import *
from PySide2.QtCore import *
import re

#菜单 文件（打开、最近文件）|插件(加载，查阅文档)|关于
#最近文件
#通过点选的方式创建透视图（而不是输入很长的名字）
#透视图支持filter功能

def show_modal_error(str):
    msg = QMessageBox()
    msg.setText(str)
    msg.exec_()

def uneditable_item(s):
    item = QTableWidgetItem(s)
    item.setFlags(item.flags()&(~Qt.ItemFlag.ItemIsEditable))
    return item

class ContextViewer(QObject):
    show_item_requested = Signal(Table)

    def __init__(self):
        super(ContextViewer, self).__init__()
        self.fileds = []
        self.widget = QTableWidget()
        self.widget.setColumnCount(3)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.widget.setHorizontalHeaderLabels(['解析器','位置', '备注'])
        self.widget.currentItemChanged.connect(self.__on_current_item_changed)
        self.widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.widget.customContextMenuRequested.connect(self.show_context_menu)
        self.widget.horizontalHeader().setHighlightSections(False)
        self.__menu = self.__create_menu()

    def __on_current_item_changed(self, cur, prev):
        self.notify_current_selected()

    def notify_current_selected(self):
        index = self.widget.currentIndex().row()
        if index >= 0 and index < len(self.fileds):
            item = self.fileds[index]
            self.show_item_requested.emit(item)

    def add(self, d:Table):
        row = len(self.fileds)
        self.fileds.append(d)

        self.widget.insertRow(row)
        self.widget.setItem(row, 0, uneditable_item(d.name))
        self.widget.setItem(row, 1, uneditable_item(str(d.begin)+'=>'+str(d.end)))
        self.widget.horizontalHeader().resizeSections(QHeaderView.ResizeToContents)

    def __create_menu(self):
        menu = QMenu()
        menu.addAction('清空').triggered.connect(self.clear)
        menu.addAction('删除该项').triggered.connect(self.remove_current)
        return menu

    def remove_current(self):
        current = self.widget.currentIndex().row()
        if current >= 0 and current < len(self.fileds):
            self.widget.removeRow(current)
            del self.fileds[current]

    def clear(self):
        self.fileds.clear()
        self.widget.setRowCount(0)
        self.widget.clearContents()
    
    def get_context(self):
        context = Table('context', None, None)
        for field in self.fileds:
            context.add_exist(field)
        return context

    def show_context_menu(self, point):
        self.__menu.exec_(self.widget.mapToGlobal(point))

class HistoryViewer(QObject):
    show_item_requested = Signal(Table)
    perspective_requested = Signal(list)

    def __init__(self, max_count=100):
        super(HistoryViewer, self).__init__()
        self.widget = QTableWidget()
        self.widget.setColumnCount(4)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.widget.setHorizontalHeaderLabels(['时间','解析器','位置', '备注'])
        self.widget.currentItemChanged.connect(self.__on_current_item_changed)
        self.widget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.widget.horizontalHeader().setHighlightSections(False)
        self.__max_count = max_count
        self.__history = []

        self.__actions = []
        self.__add_action('删除', self.delete_items)
        self.__add_action('创建透视表', self.create_perspective_request)
        self.__add_action('清空', self.clear)

    def __add_action(self, name, proc):
       action = QtWidgets.QAction(name)
       action.triggered.connect(proc)
       self.__actions.append(action)
       self.widget.addAction(action)

    def get_selected_rows(self):
        items = self.widget.selectedItems()
        rows = []
        for item in items:
            if not item.row() in rows:
                rows.append(item.row())
        return rows

    def create_perspective_request(self):
        rows = self.get_selected_rows()
        rows.sort()
        self.perspective_requested.emit([self.__history[i] for i in rows])

    def delete_items(self):
        rows = self.get_selected_rows()
        rows.sort(reverse=True)
        for row in rows:
            self.widget.removeRow(row)

    def __on_current_item_changed(self, cur, prev):
        self.notify_current_selected()
    
    def notify_current_selected(self):
        index = self.widget.currentIndex().row()
        if index >= 0 and index < len(self.__history):
            d = self.__history[index]
            self.show_item_requested.emit(d)
        else:
            self.show_item_requested.emit(None)

    def add(self, d:Table):
        if len(self.__history) >= self.__max_count:
            del self.__history[0]
            self.widget.removeRow(0)
        row = len(self.__history)
        self.__history.append(d)
        self.widget.insertRow(row)
        self.widget.setItem(row, 0, uneditable_item(time.strftime('%H:%M:%S', time.localtime())))
        self.widget.setItem(row, 1, uneditable_item(d.name))
        self.widget.setItem(row, 2, uneditable_item(str(d.begin)+'=>'+str(d.end)))
        self.widget.clearSelection()
        self.widget.setCurrentIndex(self.widget.model().index(row,0))
        self.widget.horizontalHeader().resizeSections(QHeaderView.ResizeToContents)
    
    def clear(self):
        self.__history.clear()
        self.widget.setRowCount(0)
        self.widget.clearContents()
    


class DocViewer:
    def __init__(self):
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.img_path=''

    def __fix_img_path(self, matched):
        return '![%s](%s)'%(matched.group(1), self.img_path+'/'+matched.group(2))

    def __markup_doc(self, text):
        text=re.sub(r'!\[(\w+)\]\((\w+/\w+.\w+)\)', self.__fix_img_path, text)
        body = mk.markdown(text, extras=['tables','code-friendly'])
        html = '''<html>
        <head>
        <style type="text/css">
            th {
                background-color:#00e3e3;
                padding:3px 10px;
                color:white
            }
            td {
                background-color:#f0f0f0;
                padding:3px 10px;
            }
        </style>
        </head>
        <body>'''+body+'</body>'
        return html

    def clear(self):
        self.editor.clear()

    def load(self,text):
        self.editor.setHtml(self.__markup_doc(text))

class TableViewer(QObject):
    field_selected = Signal(Field, str)
    add_field_to_context = Signal(Table)
    
    def __init__(self):
        super(TableViewer, self).__init__()
        self.__fields = {}
        self.__setup_ui()

    def __setup_ui(self):
        self.widget = QTreeWidget()
        self.widget.setColumnCount(3)
        self.widget.setHeaderLabels(['名字','值','长度(bits)'])
        self.widget.currentItemChanged.connect(self.__on_current_item_changed)
        self.widget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.__actions = []
        self.__add_action('添加到上下文', self.add_current_to_context)
        self.__add_action('复制', self.copy_item)

    def __add_action(self, name, proc):
       action = QtWidgets.QAction(name)
       action.triggered.connect(proc)
       self.__actions.append(action)
       self.widget.addAction(action)

    def copy_item(self):
        item = self.widget.currentItem()
        col = self.widget.currentColumn()
        if self.__fields.__contains__(item):
            (field, dockey) = self.__fields[item]
            clipboard = QApplication.clipboard()
            if col == 0:
                clipboard.setText(field.name)
            elif col == 1:
                clipboard.setText(str(field.value))
            elif col == 2:
                clipboard.setText(str(field.end.bits_count()-field.begin.bits_count()))

    def show_context_menu(self, point):
        self.__menu.exec_(self.widget.mapToGlobal(point))

    def __on_current_item_changed(self):
        item = self.widget.currentItem()
        if self.__fields.__contains__(item):
            (field, dockey) = self.__fields[item]
            self.field_selected.emit(field, dockey)
        else:
            self.field_selected.emit(None, None)

    def add_current_to_context(self):
        item = self.widget.currentItem()
        if self.__fields.__contains__(item):
            d = self.__fields[item][0]
            if type(d) != Table:
                show_modal_error('字段值不支持加入到上下文中')
                return
            self.add_field_to_context.emit(d)


    def __field_value_str(self,value):
        if type(value) == bytearray or type(value) == bytes:
            return '%d字节数组'%(len(value))
        else:
            return str(value)
        
    def __print_table(self, d:Table):
        item = QTreeWidgetItem()
        self.__fields[item] = (d, d.name)
        item.setText(0, d.name)
        item.setText(1, str(d.begin)+'=>'+str(d.end))
        item.setText(2, str(d.end.bits_count() - d.begin.bits_count()))
        for f in d.fields:
            if type(f) == Table:
                item.addChild(self.__print_table(f))
            else:
                child = QTreeWidgetItem()
                self.__fields[child] = (f, d.name+'.'+f.name)
                child.setText(0, f.name)
                child.setText(1, self.__field_value_str(getattr(d, f.name)))
                child.setText(2, str(f.end.bits_count() - f.begin.bits_count()))
                item.addChild(child)
        return item

    def load(self, d: Table):
        self.__fields.clear()
        self.widget.clear()
        if d != None:
            top = self.__print_table(d)
            self.widget.addTopLevelItem(top)
            self.widget.expandAll()
            self.widget.header().resizeSections(QHeaderView.ResizeToContents)
            self.widget.setCurrentIndex(self.widget.model().index(0,0))

class ChooseParserDlg(QDialog):
    default_changed = Signal(str)

    def __init__(self, p, default):
        super(ChooseParserDlg, self).__init__()
        self.setWindowTitle('选择解析器')
        self.parsers = list(p.exports.keys())
        self.default = default
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.accept)
        self.__udpate_list()

        self.input = QLineEdit()
        self.input.setText(default)
        self.input.textEdited.connect(self.__udpate_list)

        self.count = QSpinBox()
        self.count.setMinimum(1)
        self.count.setMaximum(10000)
        self.count.setValue(1)

        hbox = QHBoxLayout()
        btn = QPushButton('设为默认')
        btn.clicked.connect(self.__on_set_default_clicked)
        hbox.addWidget(btn)
        btn = QPushButton('确定')
        btn.setDefault(True)
        btn.clicked.connect(self.accept)
        hbox.addWidget(btn)
        btn = QPushButton('取消')
        btn.clicked.connect(self.reject)
        hbox.addWidget(btn)

        vbox = QVBoxLayout()
        vbox.addWidget(self.input)
        vbox.addWidget(self.list)
        vbox.addWidget(self.count)
        vbox.addLayout(hbox)
        vbox.setStretch(1, 1)

        self.setLayout(vbox)

    def __udpate_list(self, filter=None):
        self.list.clear()
        if filter != None and len(filter) > 0:
            self.list.addItems([p for p in self.parsers if filter in p])
        else:
            self.list.addItems(self.parsers)
        self.list.setCurrentRow(self.parsers.index(self.default))

    def __on_set_default_clicked(self):
        self.default = self.list.currentItem().text()
        self.default_changed.emit(self.default)

#todo 改造为向导视图
#Step1 可预览地创建fields
#Step2 查看透视图结果
#返回Step1或关闭
class PerspectiveDlg(QDialog):
    show_item_requested = Signal(Table)

    def header_labels(self, fields):
        labels = []
        for f in fields:
            labels.append(f.split('.')[-1])
        return labels

    def __init__(self, items, fields):
        super(PerspectiveDlg, self).__init__()
        self.setWindowTitle('透视图')
        self.items = items
        self.table = QTableWidget()
        self.table.setColumnCount(len(fields))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setHorizontalHeaderLabels(self.header_labels(fields))
        self.table.currentItemChanged.connect(self.__on_current_item_changed)
        for i in range(len(items)):
            item = items[i]
            self.table.insertRow(i)
            for j in range(len(fields)):
                text = str(item.get_value_by_path(fields[j].strip()))
                self.table.setItem(i, j, QTableWidgetItem(text))
        self.table.horizontalHeader().resizeSections(QHeaderView.ResizeToContents)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.resize(500, 800)

    def __on_current_item_changed(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self.items):
            return

        self.show_item_requested.emit(self.items[r])


class MainWnd(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_viewer = None
        self.memory_viewer = None
        self.plugin = None
        self.perspective_dlg = None

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle('bitinsight')
        layout = QGridLayout()

        # 左侧视图
        left_min_width = 250
        left_max_width = 400
        self.editor_tab = QTabWidget()
        self.editor_tab.currentChanged.connect(self.on_editor_tab_changed)
        self.data_nav = DataNav()
        self.editor_tab.setMinimumWidth(left_min_width)
        self.editor_tab.setMaximumWidth(left_max_width)
        self.data_nav.setMinimumWidth(left_min_width)
        self.data_nav.setMaximumWidth(left_max_width)

        # 中间视图
        mid_min_width = 350
        self.table_viewer = TableViewer()
        self.doc_viewer = DocViewer()
        self.table_viewer.field_selected.connect(self.on_field_selected)
        self.table_viewer.widget.setMinimumWidth(mid_min_width)

        # 右侧视图
        self.record_tab = QTabWidget()
        self.history_viewer = HistoryViewer()
        self.history_viewer.show_item_requested.connect(self.on_show_parser_ret)
        self.history_viewer.perspective_requested.connect(self.create_perspective)
        self.context_viewer = ContextViewer()
        self.table_viewer.add_field_to_context.connect(self.on_add_field_context)
        self.context_viewer.show_item_requested.connect(self.on_show_parser_ret)
        self.record_tab.addTab(self.history_viewer.widget, '历史记录')
        self.record_tab.addTab(self.context_viewer.widget, '上下文')
        self.record_tab.currentChanged.connect(self.on_record_tab_changed)

        # 布局
        c1=1
        c2=1
        c3=1
        r1=9
        r2=1
        r_1=7
        r_2=3
        layout.addWidget(self.editor_tab, 0, 0, r1, c1)
        layout.addWidget(self.data_nav, r1, 0, r2, c1)
        layout.addWidget(self.table_viewer.widget, 0, c1, r_1, c2)
        layout.addWidget(self.record_tab, 0, c1+c2, r_1, c3)
        layout.addWidget(self.doc_viewer.editor, r_1, c1, r_2, c2+c3)
        layout.setColumnStretch(c1, 1)
        layout.setSpacing(3)

        self.setMenuBar(self.create_menu_bar())
        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(layout)

    def create_perspective(self, items):
        (text, ok) = QInputDialog.getMultiLineText(self, '输入透视图字段', '每行输入一个字段，按照如"header.size"这样的点号分割形式填写')
        if ok:
            self.perspective_dlg = PerspectiveDlg(items, text.split('\n'))
            self.perspective_dlg.show_item_requested.connect(self.on_show_parser_ret)
            self.perspective_dlg.show()

    def on_add_field_context(self,f):
        self.context_viewer.add(f)

    def __del_memory_viewer(self):
        if self.memory_viewer != None:
            del self.memory_viewer
            self.memory_viewer = None
            self.editor_tab.removeTab(1)

    def __check_memory_viewer(self, f:Field):
        bs = f.bs
        if bs.mem != self.file_viewer.mem:
            if self.memory_viewer != None and self.memory_viewer.mem == bs.mem:
                self.editor_tab.setCurrentIndex(1)
                return self.memory_viewer
            self.__del_memory_viewer()

            self.memory_viewer = MemoryViewer(bs.mem)
            self.memory_viewer.editor.analyse_requested.connect(self.on_analyse_request)
            self.memory_viewer.editor.default_analyse_requested.connect(self.on_default_parser_analyse)
            self.editor_tab.addTab(self.memory_viewer.editor, f.name)
            self.editor_tab.setCurrentIndex(1)
            return self.memory_viewer
        else:
            self.__del_memory_viewer()
            self.editor_tab.setCurrentIndex(0)
            return self.file_viewer

    def on_show_parser_ret(self, d: Table):
        self.table_viewer.load(d)

    def current_data_viewer(self):
        index = self.editor_tab.currentIndex()
        if index < 0:
            return None
        viewer = self.file_viewer if index == 0 else self.memory_viewer
        return viewer

    def on_editor_tab_changed(self):
        viewer = self.current_data_viewer()
        if viewer == None:
            return
        self.data_nav.set_data_viewer(viewer)

    def on_record_tab_changed(self):
        viewer = self.history_viewer if self.record_tab.currentIndex() == 0 else self.context_viewer
        viewer.notify_current_selected()

    def on_field_selected(self, f:Field, dockey:str):
        if dockey == None:
            self.doc_viewer.clear()
        else:
            self.doc_viewer.load(self.plugin.doc.get(dockey))
        
        if f == None:
            if self.memory_viewer:
                self.file_viewer.clear_higlight()
            if self.memory_viewer:
                self.memory_viewer.clear_higlight()
        else:
            viewer = self.__check_memory_viewer(f)
            viewer.highlight(f.begin, f.end)

    def set_plugin_default(self, s):
        self.plugin.default = s
        if self.file_viewer:
            self.file_viewer.editor.set_default_parser(s)
        if self.memory_viewer:
            self.memory_viewer.editor.set_default_parser(s)

    def on_analyse(self, bs:BitStream, parser, count):
        for i in range(count):
            d = Table('root', self.context_viewer.get_context(), bs)
            try:
                d.add_table(self.plugin.exports[parser])
            except Exception as e:
                if type(e) == EOFError:
                    show_modal_error('数据不足，请加载更多数据')
                else:
                    et, ev, tb = sys.exc_info()
                    msg = traceback.format_exception(et, ev, tb)
                    show_modal_error('解析过程出错：%s\n%s'%(str(e), ''.join(msg)))
                return

            ret = getattr(d, parser)
            self.history_viewer.add(ret)
        self.current_data_viewer().moveto(bs.pos())

    def on_default_parser_analyse(self, bs: BitStream):
        self.on_analyse(bs, self.plugin.default, 1)

    def on_analyse_request(self, bs: BitStream):
        if self.plugin == None:
            show_modal_error('还未加载插件')
            return
        
        dlg = ChooseParserDlg(self.plugin, self.plugin.default)
        dlg.default_changed.connect(self.set_plugin_default)
        if QDialog.Rejected ==  dlg.exec_():
            return

        parser = dlg.list.currentItem().text()
        count = dlg.count.value()
        
        self.on_analyse(bs, parser, count)

    def menu_open_file(self):
        ret = QFileDialog.getOpenFileName(self, '选择要打开的文件')
        path = ret[0]
        if len(path) == 0:
            return
        
        if self.file_viewer:
            e = self.file_viewer.editor
        
        self.editor_tab.clear()
        self.file_viewer = None
        self.memory_viewer = None
        #在不同文件间共享有意义吗？（开启会导致highlight失败）
        self.history_viewer.clear()
        self.context_viewer.clear()

        file_info = QFileInfo(path)
        self.file_viewer = FileViewer(path)
        self.file_viewer.editor.analyse_requested.connect(self.on_analyse_request)
        self.file_viewer.editor.default_analyse_requested.connect(self.on_default_parser_analyse)
        self.editor_tab.insertTab(0, self.file_viewer.editor, file_info.fileName())

        self.table_viewer.widget.clear()

        suffix = file_info.suffix()
        if not self.plugin or self.plugin.name != suffix:
            self.plugin = plugin.load_plugin(file_info.suffix())
            self.doc_viewer.img_path = 'plugins/'+suffix
        self.set_plugin_default(self.plugin.default)
        

    def config_recent_files_menu(self, menu):
        pass

    def config_file_menu(self,menu):
        menu.addAction('打开...').triggered.connect(self.menu_open_file)
        self.config_recent_files_menu(menu.addMenu('最近打开的文件'))

    def create_menu_bar(self):
        menubar = QMenuBar()
        self.config_file_menu(menubar.addMenu('文件'))
        return menubar

if __name__ == "__main__":
    app = QApplication([])

    widget = MainWnd()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())
