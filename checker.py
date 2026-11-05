# -*- coding: utf-8 -*-
"""
DiskWatcher - SSH 접속과 용량 체크

- 서버마다 백그라운드 스레드 하나 (daemon) 에서 SSH 로 df/du 실행
- 결과는 Qt 시그널로 화면(메인 스레드)에 전달
- 체크 회차 번호(gen)로 새로고침 이전의 늦은 결과는 버린다
"""
import re
import time
import socket
import random
import threading

from PyQt4 import QtCore

from common import shell_quote, to_unicode, exc_text
import logger

CONNECT_TIMEOUT = 10     # 접속 제한 시간(초)
SHORT_CMD_TIMEOUT = 60   # date, df 제한 시간(초). du 는 제한 없음
_date_re = re.compile(u'^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}$')


class CheckCancelled(Exception):
    pass


# ================================================================ 명령/파싱
def df_script(path):
    return u'LC_ALL=C df -P -k ' + shell_quote(path)


def du_script(path):
    # 숨김 항목(.[!.]*) 포함, path 바로 아래 항목의 크기(KB)
    return (u'cd ' + shell_quote(path) + u' || exit 99; '
            u'LC_ALL=C du -sk -- * .[!.]* 2>/dev/null; exit 0')


DATE_SCRIPT = u"date '+%Y-%m-%d %H:%M:%S'"


def parse_df(out):
    """df -P -k 출력 -> dict. 형식이 다르면 ValueError."""
    lines = [l for l in out.splitlines() if l.strip()]
    if len(lines) < 2:
        raise ValueError(u'df 결과가 비어 있습니다.')
    cols = u' '.join(lines[1:]).split()
    if len(cols) < 6:
        raise ValueError(u'df 결과 형식이 다릅니다: ' + lines[-1])
    total = int(cols[1])
    used = int(cols[2])
    avail = int(cols[3])
    pct_text = cols[4].rstrip(u'%')
    if pct_text.isdigit():
        pct = int(pct_text)
    else:
        base = used + avail
        pct = int(round(used * 100.0 / base)) if base else 0
    return {
        'ok': True,
        'device': cols[0],
        'total_kb': total,
        'used_kb': used,
        'avail_kb': avail,
        'pct': pct,
        'mount': u' '.join(cols[5:]),
    }


def parse_du(out):
    """du -sk 출력 -> [(kb, 이름), ...] 큰 순서."""
    items = []
    for line in out.splitlines():
        parts = line.split(u'\t', 1)
        if len(parts) != 2:
            continue
        try:
            items.append((int(parts[0]), parts[1]))
        except ValueError:
            pass
    items.sort(key=lambda x: (-x[0], x[1]))
    return items


def friendly_error(ex):
    """예외 -> 화면/로그에 보여줄 짧은 한글 메시지."""
    try:
        import paramiko
        if isinstance(ex, paramiko.AuthenticationException):
            return u'로그인 실패 (user/pw 확인)'
        if isinstance(ex, paramiko.SSHException):
            return u'SSH 오류: ' + exc_text(ex).split(u': ', 1)[-1]
    except ImportError:
        pass
    if isinstance(ex, socket.timeout):
        return u'접속 시간 초과'
    if isinstance(ex, socket.error):
        code = ex.args[0] if ex.args else None
        if code in (10061, 111):
            return u'연결 거부 (IP/포트 확인)'
        if code in (10060, 110):
            return u'접속 시간 초과'
        if code in (10051, 10065, 113, 101):
            return u'네트워크 도달 불가'
        if code in (11001, 11004, -2):
            return u'호스트 이름을 찾을 수 없음'
    if isinstance(ex, EOFError):
        return u'연결이 끊어졌습니다'
    return exc_text(ex)


# ================================================================ 접속 방식
class SshRunner(object):
    """paramiko 로 실제 서버에 접속."""

    def __init__(self, target):
        self.target = target
        self.client = None

    def connect(self):
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client = client
        t = self.target
        client.connect(t.ip, port=t.port, username=t.user, password=t.pw,
                       timeout=CONNECT_TIMEOUT, allow_agent=False,
                       look_for_keys=False)

    def run(self, script, timeout=None):
        """(종료코드, stdout, stderr) 모두 unicode."""
        cmd = u'/bin/sh -c ' + shell_quote(script)
        stdin, stdout, stderr = self.client.exec_command(cmd.encode('utf-8'),
                                                         timeout=timeout)
        stdin.close()
        out = stdout.read()
        err = stderr.read()
        code = stdout.channel.recv_exit_status()
        return code, out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace')

    def close(self):
        c = self.client
        if c is not None:
            try:
                c.close()
            except Exception:
                pass


