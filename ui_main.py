# -*- coding: utf-8 -*-
"""
DiskWatcher - 메인 창
"""
import os
import datetime

from PyQt4 import QtCore, QtGui

from common import (APP_NAME, CONFIG_FILE, DEMO_CONFIG_FILE, LOG_DIR,
                    SETTINGS_FILE, human_kb, to_unicode, exc_text)
from config import load_config, save_config, make_demo_config
from checker import CheckManager
from ui_config import ConfigDialog
import logger

# ---------------------------------------------------------------- 색
C_BG = u'#EEF1F4'
C_ALERT_BG = u'#B71C1C'
C_CARD = u'#FFFFFF'
C_BORDER = u'#D5DAE0'
C_HEAD = u'#F7F9FA'
C_TEXT = u'#1F2933'
C_SUB = u'#52606D'
C_BLUE = u'#1D5FBF'
C_RED = u'#C62828'
C_YELLOW = u'#FFD54F'
C_GREEN = u'#2E7D32'
C_GRAY = u'#9AA5B1'
C_FAIL_TEXT = u'#616E7C'
C_TRACK = u'#E4E7EB'
C_EXPANDED = u'#F2F6FC'
C_MINIBAR = u'#7FA3D9'

BASE_W = 1100.0
BASE_H = 960.0
BASE_PT = 10.0
MIN_SCALE = 0.8      # 8pt
MAX_SCALE = 2.0      # 20pt

FONT = u'"Malgun Gothic", "맑은 고딕", sans-serif'
MONO = u'Consolas, "Malgun Gothic", monospace'


def px(v, s):
    return max(1, int(round(v * s)))


