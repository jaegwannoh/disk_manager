# -*- coding: utf-8 -*-
"""
DiskWatcher - 서버 설정 창 (servers.txt 추가/수정/삭제)
"""
from PyQt4 import QtCore, QtGui

from common import APP_NAME
from config import make_target, MAX_WAIT_MIN

COLUMNS = [u'이름', u'IP', u'포트', u'user', u'pw', u'path', u'임계치']
PW_MASK = u'●' * 4


class ConfigDialog(QtGui.QDialog):
    def __init__(self, config, file_name=u'servers.txt', parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(u'서버 설정 — %s' % file_name)
        self.cfg = config.copy()
        self._build_ui()
        self.spin_wait.setValue(self.cfg.wait_min)
        self.reload_table()
        self.resize(860, 640)

    # ------------------------------------------------------------ 화면
    def _build_ui(self):
        root = QtGui.QVBoxLayout(self)
        root.setSpacing(12)

        top = QtGui.QHBoxLayout()
        top.addWidget(QtGui.QLabel(u'시간 기준 서버'))
        self.combo_time = QtGui.QComboBox()
        self.combo_time.setMinimumWidth(160)
        top.addWidget(self.combo_time)
        top.addSpacing(24)
        top.addWidget(QtGui.QLabel(u'체크 후 대기'))
        self.spin_wait = QtGui.QSpinBox()
        self.spin_wait.setRange(1, MAX_WAIT_MIN)
        self.spin_wait.setSuffix(u' 분')
        top.addWidget(self.spin_wait)
        top.addStretch(1)
        root.addLayout(top)

        self.table = QtGui.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        for i in range(len(COLUMNS)):
            hh.setResizeMode(i, QtGui.QHeaderView.ResizeToContents)
        hh.setResizeMode(5, QtGui.QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.on_select)
        root.addWidget(self.table, 1)

        box = QtGui.QGroupBox()
        grid = QtGui.QGridLayout(box)
        self.ed = {}
        fields = [(u'이름', 'name', 0, 0, 1), (u'IP', 'ip', 0, 1, 1), (u'포트', 'port', 0, 2, 1),
                  (u'임계치 %', 'threshold', 0, 3, 1), (u'user', 'user', 2, 0, 1),
                  (u'pw', 'pw', 2, 1, 1), (u'path', 'path', 2, 2, 2)]
        for label, key, r, c, span in fields:
            grid.addWidget(QtGui.QLabel(label), r, c, 1, span)
            ed = QtGui.QLineEdit()
            self.ed[key] = ed
            grid.addWidget(ed, r + 1, c, 1, span)
        self.ed['pw'].setEchoMode(QtGui.QLineEdit.Password)
        self.ed['port'].setText(u'22')
        self.ed['threshold'].setText(u'85')
        self.ed['user'].setText(u'root')
        self.ed['path'].setPlaceholderText(u'/home/...')
        root.addWidget(box)

        btns = QtGui.QHBoxLayout()
        self.btn_add = self._button(u'추가', self.on_add)
        self.btn_edit = self._button(u'수정', self.on_edit)
        self.btn_del = self._button(u'삭제', self.on_delete, 'danger')
        self.btn_up = self._button(u'▲ 위로', lambda: self.on_move(-1))
        self.btn_down = self._button(u'▼ 아래로', lambda: self.on_move(1))
        for b in (self.btn_add, self.btn_edit, self.btn_del):
            btns.addWidget(b)
        btns.addSpacing(16)
        btns.addWidget(self.btn_up)
        btns.addWidget(self.btn_down)
        btns.addStretch(1)
        btns.addWidget(self._button(u'취소', self.reject))
        self.btn_save = self._button(u'저장 후 새로고침', self.on_save, 'primary')
        self.btn_save.setDefault(True)
        btns.addWidget(self.btn_save)
        root.addLayout(btns)
        self._update_buttons()

    def _button(self, text, slot, name=None):
        b = QtGui.QPushButton(text)
        b.setAutoDefault(False)
        if name:
            b.setObjectName(name)
        b.clicked.connect(slot)
        return b

    # ------------------------------------------------------------ 표
    def reload_table(self, select=None):
        targets = self.cfg.targets
        self.table.setRowCount(len(targets))
        for r, t in enumerate(targets):
            vals = [t.name, t.ip, unicode(t.port), t.user, PW_MASK, t.path, u'%d%%' % t.threshold]
            for c, v in enumerate(vals):
                item = QtGui.QTableWidgetItem(v)
                if c in (2, 6):
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(r, c, item)
        self.refresh_time_combo()
        if select is not None and 0 <= select < len(targets):
            self.table.selectRow(select)
        else:
            self.table.clearSelection()
        self._update_buttons()

    def refresh_time_combo(self):
        current = self.combo_time.currentText() or self.cfg.time_server
        names = self.cfg.server_names()
        self.combo_time.clear()
        self.combo_time.addItems(names)
        if current in names:
            self.combo_time.setCurrentIndex(names.index(current))
        elif names:
            self.combo_time.setCurrentIndex(0)

    def selected_index(self):
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _update_buttons(self):
        idx = self.selected_index()
        n = len(self.cfg.targets)
        self.btn_edit.setEnabled(idx >= 0)
        self.btn_del.setEnabled(idx >= 0)
        self.btn_up.setEnabled(idx > 0)
        self.btn_down.setEnabled(0 <= idx < n - 1)

    def on_select(self):
        idx = self.selected_index()
        if idx >= 0:
            t = self.cfg.targets[idx]
            for key, val in (('name', t.name), ('ip', t.ip), ('port', unicode(t.port)),
                             ('user', t.user), ('pw', t.pw), ('path', t.path),
                             ('threshold', unicode(t.threshold))):
                self.ed[key].setText(val)
        self._update_buttons()

    # ------------------------------------------------------------ 버튼
    def _warn(self, text):
        QtGui.QMessageBox.warning(self, APP_NAME, text)

    def _form_target(self):
        e = self.ed
        t, err = make_target(e['name'].text(), e['ip'].text(), e['port'].text(),
                             e['user'].text(), e['pw'].text(), e['path'].text(),
                             e['threshold'].text())
        if err:
            self._warn(err)
            return None
        return t

    def _check_conflicts(self, t, skip):
        """중복 path 확인, 같은 이름의 접속 정보 맞추기. 진행해도 되면 True."""
        for i, o in enumerate(self.cfg.targets):
            if i != skip and o.name == t.name and o.path == t.path:
                self._warn(u'%s 서버에 %s 가 이미 있습니다.' % (t.name, t.path))
                return False
        others = [o for i, o in enumerate(self.cfg.targets)
                  if i != skip and o.name == t.name and not o.same_login(t)]
        if others:
            ans = QtGui.QMessageBox.question(
                self, APP_NAME,
                u'같은 이름(%s)의 다른 줄과 접속 정보(IP/포트/user/pw)가 다릅니다.\n'
                u'같은 이름의 줄을 모두 이 접속 정보로 바꿀까요?' % t.name,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if ans != QtGui.QMessageBox.Yes:
                return False
            for o in others:
                o.ip, o.port, o.user, o.pw = t.ip, t.port, t.user, t.pw
        return True

    def on_add(self):
        t = self._form_target()
        if t is None or not self._check_conflicts(t, -1):
            return
        self.cfg.targets.append(t)
        self.reload_table(len(self.cfg.targets) - 1)

    def on_edit(self):
        idx = self.selected_index()
        if idx < 0:
            return
        t = self._form_target()
        if t is None or not self._check_conflicts(t, idx):
            return
        self.cfg.targets[idx] = t
        self.reload_table(idx)

    def on_delete(self):
        idx = self.selected_index()
        if idx < 0:
            return
        t = self.cfg.targets[idx]
        ans = QtGui.QMessageBox.question(
            self, APP_NAME, u'%s  %s\n이 줄을 삭제할까요?' % (t.name, t.path),
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if ans != QtGui.QMessageBox.Yes:
            return
        del self.cfg.targets[idx]
        self.reload_table(min(idx, len(self.cfg.targets) - 1))

    def on_move(self, delta):
        idx = self.selected_index()
        new = idx + delta
        if idx < 0 or not 0 <= new < len(self.cfg.targets):
            return
        ts = self.cfg.targets
        ts[idx], ts[new] = ts[new], ts[idx]
        self.reload_table(new)

    def on_save(self):
        self.cfg.time_server = self.combo_time.currentText()
        self.cfg.wait_min = self.spin_wait.value()
        self.accept()

    def result_config(self):
        return self.cfg