class DemoRunner(object):
    """서버 없이 화면을 시험하기 위한 가짜 접속 (main.py --demo).
    서버 이름에 FAIL 이 들어 있으면 접속 실패로 흉내 낸다."""

    _usage = {}
    _lock = threading.Lock()
    _names = [u'mysql', u'backup', u'archive', u'tmp', u'logs', u'export',
              u'scripts', u'conf', u'home_bak', u'lost+found', u'.cache',
              u'한글폴더', u'data_2026']

    def __init__(self, target):
        self.target = target
        self.closed = False

    def _sleep(self, sec):
        end = time.time() + sec
        while time.time() < end:
            if self.closed:
                raise EOFError('closed')
            time.sleep(0.05)

    def connect(self):
        self._sleep(random.uniform(0.2, 0.8))
        if u'FAIL' in self.target.name.upper():
            self._sleep(1.0)
            raise socket.timeout('timed out')

    def _path_of(self, script):
        m = re.search(u"'((?:[^']|'\\\\'')*)'", script)
        return m.group(1).replace(u"'\\''", u"'") if m else u'/'

    def run(self, script, timeout=None):
        if script.startswith(u'date'):
            self._sleep(0.2)
            return 0, to_unicode(time.strftime('%Y-%m-%d %H:%M:%S')) + u'\n', u''
        path = self._path_of(script)
        seed = sum(ord(c) for c in path)
        total = [104857600, 524288000, 2147483648][seed % 3]   # 100G/500G/2T
        if u' df ' in script:
            self._sleep(random.uniform(0.2, 0.6))
            with self._lock:
                pct = self._usage.get(path, 35 + seed % 50)
                pct = max(5, min(99, pct + random.randint(-2, 4)))
                self._usage[path] = pct
            used = total * pct // 100
            out = (u'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
                   u'/dev/sd%s1 %d %d %d %d%% %s\n'
                   % (u'abcd'[seed % 4], total, used, total - used, pct,
                      path if seed % 2 else u'/'))
            return 0, out, u''
        # du
        self._sleep(random.uniform(1.0, 4.0))
        rnd = random.Random(seed)
        weights = [rnd.paretovariate(1.2) for n in self._names]
        with self._lock:
            used = total * self._usage.get(path, 50) // 100
        lines = []
        for name, wt in zip(self._names, weights):
            lines.append(u'%d\t%s' % (int(used * 0.9 * wt / sum(weights)), name))
        return 0, u'\n'.join(lines) + u'\n', u''

    def close(self):
        self.closed = True


# ================================================================ 작업 스레드
class _Bridge(QtCore.QObject):
    """백그라운드 스레드 -> 메인 스레드 전달용. 첫 인자는 항상 체크 회차(gen)."""
    server_state = QtCore.pyqtSignal(int, object, object, object)   # gen, 이름, 상태, 메시지
    partition = QtCore.pyqtSignal(int, int, object)                 # gen, index, 결과
    top = QtCore.pyqtSignal(int, int, object)                       # gen, index, 결과
    server_done = QtCore.pyqtSignal(int, object)                    # gen, 이름
    time_result = QtCore.pyqtSignal(int, object)                    # gen, 시각 or None


class _Job(object):
    def __init__(self, gen, bridge, demo):
        self.gen = gen
        self.bridge = bridge
        self.demo = demo
        self.cancelled = False
        self.runner = None
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

    def start(self):
        self.thread.start()

    def cancel(self):
        self.cancelled = True
        r = self.runner
        if r is not None:
            r.close()

    def open_runner(self, target):
        self.runner = DemoRunner(target) if self.demo else SshRunner(target)
        if self.cancelled:
            raise CheckCancelled()
        self.runner.connect()
        if self.cancelled:
            raise CheckCancelled()

    def check(self):
        if self.cancelled:
            raise CheckCancelled()

    def _main(self):
        try:
            self.run()
        except CheckCancelled:
            pass
        except Exception:
            if not self.cancelled:
                logger.log_error(u'체크 작업 오류')
        finally:
            if self.runner is not None:
                self.runner.close()
            try:
                self.finish()
            except Exception:
                pass

    def run(self):
        raise NotImplementedError

    def finish(self):
        pass