def build_style(s):
    """배율 s 에 맞춘 전체 스타일시트."""
    d = {
        'font': FONT, 'mono': MONO,
        'base': px(BASE_PT, s), 'small': px(BASE_PT * 0.85, s),
        'sub': px(BASE_PT * 0.9, s), 'path': px(BASE_PT * 1.1, s),
        'pct': px(BASE_PT * 1.6, s), 'name': px(BASE_PT * 1.2, s),
        'big': px(BASE_PT * 1.5, s), 'banner': px(BASE_PT * 1.1, s),
        'btn_pad_v': px(7, s), 'btn_pad_h': px(14, s), 'radius': px(6, s),
        'dot_r': px(5, s), 'card_r': px(8, s), 'in_pad': px(4, s),
        'bg': C_BG, 'alert': C_ALERT_BG, 'card': C_CARD, 'border': C_BORDER,
        'head': C_HEAD, 'text': C_TEXT, 'subc': C_SUB, 'blue': C_BLUE,
        'red': C_RED, 'yellow': C_YELLOW, 'green': C_GREEN, 'gray': C_GRAY,
        'fail': C_FAIL_TEXT, 'expanded': C_EXPANDED,
        'yb': px(4, s),
    }
    return u"""
QWidget { font-family: %(font)s; font-size: %(base)spt; color: %(text)s; }
QMainWindow, QDialog { background: #FFFFFF; }

QPushButton { padding: %(btn_pad_v)spx %(btn_pad_h)spx; border: 1px solid #B8C1CB;
    border-radius: %(radius)spx; background: #FFFFFF; }
QPushButton:hover { background: #F0F3F6; }
QPushButton:pressed { background: #E4E7EB; }
QPushButton#primary { background: %(blue)s; border-color: %(blue)s; color: #FFFFFF; font-weight: bold; }
QPushButton#primary:hover { background: #174C99; }
QPushButton#danger { color: #B71C1C; border-color: %(red)s; }

QLineEdit, QComboBox, QSpinBox { padding: %(in_pad)spx; border: 1px solid #B8C1CB;
    border-radius: 4px; background: #FFFFFF; }
QTableWidget { border: 1px solid %(border)s; gridline-color: #EEF1F4;
    selection-background-color: %(blue)s; selection-color: #FFFFFF; }
QHeaderView::section { background: %(head)s; color: %(subc)s; font-weight: bold;
    border: none; border-bottom: 1px solid %(border)s; padding: %(in_pad)spx; }
QGroupBox { background: %(head)s; border: 1px solid #E4E7EB; border-radius: %(radius)spx; }

#toolbar { background: %(head)s; border-bottom: 1px solid %(border)s; }
#timeTitle, #countTitle { font-size: %(small)spt; color: %(subc)s; }
#timeValue { font-family: %(mono)s; font-size: %(big)spt; font-weight: bold; }
#timeValue[unknown="true"] { color: #B71C1C; }
#countValue { font-family: %(mono)s; font-size: %(big)spt; font-weight: bold; color: %(blue)s; }
#vline { background: %(border)s; }

#contentArea { background: %(bg)s; }
#contentArea[alert="true"] { background: %(alert)s; }
#cards { background: transparent; }
QScrollArea#scroll { background: transparent; border: none; }
#banner { background: #FFFFFF; color: #8E1A14; font-size: %(banner)spt; font-weight: bold;
    border-radius: %(radius)spx; padding: %(btn_pad_v)spx %(btn_pad_h)spx; }
#emptyLabel { color: %(subc)s; font-size: %(path)spt; }
#contentArea[alert="true"] #emptyLabel { color: #FFFFFF; }

#card { background: %(card)s; border: 1px solid %(border)s; border-radius: %(card_r)spx; }
#card[state="over"] { border: %(yb)spx solid %(yellow)s; }
#cardHead { background: %(head)s; border: none; border-bottom: 1px solid #E4E7EB;
    border-top-left-radius: %(card_r)spx; border-top-right-radius: %(card_r)spx; }
#card[state="over"] #cardHead { background: %(alert)s; }
#card[state="over"] #cardHead QLabel { color: #FFFFFF; }
#cardName { font-size: %(name)spt; font-weight: bold; }
#cardInfo { color: %(subc)s; }
#dot { border-radius: %(dot_r)spx; background: %(green)s; }
#card[state="checking"] #dot { background: %(blue)s; }
#card[state="over"] #dot { background: %(yellow)s; }
#card[state="fail"] #dot { background: %(gray)s; }
#card[state="fail"] QLabel { color: %(fail)s; }

#row { background: %(card)s; border: none; border-top: 1px solid #E4E7EB; }
#row[first="true"] { border-top: none; }
#row[expanded="true"] { background: %(expanded)s; }
#row:focus { background: #F7F9FA; }
#row[expanded="true"]:focus { background: #E8EFFA; }
#pathLabel { font-family: %(mono)s; font-size: %(path)spt; font-weight: bold; }
#subLabel { font-size: %(sub)spt; color: %(subc)s; }
#sizeLabel { font-size: %(sub)spt; color: %(subc)s; }
#pctLabel { font-size: %(pct)spt; font-weight: bold; }
#pctLabel[over="true"] { color: #B71C1C; }

#topBox { background: #FFFFFF; border: 1px solid #E4E7EB; border-radius: %(radius)spx; }
#topHead { font-size: %(small)spt; color: %(subc)s; }
#topName, #topSize { font-family: %(mono)s; }
#topRank, #topPct, #topInfo { color: %(subc)s; }
""" % d


def repolish(widget):
    """동적 속성을 바꾼 뒤 스타일을 다시 적용 (자식 포함)."""
    st = widget.style()
    for w in [widget] + widget.findChildren(QtGui.QWidget):
        st.unpolish(w)
        st.polish(w)
    widget.update()


def set_prop(widget, name, value):
    value = u'true' if value is True else (u'false' if value is False else value)
    if widget.property(name) == value:
        return False
    widget.setProperty(name, value)
    return True


