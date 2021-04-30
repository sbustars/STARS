import os
import sys
from threading import Thread

sys.path.append(os.getcwd())  # must be ran in sbumips directory (this is bc PYTHONPATH is weird in terminal)
from constants import REGS, F_REGS
from interpreter.interpreter import Interpreter
from sbumips import assemble
from settings import settings
from controller import Controller
from gui.vt100 import VT100
from gui.textedit import TextEdit
from gui.syntaxhighlighter import Highlighter

from PySide2.QtCore import Qt, QSemaphore, QEvent, Signal, QFile, QStringListModel
from PySide2.QtGui import QTextCursor, QGuiApplication, QPalette, QColor, QFont, QKeySequence, QCursor
from PySide2.QtWidgets import *

'''
https://github.com/sbustars/STARS
Copyright 2020 Kevin McDonnell, Jihu Mun, and Ian Peitzsch
Developed by Kevin McDonnell (ktm@cs.stonybrook.edu),
Jihu Mun (jihu1011@gmail.com),
and Ian Peitzsch (irpeitzsch@gmail.com)
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''


def to_ascii(c):
    if c in range(127):
        if c == 0:  # Null terminator
            return "\\0"

        elif c == 9:  # Tab
            return "\\t"

        elif c == 10:  # Newline
            return "\\n"

        elif c >= 32:  # Regular character
            return chr(c)

        else:  # Invalid character
            return '.'

    else:  # Invalid character
        return '.'


class MainWindow(QMainWindow):
    changed_interp = Signal()

    def __init__(self, app):
        super().__init__()
        self.vt100 = None

        self.app = app

        self.controller = Controller(None, None)

        settings['gui'] = True
        settings['debug'] = True

        self.console_sem = QSemaphore(1)
        self.out_pos = 0
        self.mem_sem = QSemaphore(1)
        self.result = None
        self.intr = None
        self.cur_file = None

        self.rep = 'Hexadecimal'

        self.running = False
        self.run_sem = QSemaphore(1)

        self.breakpoints = []

        self.default_theme = QGuiApplication.palette()
        self.dark = False
        self.palette = QPalette()
        self.palette.setColor(QPalette.Window, QColor(25, 25, 25))  # 53 53 53
        self.palette.setColor(QPalette.WindowText, Qt.darkCyan)
        self.palette.setColor(QPalette.Base, QColor(53, 53, 53))  # 25 25 25
        self.palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        self.palette.setColor(QPalette.ToolTipBase, Qt.darkCyan)
        self.palette.setColor(QPalette.ToolTipText, Qt.darkCyan)
        self.palette.setColor(QPalette.Text, Qt.darkCyan)
        self.palette.setColor(QPalette.Button, QColor(53, 53, 53))
        self.palette.setColor(QPalette.ButtonText, Qt.darkCyan)
        self.palette.setColor(QPalette.BrightText, Qt.red)
        self.palette.setColor(QPalette.Link, QColor(42, 130, 218))
        self.palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        self.palette.setColor(QPalette.HighlightedText, Qt.black)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("STARS")
        self.lay = QGridLayout()
        self.lay.setSpacing(0)
        self.init_menubar()
        self.init_instrs()
        self.init_mem()
        self.init_out()
        self.init_regs()
        self.init_pa()
        self.init_cop_flags()
        self.add_edit()
        center = QWidget()
        center.setLayout(self.lay)
        self.setCentralWidget(center)
        self.showMaximized()

    def init_regs(self):
        self.float = False
        self.reg_button = QPushButton("Change")
        self.reg_button.clicked.connect(self.update_reg)
        self.reg_box = QGridLayout()
        self.regs = {}
        self.rlabels = []
        self.reg_box.setSpacing(0)
        i = 0
        for r in REGS:
            self.regs[r] = QLabel('0x00000000')
            self.regs[r].setFont(QFont("Courier New", 8))
            self.regs[r].setFrameShape(QFrame.Box)
            self.regs[r].setFrameShadow(QFrame.Raised)
            # self.regs[r].setLineWidth(2)
            reg_label = QLabel(r)
            reg_label.setFont(QFont("Courier New", 8))
            self.rlabels.append(reg_label)
            self.reg_box.addWidget(reg_label, i, 0)
            self.reg_box.addWidget(self.regs[r], i, 1)
            i += 1

        # self.freg_box = QGridLayout()
        # self.fregs = {}
        # self.freg_box.setSpacing(0)
        # i = 0
        for r in F_REGS:
            self.regs[r] = QLabel('0x00000000')
            self.regs[r].setFont(QFont("Courier New", 8))
            self.regs[r].setFrameShape(QFrame.Box)
            self.regs[r].setFrameShadow(QFrame.Raised)
            # self.regs[r].setLineWidth(2)
            # reg_label = QLabel(r)
            # reg_label.setFont(QFont("Courier New", 8))
            # self.freg_box.addWidget(reg_label, i, 0)
            # self.freg_box.addWidget(self.fregs[r], i, 1)
            # i += 1
        self.lay.addLayout(self.reg_box, 1, 3, 2, 1)
        self.lay.addWidget(self.reg_button, 0, 3)
        # self.lay.addLayout(self.freg_box, 1, 4, 2, 1)

    def init_cop_flags(self):
        flag_box = QGridLayout()
        flag_box.setSpacing(0)
        self.flags = []
        count = 0
        for i in range(1, 5):
            c1 = QCheckBox(f'{count}')
            self.flags.append(c1)
            count += 1
            c2 = QCheckBox(f'{count}')
            count += 1
            self.flags.append(c2)
            flag_box.addWidget(c1, i, 0)
            flag_box.addWidget(c2, i, 1)
        flag_box.addWidget(QLabel('Coproc 1 Flags:'), 0, 0)
        self.lay.addLayout(flag_box, 3, 3)

    def init_instrs(self):
        i = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(i)
        self.instrs = []
        self.pcs = []
        self.checkboxes = []
        self.instr_grid = QGridLayout()
        self.instr_grid.setSpacing(0)

        i.setLayout(self.instr_grid)
        scroll.setMaximumHeight(300)
        self.lay.addWidget(scroll, 1, 1)
        # self.instrs = QTextEdit()
        # self.instrs.setLineWrapMode(QTextEdit.NoWrap)
        # self.instrs.setReadOnly(True)
        # self.left.addWidget(self.instrs)

    def add_edit(self):
        self.files = {} # filename -> (dirty: bool, path: str)
        self.new_files = set()
        self.highlighter = {}

        self.count = 0
        self.len = 0
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        nt = QPushButton('+')
        nt.clicked.connect(self.new_tab)
        self.tabs.setCornerWidget(nt)


        text_edit = TextEdit()
        text_edit.setAcceptRichText(False)
        self.comp = QCompleter()
        self.comp.setModel(self.modelFromFile(r"wordslist.txt", self.comp))
        self.comp.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self.comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.comp.setWrapAround(False)
        text_edit.setCompleter(self.comp)

        self.new_tab()

        self.lay.addWidget(self.tabs, 1, 0)

    def modelFromFile(self, filename, comp):
        f = QFile(filename)
        if not f.open(QFile.ReadOnly):
            return QStringListModel(comp)

        QGuiApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        words = []
        while not f.atEnd():
            line = f.readLine()
            if len(line) > 0:
                s = str(line.trimmed(), encoding='ascii')
                words.append(s)

        QGuiApplication.restoreOverrideCursor()

        return QStringListModel(words, comp)

    def init_menubar(self):
        bar = self.menuBar()

        file_ = bar.addMenu("File")
        open_ = QAction("Open", self)
        open_.triggered.connect(self.open_file)
        file_.addAction(open_)
        save_ = QAction("Save", self)
        save_.triggered.connect(self.save_file)
        file_.addAction(save_)

        tools = bar.addMenu("Tools")
        dark_mode = QAction("Dark Mode", self)
        dark_mode.triggered.connect(self.change_theme)
        tools.addAction(dark_mode)
        vt = QAction("MMIO Display", self)
        vt.triggered.connect(self.launch_vt100)
        tools.addAction(vt)

        sett = bar.addMenu("Settings")
        for s in ['garbage_memory', 'garbage_registers', 'disp_instr_count', 'warnings']:
            pass
        mem_wid = QWidgetAction(sett)
        mem_box = QCheckBox("Garbage Memory")
        if settings['garbage_memory']:
            mem_box.setChecked()
        mem_box.stateChanged.connect(lambda: self.controller.setSetting('garbage_memory', mem_box.isChecked()))
        mem_wid.setDefaultWidget(mem_box)
        sett.addAction(mem_wid)

        reg_wid = QWidgetAction(sett)
        reg_box = QCheckBox("Garbage Registers")
        if settings['garbage_registers']:
            reg_box.setChecked()
        reg_box.stateChanged.connect(lambda: self.controller.setSetting('garbage_registers', reg_box.isChecked()))
        reg_wid.setDefaultWidget(reg_box)
        sett.addAction(reg_wid)

        inst_wid = QWidgetAction(sett)
        inst_box = QCheckBox("Instruction Count")
        if settings['disp_instr_count']:
            inst_box.setChecked()
        inst_box.stateChanged.connect(lambda: self.controller.setSetting('disp_instr_count', inst_box.isChecked()))
        inst_wid.setDefaultWidget(inst_box)
        sett.addAction(inst_wid)

        warn_wid = QWidgetAction(sett)
        warn_box = QCheckBox("Warnings")
        if settings['warnings']:
            warn_box.setChecked()
        warn_box.stateChanged.connect(lambda: self.controller.setSetting('warnings', warn_box.isChecked()))
        warn_wid.setDefaultWidget(warn_box)
        sett.addAction(warn_wid)

        help_ = bar.addMenu("Help")

        run = bar.addMenu("Run")
        asm = QAction("Assemble (F3)", self)
        asm.triggered.connect(lambda: self.assemble(self.tabs.currentWidget().name) if self.tabs.currentWidget().name else None)
        asm_short = QShortcut(QKeySequence(self.tr("F3")), self)
        asm_short.activated.connect(lambda: asm.trigger())
        run.addAction(asm)
        start = QAction("Start (F5)", self)
        start.triggered.connect(self.start)
        start_short = QShortcut(QKeySequence(self.tr("F5")), self)
        start_short.activated.connect(lambda: start.trigger())
        run.addAction(start)
        step = QAction("Step (F7)", self)
        step.triggered.connect(self.step)
        step_short = QShortcut(QKeySequence(self.tr("F7")), self)
        step_short.activated.connect(lambda: step.trigger())
        run.addAction(step)
        back = QAction("Back (F8)", self)
        back.triggered.connect(self.reverse)
        back_short = QShortcut(QKeySequence(self.tr("F8")), self)
        back_short.activated.connect(lambda: back.trigger())
        run.addAction(back)
        pause = QAction('Pause (F9)', self)
        pause.triggered.connect(self.pause)
        pause_short = QShortcut(QKeySequence(self.tr("F9")), self)
        pause_short.activated.connect(lambda: pause.trigger())
        run.addAction(pause)

        asm_but = QAction("✇", self)
        # asm_but.setToolTip('F3')
        # asm_but.setToolTipsVisible(True)
        # asm_but.setWhatsThis('F3')
        asm_but.triggered.connect(lambda : asm.trigger())
        bar.addAction(asm_but)
        start_but = QAction("▶️", self)
        start_but.triggered.connect(lambda: start.trigger())
        bar.addAction(start_but)
        step_but = QAction("⏭", self)
        step_but.triggered.connect(lambda: step.trigger())
        bar.addAction(step_but)
        back_but = QAction("⏮", self)
        back_but.triggered.connect(lambda: back.trigger())
        bar.addAction(back_but)
        pause_but = QAction("⏸", self)
        pause_but.triggered.connect(lambda: pause.trigger())
        bar.addAction(pause_but)

        self.instr_count = QLabel("Instruction Count: 0\t\t")
        bar.setCornerWidget(self.instr_count)

    def init_out(self):
        self.out = QTextEdit()
        self.out.setMaximumHeight(100)
        self.out.installEventFilter(self)
        self.lay.addWidget(self.out, 3, 0, 1, 2)

    def init_mem(self):
        grid = QGridLayout()
        self.section_dropdown = QComboBox()
        self.section_dropdown.addItems(['Kernel', '.data', 'stack', 'MMIO'])
        self.section_dropdown.currentTextChanged.connect(self.change_section)
        grid.addWidget(self.section_dropdown, 0, 0)
        grid.setSpacing(0)
        grid.addWidget(QLabel("+0"), 0, 1)
        grid.addWidget(QLabel("+4"), 0, 2)
        grid.addWidget(QLabel("+8"), 0, 3)
        grid.addWidget(QLabel("+c"), 0, 4)
        self.mem_right = QPushButton("🡣")
        self.mem_right.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mem_right.setMaximumWidth(25)
        self.mem_left = QPushButton("🡡")
        self.mem_left.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mem_left.setMaximumWidth(25)
        self.hdc_dropdown = QComboBox()
        self.hdc_dropdown.addItems(["Hexadecimal", "Decimal", "ASCII"])
        self.hdc_dropdown.currentTextChanged.connect(self.change_rep)
        grid.addWidget(self.mem_left, 1, 5, 8, 1)
        grid.addWidget(self.mem_right, 9, 5, 8, 1)
        grid.addWidget(self.hdc_dropdown, 1, 6, 1, 2)
        self.addresses = [0] * 16
        self.addresses = self.addresses[:]
        self.mem_vals = []
        self.base_address = 0
        count = 0
        for i in range(1, 17):
            for j in range(5):
                q = QLabel(" ")
                q.setFrameShape(QFrame.Box)
                q.setFrameShadow(QFrame.Raised)
                q.setLineWidth(2)
                if j == 0:
                    q.setText(f'0x{count:08x}')
                    q.setFont(QFont("Courier New"))
                    self.addresses[i - 1] = q
                else:
                    self.mem_vals.append(q)
                grid.addWidget(q, i, j)
            count += 16

        labels = QScrollArea()
        l = QWidget()
        labels.setMaximumHeight(400)
        labels.setWidget(l)
        self.lab_grid = QVBoxLayout()
        labels.setLayout(self.lab_grid)
        grid.addWidget(labels, 2, 6, 15, 2)

        self.lay.addLayout(grid, 2, 0, 1, 2)

    def init_pa(self):
        self.pa = QLineEdit()
        pa = QHBoxLayout()
        label = QLabel('Program Arguments:')
        pa.addWidget(label)
        pa.addWidget(self.pa)
        self.lay.addLayout(pa, 0, 0, 1, 2)

    def save_file(self, wid=None, ind=None):
        if not wid:
            wid = self.tabs.currentWidget()
        if not ind:
            ind = self.tabs.currentIndex()
        key = wid.name
        to_write = wid.toPlainText()
        f = None
        try:
            if key in self.files:
                if not self.files[key]:
                    return
                f = open(key, 'w+')

                f.write(to_write)
                f.close()
                self.files[key] = False
                n = key.split('/')[-1]
                self.tabs.setTabText(ind, n)

            else:
                filename = QFileDialog.getSaveFileName(self, 'Save', f'{key}', options=QFileDialog.DontUseNativeDialog)
                if len(filename) < 2 or filename[0] is None:
                    return
                key = filename[0]
                f = open(key, 'w+')

                f.write(to_write)
                f.close()
                wid.name = filename[0]
                n = filename[0].split('/')[-1]
                self.tabs.setTabText(ind, n)
                self.files[key] = False


        except:
            if f:
                f.close()
            return

    def open_file(self):
        try:
            filename = QFileDialog.getOpenFileName(self, 'Open', '', options=QFileDialog.DontUseNativeDialog)
        except:
            self.out.setPlainText(f'Could not open file\n')
            return

        if not filename or len(filename[0]) == 0:
            return

        s = []
        with open(filename[0]) as f:
            s = f.readlines()
        wid = TextEdit(name=filename[0])
        wid.textChanged.connect(self.update_dirty)
        wid.setCompleter(self.comp)
        wid.setPlainText(''.join(s))
        n = filename[0].split('/')[-1]
        if not filename[0] in self.files:
            self.files[filename[0]] = False
            self.new_tab(wid=wid, name=n)


    def assemble(self, filename):
        try:
            if self.running:
                self.intr.end.emit(False)
            for i in range(self.len):
                self.save_file(wid=self.tabs.widget(i), ind=i)
            self.out.setPlainText('')
            self.result = assemble(filename)
            self.intr = Interpreter(self.result, self.pa.text().split())
            self.controller.set_interp(self.intr)
            self.instrs = []
            self.update_screen(self.intr.reg['pc'])
            self.fill_labels()
            self.intr.step.connect(self.update_screen)
            self.intr.console_out.connect(self.update_console)
            self.mem_right.clicked.connect(self.mem_rightclick)
            self.mem_left.clicked.connect(self.mem_leftclick)
            self.intr.end.connect(self.set_running)
            self.breakpoints = []
            self.setWindowTitle(f'STARS')

        except Exception as e:
            if hasattr(e, 'message'):
                self.console_sem.acquire()
                self.out.setPlainText(type(e).__name__ + ": " + e.message)
                self.console_sem.release()

            else:
                self.console_sem.acquire()
                self.out.setPlainText(type(e).__name__ + ": " + str(e))
                self.console_sem.release()

    def change_theme(self):
        if not self.dark:
            self.app.setPalette(self.palette)
            for reg in REGS:
                self.regs[reg].setPalette(self.palette)
        else:
            self.app.setPalette(self.default_theme)
            for reg in REGS:
                self.regs[reg].setPalette(self.default_theme)
        self.dark = not self.dark

    def start(self):
        if not self.controller.good():
            return
        if not self.running:
            self.set_running(True)
            self.controller.set_interp(self.intr)
            self.changed_interp.emit()
            self.controller.pause(False)
            self.out.setPlainText('')
            self.out_pos = self.out.textCursor().position()
            self.program = Thread(target=self.intr.interpret, daemon=True)
            for b in self.breakpoints:
                self.controller.add_breakpoint(b)
            self.program.start()
        elif not self.controller.cont():
            self.controller.pause(False)

    def pause(self):
        if not self.controller.good():
            return
        if self.controller.cont():
            self.controller.pause(True)

    def step(self):
        if not self.controller.good():
            return
        if not self.running:
            self.set_running(True)
            self.controller.set_interp(self.intr)
            self.controller.set_pause(True)
            self.out.setPlainText('')
            self.program = Thread(target=self.intr.interpret, daemon=True)
            for b in self.breakpoints:
                self.controller.add_breakpoint(b)
            self.program.start()
        else:
            self.controller.set_pause(True)

    def reverse(self):
        if not self.controller.good() or not self.running:
            return
        else:
            self.controller.reverse()

    def change_rep(self, t):
        self.rep = t
        if self.controller.good():
            self.update_screen()

    def change_section(self, t):
        if t == 'Kernel':
            self.base_address = 0
        elif t == '.data':
            self.base_address = settings['data_min']
        elif t == 'MMIO':
            self.base_address = 0xffff0000
        else:
            self.base_address = settings['initial_$sp'] - 0xc
            if self.base_address % 256 != 0:
                self.base_address -= self.base_address % 256
        if self.controller.good():
            self.fill_mem()

    def set_running(self, run):
        self.run_sem.acquire()
        self.running = run
        if not run:
            self.instrs = []
        self.run_sem.release()

    def update_screen(self, pc):
        self.fill_reg()
        self.fill_instrs(pc)
        self.fill_mem()
        self.fill_flags()
        self.instr_count.setText(f'Instruction Count: {self.controller.get_instr_count()}\t\t')

    def fill_labels(self):
        for i in reversed(range(self.lab_grid.count())):
            self.lab_grid.itemAt(i).widget().setParent(None)
        labels = self.controller.get_labels()
        for l in labels:
            q = QPushButton(f'{l}: 0x{labels[l]:08x}')
            q.clicked.connect(lambda : self.mem_move_to(labels[l]))
            self.lab_grid.addWidget(q)

    def mem_move_to(self, addr):
        self.mem_sem.acquire()

        if addr % 256 == 0:
            self.base_address = addr

        else:
            addr -= (addr % 256)
            self.base_address = addr

        self.mem_sem.release()

        self.section_dropdown.setCurrentIndex(0)
        if addr >= settings['data_min']:
            self.section_dropdown.setCurrentIndex(1)
        if addr >= 0xffff0000:
            self.section_dropdown.setCurrentIndex(2)

        self.fill_mem()

    def fill_flags(self):
        for i in range(len(self.intr.condition_flags)):
            if self.intr.condition_flags[i]:
                self.flags[i].setCheckState(Qt.Checked)
            else:
                self.flags[i].setCheckState(Qt.Unchecked)

    def fill_reg(self):
        i = 0

        for j in range(len(REGS)):
            if self.float and j < len(F_REGS):
                r = F_REGS[j]
                self.rlabels[i].setText(f'{r:5}')
                i += 1
                if self.rep == "Decimal":
                    self.regs[r].setText(f'{self.intr.f_reg[r]:8f}')
                else:
                    self.regs[r].setText(f'0x{self.controller.get_reg_word(r):08x}')
            else:
                r = REGS[j]
                self.rlabels[i].setText(f'{r:5}')
                i += 1
                if self.rep == "Decimal":
                    self.regs[r].setText(str(self.intr.reg[r]))
                else:
                    a = self.intr.reg[r]
                    if a < 0:
                        a += 2 ** 32
                    self.regs[r].setText(f'0x{a:08x}')


    def fill_instrs(self, pc):
        # pc = self.intr.reg['pc']
        if len(self.instrs) > 0:
            # fmt = QTextCharFormat()
            # self.prev_instr.setTextFormat(fmt)
            #
            #
            # fmt = QTextCharFormat()
            # fmt.setBackground(Qt.cyan)
            # self.instrs[pc - settings['initial_pc']].setTextFormat(fmt)
            self.prev_instr.setStyleSheet("QLineEdit { background: rgb(255, 255, 255) };")
            prev_ind = (pc - settings['initial_pc']) // 4
            if prev_ind < len(self.instrs):
                self.prev_instr = self.instrs[prev_ind]
            self.prev_instr.setStyleSheet("QLineEdit { background: rgb(0, 255, 255) };")

        else:
            mem = self.intr.mem
            count = 0
            for k in mem.text.keys():
                if type(mem.text[k]) is not str:
                    i = mem.text[k]
                    check = QCheckBox()
                    check.stateChanged.connect(lambda state, i=i: self.add_breakpoint(('b', str(i.filetag.file_name)[1:-1], str(i.filetag.line_no))) if state == Qt.Checked else self.remove_breakpoint(
                        ('b', str(i.filetag.file_name)[1:-1], str(i.filetag.line_no))))
                    self.checkboxes.append(check)
                    self.instr_grid.addWidget(check, count, 0)
                    if i.is_from_pseudoinstr:
                        q = QLineEdit(f'0x{int(k):08x}\t{i.original_text} ( {i.basic_instr()} )')
                        q.setReadOnly(True)
                        q.setFont(QFont("Courier New", 10))
                        self.instrs.append(q)
                        self.instr_grid.addWidget(q, count, 1)
                    else:
                        q = QLineEdit(f'0x{int(k):08x}\t{i.basic_instr()}')
                        q.setFont(QFont("Courier New", 10))
                        q.setReadOnly(True)
                        self.instrs.append(q)
                        self.instr_grid.addWidget(q, count, 1)
                    count += 1
            self.instrs[0].setStyleSheet("QLineEdit { background: rgb(0, 255, 255) };")
            self.prev_instr = self.instrs[0]

    def fill_mem(self):
        self.mem_sem.acquire()
        count = self.base_address
        for q in self.mem_vals:
            if self.rep == "Decimal":
                q.setText(f'{self.controller.get_byte(count + 3):3} {self.controller.get_byte(count + 2):3} {self.controller.get_byte(count + 1):3} {self.controller.get_byte(count):3}')
            elif self.rep == "ASCII":
                q.setText(
                    f'{to_ascii(self.controller.get_byte(count + 3, signed=True)):2} {to_ascii(self.controller.get_byte(count + 2, signed=True)):2} {to_ascii(self.controller.get_byte(count + 1, signed=True)):2} {to_ascii(self.controller.get_byte(count, signed=True)):2}')
            else:
                q.setText(
                    f'0x{self.controller.get_byte(count + 3):02x} 0x{self.controller.get_byte(count + 2):02x} 0x{self.controller.get_byte(count + 1):02x} 0x{self.controller.get_byte(count):02x}')
            count += 4
        count = self.base_address
        for a in self.addresses:
            a.setText(f'0x{count:08x}')
            count += 16
        self.mem_sem.release()

    def mem_rightclick(self):
        if not self.controller.good():
            return
        self.mem_sem.acquire()
        if self.base_address <= settings['data_max'] - 256:
            self.base_address += 256
        self.mem_sem.release()
        self.fill_mem()

    def mem_leftclick(self):
        if not self.controller.good():
            return
        self.mem_sem.acquire()
        if self.base_address >= 256:
            self.base_address -= 256
        self.mem_sem.release()
        self.fill_mem()

    def update_console(self, s):
        self.console_sem.acquire()
        cur = self.out.textCursor()
        cur.setPosition(QTextCursor.End)
        self.out.insertPlainText(s)
        self.out_pos = self.out.textCursor().position()
        self.console_sem.release()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and obj is self.out:
            if event.key() == Qt.Key_Return and self.out.hasFocus():
                self.console_sem.acquire()
                cur = self.out.textCursor()
                cur.setPosition(self.out_pos, QTextCursor.KeepAnchor)
                s = cur.selectedText()
                cur.setPosition(QTextCursor.End)
                self.out_pos = self.out.textCursor().position()
                self.console_sem.release()
                self.intr.set_input(s)
        return super().eventFilter(obj, event)

    def add_breakpoint(self, cmd):
        self.controller.add_breakpoint(cmd)
        self.breakpoints.append(cmd)

    def remove_breakpoint(self, cmd):
        self.controller.remove_breakpoint((f'"{cmd[1]}"', cmd[2]))
        self.breakpoints.remove(cmd)

    def launch_vt100(self):
        if self.vt100:
            self.vt100.close()
        self.vt100 = VT100(self.controller, self.changed_interp)

    def update_reg(self):
        self.float = not self.float
        self.fill_reg()

    def close_tab(self, i):
        if self.tabs.widget(i).name in self.files:
            self.files.pop(self.tabs.widget(i).name)
        self.tabs.removeTab(i)
        self.len -= 1

    def new_tab(self, wid=None, name=''):
        self.count += 1
        self.len += 1
        if len(name) == 0:
            name = f'main{"" if self.count == 1 else self.count-1}.asm'
        if not wid:
            wid = TextEdit(name=name)
            wid.setAcceptRichText(False)
            wid.setCompleter(self.comp)
            wid.textChanged.connect(self.update_dirty)
        self.tabs.addTab(wid, name)
        self.highlighter[name] = Highlighter(wid.document())

    def update_dirty(self):
        w = self.tabs.currentWidget()
        i = self.tabs.currentIndex()
        if w is not None and (w.name not in self.files or not self.files[w.name]):
            self.tabs.setTabText(i, f'{self.tabs.tabText(i)} *')
        self.files[w.name] = True

if __name__ == "__main__":
    app = QApplication()
    window = MainWindow(app)
    app.exec_()