class ServerJob(_Job):
    """서버 하나: 접속 -> path 별 df -> path 별 du."""

    def __init__(self, gen, bridge, demo, name, items):
        _Job.__init__(self, gen, bridge, demo)
        self.name = name
        self.items = items          # [(index, Target), ...]

    def state(self, st, msg=u''):
        if not self.cancelled:
            self.bridge.server_state.emit(self.gen, self.name, st, msg)

    def run(self):
        self.state('checking')
        try:
            self.open_runner(self.items[0][1])
        except CheckCancelled:
            raise
        except Exception as ex:
            if self.cancelled:
                raise CheckCancelled()
            msg = friendly_error(ex)
            self.state('fail', msg)
            for idx, t in self.items:
                self.bridge.partition.emit(self.gen, idx, {
                    'ok': False, 'conn_fail': True, 'error': msg})
            return

        for idx, t in self.items:
            self.check()
            self.bridge.partition.emit(self.gen, idx, self.check_df(t))
        self.state('connected')
        for idx, t in self.items:
            self.check()
            self.bridge.top.emit(self.gen, idx, self.check_du(t))
        self.state('done')

    def check_df(self, t):
        try:
            code, out, err = self.runner.run(df_script(t.path), SHORT_CMD_TIMEOUT)
            self.check()
            if code != 0:
                first = (err.strip().splitlines() or [u'df 실패 (code %d)' % code])[0]
                return {'ok': False, 'conn_fail': False, 'error': first}
            return parse_df(out)
        except CheckCancelled:
            raise
        except Exception as ex:
            self.check()
            return {'ok': False, 'conn_fail': False, 'error': friendly_error(ex)}

    def check_du(self, t):
        start = time.time()
        try:
            code, out, err = self.runner.run(du_script(t.path), None)
            self.check()
            if code == 99:
                return {'ok': False, 'error': u'경로에 들어갈 수 없습니다: ' + t.path}
            items = parse_du(out)
            return {'ok': True, 'items': items[:10],
                    'total_kb': sum(x[0] for x in items),
                    'count': len(items), 'seconds': time.time() - start}
        except CheckCancelled:
            raise
        except Exception as ex:
            self.check()
            return {'ok': False, 'error': friendly_error(ex)}

    def finish(self):
        self.bridge.server_done.emit(self.gen, self.name)


class TimeJob(_Job):
    """시간 기준 서버에서 date 실행."""

    def __init__(self, gen, bridge, demo, target):
        _Job.__init__(self, gen, bridge, demo)
        self.target = target
        self.result = None

    def run(self):
        try:
            self.open_runner(self.target)
            code, out, err = self.runner.run(DATE_SCRIPT, SHORT_CMD_TIMEOUT)
            text = out.strip()
            if code == 0 and _date_re.match(text):
                self.result = text
        except CheckCancelled:
            raise
        except Exception:
            self.result = None

    def finish(self):
        self.bridge.time_result.emit(self.gen, self.result)


# ================================================================ 관리자
class CheckManager(QtCore.QObject):
    """체크 한 바퀴를 관리. 모든 시그널은 메인 스레드에서 나간다."""
    cycle_started = QtCore.pyqtSignal()
    server_state = QtCore.pyqtSignal(object, object, object)   # 이름, 상태, 메시지
    partition = QtCore.pyqtSignal(int, object)
    top = QtCore.pyqtSignal(int, object)
    cycle_finished = QtCore.pyqtSignal(object)                 # 서버 시각 or None

    def __init__(self, demo=False, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.demo = demo
        self.gen = 0
        self.running = False
        self.config = None
        self._jobs = []
        self._pending = set()
        b = self._bridge = _Bridge()
        b.server_state.connect(self._on_server_state)
        b.partition.connect(self._on_partition)
        b.top.connect(self._on_top)
        b.server_done.connect(self._on_server_done)
        b.time_result.connect(self._on_time)

    def start(self, config):
        """진행 중인 체크를 버리고 새로 시작."""
        self.cancel()
        self.gen += 1
        self.config = config
        self.running = True
        self.cycle_started.emit()
        groups = config.server_groups()
        self._pending = set(name for name, items in groups)
        if not groups:
            self._start_time_check()
            return
        for name, items in groups:
            job = ServerJob(self.gen, self._bridge, self.demo, name, items)
            self._jobs.append(job)
            job.start()

    def cancel(self):
        for job in self._jobs:
            job.cancel()
        self._jobs = []
        self._pending = set()
        self.running = False

    def _start_time_check(self):
        target = self.config.first_target(self.config.time_server)
        if target is None:
            self._finish(None)
            return
        job = TimeJob(self.gen, self._bridge, self.demo, target)
        self._jobs.append(job)
        job.start()

    def _finish(self, time_text):
        self._jobs = []
        self.running = False
        self.cycle_finished.emit(time_text)

    # -- bridge (gen 이 현재 회차일 때만 전달)
    def _on_server_state(self, gen, name, st, msg):
        if gen == self.gen and self.running:
            self.server_state.emit(name, st, msg)

    def _on_partition(self, gen, idx, res):
        if gen == self.gen and self.running:
            self.partition.emit(idx, res)

    def _on_top(self, gen, idx, res):
        if gen == self.gen and self.running:
            self.top.emit(idx, res)

    def _on_server_done(self, gen, name):
        if gen != self.gen or not self.running:
            return
        self._pending.discard(name)
        if not self._pending:
            self._start_time_check()

    def _on_time(self, gen, text):
        if gen == self.gen and self.running:
            self._finish(text)