# ================================================================ 막대
class UsageBar(QtGui.QWidget):
    """사용량 막대. threshold 가 있으면 그 위치에 세로선."""

    def __init__(self, parent=None, bar_h=14, color=C_BLUE, threshold=None):
        QtGui.QWidget.__init__(self, parent)
        self.pct = None
        self.threshold = threshold
        self.color = QtGui.QColor(color)
        self.base_bar_h = bar_h
        self.bar_h = bar_h
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self._update_height()

    def _update_height(self):
        self.setFixedHeight(self.bar_h + (self.bar_h // 2 + 2) * 2 if self.threshold else self.bar_h)

    def apply_scale(self, s):
        self.bar_h = px(self.base_bar_h, s)
        self._update_height()
        self.update()

    def set_value(self, pct, color=None, threshold=None):
        self.pct = pct
        if color is not None:
            self.color = QtGui.QColor(color)
        if threshold is not None:
            self.threshold = threshold
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        bh = self.bar_h
        y = (h - bh) / 2.0
        r = bh / 2.0
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(C_TRACK))
        p.drawRoundedRect(QtCore.QRectF(0, y, w, bh), r, r)
        if self.pct is not None and self.pct > 0:
            fw = max(bh, w * min(100, self.pct) / 100.0)
            p.setBrush(self.color)
            p.drawRoundedRect(QtCore.QRectF(0, y, fw, bh), r, r)
        if self.threshold:
            x = w * self.threshold / 100.0
            p.setBrush(QtGui.QColor(C_SUB))
            lw = max(2.0, bh / 7.0)
            p.drawRect(QtCore.QRectF(min(x, w - lw), 0, lw, h))
        p.end()


# ================================================================ 상위 10개
class TopBox(QtGui.QFrame):
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setObjectName('topBox')
        self.grid = QtGui.QGridLayout(self)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(4)
        self.bars = []
        self.scale = 1.0
        self.set_message(u'용량 계산 중...')

    def _clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.bars = []

    def _label(self, text, name, align=None):
        lb = QtGui.QLabel(text)
        lb.setObjectName(name)
        if align is not None:
            lb.setAlignment(align)
        return lb

    def set_message(self, text):
        self._clear()
        self.grid.addWidget(self._label(text, 'topInfo'), 0, 0)

    def set_result(self, res):
        if res is None:
            self.set_message(u'용량 계산 중...')
            return
        if not res.get('ok'):
            self.set_message(u'상위 10개를 가져오지 못했습니다: ' + res.get('error', u''))
            return
        items = res.get('items') or []
        if not items:
            self.set_message(u'(항목 없음)')
            return
        self._clear()
        right = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        g = self.grid
        for col, (text, al) in enumerate([(u'순위', None), (u'항목', None), (u'비율', None),
                                          (u'크기', right), (u'%', right)]):
            g.addWidget(self._label(text, 'topHead', al), 0, col)
        total = res.get('total_kb') or 0
        for i, (kb, name) in enumerate(items):
            pct = kb * 100.0 / total if total else 0.0
            row = i + 1
            g.addWidget(self._label(u'%d' % (i + 1), 'topRank'), row, 0)
            nm = self._label(name, 'topName')
            nm.setToolTip(name)
            g.addWidget(nm, row, 1)
            bar = UsageBar(bar_h=8, color=C_MINIBAR)
            bar.set_value(pct)
            bar.apply_scale(self.scale)
            self.bars.append(bar)
            g.addWidget(bar, row, 2)
            g.addWidget(self._label(human_kb(kb), 'topSize', right), row, 3)
            g.addWidget(self._label(u'%.1f%%' % pct, 'topPct', right), row, 4)
        info = u'전체 %d개 항목 · 합계 %s' % (res.get('count', len(items)), human_kb(total))
        if res.get('seconds') is not None:
            info += u' · %.1f초' % res['seconds']
        g.addWidget(self._label(info, 'topInfo'), len(items) + 1, 0, 1, 5)
        g.setColumnStretch(2, 1)

    def apply_scale(self, s):
        self.scale = s
        m = px(10, s)
        self.grid.setContentsMargins(m, px(6, s), m, px(6, s))
        self.grid.setHorizontalSpacing(px(12, s))
        self.grid.setColumnMinimumWidth(1, px(200, s))
        self.grid.setColumnMinimumWidth(3, px(80, s))
        for b in self.bars:
            b.apply_scale(s)


# ================================================================ 파티션 한 칸
class PartitionRow(QtGui.QFrame):
    changed = QtCore.pyqtSignal()

    def __init__(self, index, target, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setObjectName('row')
        self.index = index
        self.target = target
        self.result = None       # df 결과 dict
        self.top_result = None   # du 결과 dict
        self.expanded = False
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setToolTip(u'클릭하면 상위 10개를 펼치거나 접습니다')

        self.head = QtGui.QWidget()
        self.path_label = QtGui.QLabel()
        self.path_label.setObjectName('pathLabel')
        self.sub_label = QtGui.QLabel()
        self.sub_label.setObjectName('subLabel')
        left = QtGui.QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(self.path_label)
        left.addWidget(self.sub_label)
        self.left_box = QtGui.QWidget()
        self.left_box.setLayout(left)
        left.setContentsMargins(0, 0, 0, 0)

        self.bar = UsageBar(bar_h=14, threshold=target.threshold)

        self.size_label = QtGui.QLabel(u'-')
        self.size_label.setObjectName('sizeLabel')
        self.pct_label = QtGui.QLabel(u'-')
        self.pct_label.setObjectName('pctLabel')
        right = QtGui.QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.addStretch(1)
        right.addWidget(self.size_label, 0, QtCore.Qt.AlignBottom)
        right.addWidget(self.pct_label, 0, QtCore.Qt.AlignBottom)
        self.right_box = QtGui.QWidget()
        self.right_box.setLayout(right)

        hl = QtGui.QHBoxLayout(self.head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(self.left_box)
        hl.addWidget(self.bar, 1)
        hl.addWidget(self.right_box)
        self.head_layout = hl

        self.top_box = TopBox()
        self.top_box.setVisible(False)

        vl = QtGui.QVBoxLayout(self)
        vl.addWidget(self.head)
        vl.addWidget(self.top_box)
        self.main_layout = vl

        self.update_view()

    # -- 상태
    def is_ok(self):
        return bool(self.result and self.result.get('ok'))

    def is_over(self):
        return self.is_ok() and self.result['pct'] >= self.target.threshold

    # -- 이벤트
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # 펼친 목록 안을 클릭했을 때는 접지 않음
            if not self.top_box.isVisible() or event.pos().y() < self.top_box.geometry().top():
                self.toggle()
                return
        QtGui.QFrame.mousePressEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.toggle()
            return
        QtGui.QFrame.keyPressEvent(self, event)

    def toggle(self):
        self.set_expanded(not self.expanded)

    def set_expanded(self, on):
        self.expanded = bool(on)
        self.top_box.setVisible(self.expanded)
        if set_prop(self, 'expanded', self.expanded):
            repolish(self)
        self.update_view()

    # -- 결과
    def set_partition(self, res):
        self.result = res
        if res and not res.get('ok') and res.get('conn_fail'):
            self.top_result = None
        self.update_view()

    def set_top(self, res):
        self.top_result = res
        self.top_box.set_result(res)

    def update_view(self):
        t = self.target
        arrow = u'▾ ' if self.expanded else u'▸ '
        self.path_label.setText(arrow + t.path)
        self.path_label.setToolTip(t.path)
        r = self.result
        th = u'임계치 %d%%' % t.threshold
        over = False
        if r is None:
            self.sub_label.setText(u'확인 중 · ' + th)
            self.size_label.setText(u'')
            self.pct_label.setText(u'-')
            self.bar.set_value(None)
        elif not r.get('ok'):
            head = u'접속 실패' if r.get('conn_fail') else u'오류'
            self.sub_label.setText(u'%s: %s · %s' % (head, r.get('error', u''), th))
            self.size_label.setText(u'')
            self.pct_label.setText(u'-')
            self.bar.set_value(None)
            if r.get('conn_fail'):
                self.top_box.set_message(u'접속 실패로 가져오지 못했습니다.')
        else:
            over = r['pct'] >= t.threshold
            self.sub_label.setText(u'파티션 %s · %s · %s' % (r['mount'], r['device'], th))
            self.size_label.setText(u'%s / %s' % (human_kb(r['used_kb']), human_kb(r['total_kb'])))
            self.pct_label.setText(u'%d%%' % r['pct'])
            self.bar.set_value(r['pct'], C_RED if over else C_BLUE)
        if set_prop(self.pct_label, 'over', over):
            repolish(self.pct_label)

    def apply_scale(self, s):
        m = px(16, s)
        self.main_layout.setContentsMargins(m, px(9, s), m, px(9, s))
        self.main_layout.setSpacing(px(8, s))
        self.head_layout.setSpacing(px(20, s))
        self.left_box.setFixedWidth(px(280, s))
        self.right_box.setFixedWidth(px(200, s))
        self.right_box.layout().setSpacing(px(10, s))
        self.bar.apply_scale(s)
        self.top_box.apply_scale(s)


# ================================================================ 서버 카드
class ServerCard(QtGui.QFrame):
    def __init__(self, name, items, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setObjectName('card')
        self.name = name
        self.ip = items[0][1].ip
        self.job_state = 'checking'
        self.job_msg = u''

        self.head = QtGui.QFrame()
        self.head.setObjectName('cardHead')
        self.dot = QtGui.QLabel()
        self.dot.setObjectName('dot')
        self.name_label = QtGui.QLabel(name)
        self.name_label.setObjectName('cardName')
        self.info_label = QtGui.QLabel()
        self.info_label.setObjectName('cardInfo')
        hl = QtGui.QHBoxLayout(self.head)
        hl.addWidget(self.dot, 0, QtCore.Qt.AlignVCenter)
        hl.addWidget(self.name_label)
        hl.addWidget(self.info_label, 1)
        self.head_layout = hl

        vl = QtGui.QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)
        vl.addWidget(self.head)
        self.rows = []
        for i, (idx, t) in enumerate(items):
            row = PartitionRow(idx, t)
            set_prop(row, 'first', i == 0)
            self.rows.append(row)
            vl.addWidget(row)
        self.refresh_state()

    def set_job_state(self, st, msg=u''):
        self.job_state = st
        self.job_msg = msg
        self.refresh_state()

    def is_over(self):
        return any(r.is_over() for r in self.rows)

    def refresh_state(self):
        st = self.job_state
        if st == 'fail':
            state, text = 'fail', u'접속 실패 (%s)' % self.job_msg
        elif self.is_over():
            state, text = 'over', u'임계치 초과'
        elif st == 'checking':
            state, text = 'checking', u'체크 중...'
        elif st == 'connected':
            state, text = 'ok', u'정상 · 상위 10개 계산 중...'
        else:
            state, text = 'ok', u'정상'
        self.info_label.setText(u'%s · %s' % (self.ip, text))
        if set_prop(self, 'state', state):
            repolish(self)

    def apply_scale(self, s):
        d = px(10, s)
        self.dot.setFixedSize(d, d)
        self.head_layout.setContentsMargins(px(16, s), px(8, s), px(16, s), px(8, s))
        self.head_layout.setSpacing(px(10, s))
        for r in self.rows:
            r.apply_scale(s)


# ================================================================ 메인 창
class MainWindow(QtGui.QMainWindow):
    def __init__(self, demo=False):
        QtGui.QMainWindow.__init__(self)
        self.demo = demo
        self.config_path = DEMO_CONFIG_FILE if demo else CONFIG_FILE
        if demo:
            make_demo_config(self.config_path)
        self.settings = QtCore.QSettings(SETTINGS_FILE, QtCore.QSettings.IniFormat)
        self.config = None
        self.cards = []
        self.rows = {}           # index -> PartitionRow
        self.scale = None
        self.remaining = 0
        self.last_time_text = None
        self.log_date = datetime.date.today()

        self.manager = CheckManager(demo, self)
        self.manager.cycle_started.connect(self.on_cycle_started)
        self.manager.server_state.connect(self.on_server_state)
        self.manager.partition.connect(self.on_partition)
        self.manager.top.connect(self.on_top)
        self.manager.cycle_finished.connect(self.on_cycle_finished)

        self.countdown = QtCore.QTimer(self)
        self.countdown.setInterval(1000)
        self.countdown.timeout.connect(self.on_tick)

        self.scale_timer = QtCore.QTimer(self)
        self.scale_timer.setSingleShot(True)
        self.scale_timer.setInterval(80)
        self.scale_timer.timeout.connect(self.apply_scale)

        self._build_ui()
        self._restore_geometry()
        self.apply_scale(force=True)
        logger.cleanup_old_logs()
        QtCore.QTimer.singleShot(0, self.load_and_start)

    # ------------------------------------------------------------ 화면 구성
    def _build_ui(self):
        self._update_title(False)
        icon = self.style().standardIcon(QtGui.QStyle.SP_DriveHDIcon)
        self.setWindowIcon(icon)

        central = QtGui.QWidget()
        root = QtGui.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 도구 막대
        bar = QtGui.QFrame()
        bar.setObjectName('toolbar')
        tl = QtGui.QHBoxLayout(bar)
        self.toolbar_layout = tl
        st = self.style()
        self.btn_refresh = QtGui.QPushButton(st.standardIcon(QtGui.QStyle.SP_BrowserReload), u'새로고침')
        self.btn_refresh.setObjectName('primary')
        self.btn_refresh.setToolTip(u'진행 중인 체크를 멈추고 바로 다시 체크합니다 (F5)')
        self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_log = QtGui.QPushButton(st.standardIcon(QtGui.QStyle.SP_DirOpenIcon), u'로그 폴더')
        self.btn_log.clicked.connect(self.on_open_logs)
        self.btn_config = QtGui.QPushButton(st.standardIcon(QtGui.QStyle.SP_FileDialogDetailedView), u'서버 설정')
        self.btn_config.clicked.connect(self.on_settings)
        for b in (self.btn_refresh, self.btn_log, self.btn_config):
            b.setCursor(QtCore.Qt.PointingHandCursor)
            tl.addWidget(b)
        QtGui.QShortcut(QtGui.QKeySequence(u'F5'), self, self.on_refresh)
        tl.addStretch(1)

        self.time_title = QtGui.QLabel(u'마지막 갱신 (서버 시간)')
        self.time_title.setObjectName('timeTitle')
        self.time_value = QtGui.QLabel(u'-')
        self.time_value.setObjectName('timeValue')
        tl.addLayout(self._stack(self.time_title, self.time_value))
        vline = QtGui.QFrame()
        vline.setObjectName('vline')
        vline.setFixedWidth(1)
        self.vline = vline
        tl.addWidget(vline)
        self.count_title = QtGui.QLabel(u'다음 체크까지')
        self.count_title.setObjectName('countTitle')
        self.count_value = QtGui.QLabel(u'-')
        self.count_value.setObjectName('countValue')
        tl.addLayout(self._stack(self.count_title, self.count_value))
        root.addWidget(bar)

        # 내용 영역 (경고 시 배경 빨강)
        self.content = QtGui.QFrame()
        self.content.setObjectName('contentArea')
        set_prop(self.content, 'alert', False)
        cl = QtGui.QVBoxLayout(self.content)
        self.content_layout = cl
        self.banner = QtGui.QLabel()
        self.banner.setObjectName('banner')
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        cl.addWidget(self.banner)

        self.scroll = QtGui.QScrollArea()
        self.scroll.setObjectName('scroll')
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtGui.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        self.cards_widget = QtGui.QWidget()
        self.cards_widget.setObjectName('cards')
        self.cards_widget.setAutoFillBackground(False)
        self.cards_layout = QtGui.QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.cards_widget)
        cl.addWidget(self.scroll, 1)
        root.addWidget(self.content, 1)

        self.setCentralWidget(central)

    def _stack(self, top, bottom):
        v = QtGui.QVBoxLayout()
        v.setSpacing(0)
        v.addWidget(top, 0, QtCore.Qt.AlignRight)
        v.addWidget(bottom, 0, QtCore.Qt.AlignRight)
        return v

    def _update_title(self, alert):
        title = APP_NAME
        if self.demo:
            title += u' (데모)'
        if alert:
            title = u'[경고] ' + title
        self.setWindowTitle(title)

    def _rebuild_cards(self):
        keep = set()
        for r in self.rows.values():
            if r.expanded:
                keep.add((r.target.name, r.target.path))
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.cards = []
        self.rows = {}
        groups = self.config.server_groups()
        if not groups:
            lb = QtGui.QLabel(u'등록된 감시 대상이 없습니다.\n[서버 설정] 버튼을 눌러 서버를 추가하세요.')
            lb.setObjectName('emptyLabel')
            lb.setAlignment(QtCore.Qt.AlignCenter)
            self.cards_layout.addWidget(lb, 1)
        for name, items in groups:
            card = ServerCard(name, items)
            self.cards.append(card)
            for row in card.rows:
                self.rows[row.index] = row
                if (row.target.name, row.target.path) in keep:
                    row.set_expanded(True)
            self.cards_layout.addWidget(card)
        self.cards_layout.addStretch(1)
        if self.scale is not None:
            for c in self.cards:
                c.apply_scale(self.scale)
        self.time_title.setText(u'마지막 갱신 (서버 시간 · %s)' % (self.config.time_server or u'없음'))
        self.update_alert()

    # ------------------------------------------------------------ 크기/배율
    def _restore_geometry(self):
        geo = self.settings.value('geometry')
        if geo is not None and self.restoreGeometry(geo):
            return
        avail = QtGui.QApplication.desktop().availableGeometry(self)
        w = min(int(BASE_W), int(avail.width() * 0.9))
        h = min(int(BASE_H), int(avail.height() * 0.9))
        self.resize(w, h)
        self.move(avail.x() + (avail.width() - w) // 2, avail.y() + (avail.height() - h) // 2)

    def resizeEvent(self, event):
        QtGui.QMainWindow.resizeEvent(self, event)
        self.scale_timer.start()

    def apply_scale(self, force=False):
        s = min(self.width() / BASE_W, self.height() / BASE_H)
        s = max(MIN_SCALE, min(MAX_SCALE, s))
        s = round(s * 10) / 10.0
        if s == self.scale and not force:
            return
        self.scale = s
        self.setStyleSheet(build_style(s))
        m = px(16, s)
        self.toolbar_layout.setContentsMargins(m, px(10, s), m, px(10, s))
        self.toolbar_layout.setSpacing(px(8, s))
        self.vline.setFixedHeight(px(40, s))
        self.content_layout.setContentsMargins(m, m, m, m)
        self.content_layout.setSpacing(px(12, s))
        self.cards_layout.setSpacing(px(12, s))
        self.count_value.setMinimumWidth(px(110, s))
        for c in self.cards:
            c.apply_scale(s)

    # ------------------------------------------------------------ 동작
    def load_and_start(self):
        try:
            cfg, errors = load_config(self.config_path)
        except Exception as ex:
            logger.log_error(u'설정 파일 읽기 실패')
            QtGui.QMessageBox.critical(self, APP_NAME, u'설정 파일을 읽을 수 없습니다.\n' + exc_text(ex))
            from config import Config
            cfg, errors = Config(), []
        self.config = cfg
        self._rebuild_cards()
        self.start_check()
        if errors:
            for e in errors:
                logger.log_error(u'[설정] ' + e, with_trace=False)
            more = u'\n... 외 %d건' % (len(errors) - 10) if len(errors) > 10 else u''
            QtGui.QMessageBox.warning(
                self, APP_NAME,
                u'설정 파일에 문제가 있는 줄은 건너뛰었습니다.\n\n' + u'\n'.join(errors[:10]) + more)

    def start_check(self):
        if self.config is None:
            return
        self.countdown.stop()
        self.manager.start(self.config)

    def on_refresh(self):
        self.start_check()

    def on_open_logs(self):
        try:
            logger.ensure_log_dir()
            os.startfile(LOG_DIR)
        except Exception as ex:
            logger.log_error(u'로그 폴더 열기 실패')
            QtGui.QMessageBox.warning(self, APP_NAME, u'로그 폴더를 열 수 없습니다.\n' + exc_text(ex))

    def on_settings(self):
        dlg = ConfigDialog(self.config, os.path.basename(self.config_path), self)
        if dlg.exec_() != QtGui.QDialog.Accepted:
            return
        cfg = dlg.result_config()
        try:
            save_config(cfg, self.config_path)
        except Exception as ex:
            logger.log_error(u'설정 파일 저장 실패')
            QtGui.QMessageBox.critical(self, APP_NAME, u'설정 파일을 저장할 수 없습니다.\n' + exc_text(ex))
            return
        self.config = cfg
        self._rebuild_cards()
        self.start_check()

    # ------------------------------------------------------------ 체크 결과
    def on_cycle_started(self):
        self.count_value.setText(u'체크 중...')
        for c in self.cards:
            c.set_job_state('checking')

    def on_server_state(self, name, st, msg):
        for c in self.cards:
            if c.name == name:
                c.set_job_state(st, msg)
        if st == 'fail':
            self.update_alert()

    def on_partition(self, idx, res):
        row = self.rows.get(idx)
        if row is None:
            return
        row.set_partition(res)
        for c in self.cards:
            if row in c.rows:
                c.refresh_state()
        self.update_alert()

    def on_top(self, idx, res):
        row = self.rows.get(idx)
        if row is not None:
            row.set_top(res)

    def on_cycle_finished(self, time_text):
        self.last_time_text = time_text
        self.time_value.setText(time_text or u'Unknown')
        if set_prop(self.time_value, 'unknown', time_text is None):
            repolish(self.time_value)
        self.write_cycle_log(time_text)
        today = datetime.date.today()
        if today != self.log_date:
            self.log_date = today
            logger.cleanup_old_logs()
        self.remaining = self.config.wait_min * 60
        self._show_remaining()
        self.countdown.start()

    def on_tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.countdown.stop()
            self.start_check()
            return
        self._show_remaining()

    def _show_remaining(self):
        m, s = divmod(max(0, self.remaining), 60)
        if m >= 60:
            h, m = divmod(m, 60)
            self.count_value.setText(u'%d:%02d:%02d' % (h, m, s))
        else:
            self.count_value.setText(u'%02d:%02d' % (m, s))

    def update_alert(self):
        over = []
        for c in self.cards:
            for r in c.rows:
                if r.is_over():
                    over.append(r)
        alert = bool(over)
        if set_prop(self.content, 'alert', alert):
            repolish(self.content)
        self.banner.setVisible(alert)
        self._update_title(alert)
        if alert:
            parts = [u'%s %s %d%% (임계치 %d%%)' % (r.target.name, r.target.path,
                                                  r.result['pct'], r.target.threshold)
                     for r in over[:3]]
            text = u'임계치 초과 %d건 — ' % len(over) + u', '.join(parts)
            if len(over) > 3:
                text += u' 외 %d건' % (len(over) - 3)
            self.banner.setText(text)

    def write_cycle_log(self, time_text):
        lines = []
        for c in self.cards:
            for r in c.rows:
                t = r.target
                res = r.result
                if res is None:
                    tag, detail = u'[FAIL]', u'결과 없음'
                elif not res.get('ok'):
                    tag = u'[FAIL]'
                    head = u'접속 실패' if res.get('conn_fail') else u'오류'
                    detail = u'%s: %s' % (head, res.get('error', u''))
                else:
                    tag = u'[OVER]' if r.is_over() else u'[OK]'
                    size = u'%s/%s' % (human_kb(res['used_kb']), human_kb(res['total_kb']))
                    detail = u'%-15s %3d%%  (임계치 %d%%)' % (size, res['pct'], t.threshold)
                lines.append(u'%-6s %-10s %-24s %s' % (tag, t.name, t.path, detail))
        if time_text is None and self.config.targets:
            lines.append(u'[TIME] Unknown (시간 기준 서버: %s)' % (self.config.time_server or u'없음'))
        if lines:
            logger.write_disk_log(lines)

    # ------------------------------------------------------------ 종료
    def closeEvent(self, event):
        try:
            self.settings.setValue('geometry', self.saveGeometry())
            self.settings.sync()
        except Exception:
            logger.log_error(u'창 위치 저장 실패')
        self.countdown.stop()
        self.manager.cancel()
        event.accept()
