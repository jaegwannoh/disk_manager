# -*- coding: utf-8 -*-
"""
DiskWatcher - 설정 파일(servers.txt) 읽기/저장

형식 (UTF-8)
    # 주석
    TIME_SERVER=WEB1
    WAIT_MIN=5
    이름|IP|포트|user|pw|path|임계치%
"""
import os
import codecs

from common import CONFIG_FILE, to_unicode

DEFAULT_WAIT_MIN = 5
MAX_WAIT_MIN = 1440
SEP = u'|'

HEADER = u"""# DiskWatcher 설정 파일 (UTF-8)
# '#' 으로 시작하는 줄은 주석입니다.
#
# TIME_SERVER : 갱신 시각을 가져올 서버 이름
# WAIT_MIN    : 체크가 끝난 뒤 다음 체크까지 대기 시간(분)
#
# 감시 대상은 path 하나당 한 줄로 씁니다.
# 이름이 같은 줄은 화면에서 한 서버로 묶이고, 접속 정보는 첫 줄 값을 씁니다.
# 이름|IP|포트|user|pw|path|임계치%
# 예) WEB1|10.0.0.11|22|root|1234|/home|85
"""


class Target(object):
    """감시 대상 한 줄 (서버 + path)."""

    def __init__(self, name, ip, port, user, pw, path, threshold):
        self.name = name
        self.ip = ip
        self.port = port
        self.user = user
        self.pw = pw
        self.path = path
        self.threshold = threshold

    def copy(self):
        return Target(self.name, self.ip, self.port, self.user, self.pw,
                      self.path, self.threshold)

    def same_login(self, other):
        return (self.ip, self.port, self.user, self.pw) == \
               (other.ip, other.port, other.user, other.pw)

    def to_line(self):
        return SEP.join([self.name, self.ip, unicode(self.port), self.user,
                         self.pw, self.path, unicode(self.threshold)])


class Config(object):
    def __init__(self):
        self.time_server = u''
        self.wait_min = DEFAULT_WAIT_MIN
        self.targets = []

    def copy(self):
        c = Config()
        c.time_server = self.time_server
        c.wait_min = self.wait_min
        c.targets = [t.copy() for t in self.targets]
        return c

    def server_names(self):
        names = []
        for t in self.targets:
            if t.name not in names:
                names.append(t.name)
        return names

    def server_groups(self):
        """[(이름, [(index, target), ...]), ...] 파일 순서대로."""
        groups = []
        lookup = {}
        for i, t in enumerate(self.targets):
            if t.name not in lookup:
                lookup[t.name] = []
                groups.append((t.name, lookup[t.name]))
            lookup[t.name].append((i, t))
        return groups

    def first_target(self, name):
        for t in self.targets:
            if t.name == name:
                return t
        return None


# ---------------------------------------------------------------- 검사
def make_target(name, ip, port, user, pw, path, threshold):
    """입력값을 검사해서 (Target, None) 또는 (None, 오류메시지) 를 돌려준다."""
    vals = [to_unicode(v).strip() for v in (name, ip, port, user, pw, path, threshold)]
    name, ip, port, user, pw, path, threshold = vals
    for label, v in ((u'이름', name), (u'IP', ip), (u'user', user), (u'pw', pw),
                     (u'path', path)):
        if SEP in v or u'\n' in v or u'\r' in v:
            return None, u"%s 에 '|' 문자나 줄바꿈은 쓸 수 없습니다." % label
    if not name:
        return None, u'이름을 입력하세요.'
    if u'=' in name:
        return None, u"이름에 '=' 문자는 쓸 수 없습니다."
    if not ip:
        return None, u'IP를 입력하세요.'
    try:
        port_n = int(port)
        if not 1 <= port_n <= 65535:
            raise ValueError
    except ValueError:
        return None, u'포트는 1~65535 숫자여야 합니다.'
    if not user:
        return None, u'user를 입력하세요.'
    if not path.startswith(u'/'):
        return None, u"path는 '/' 로 시작해야 합니다."
    if len(path) > 1:
        path = path.rstrip(u'/') or u'/'
    try:
        th = int(threshold.rstrip(u'%'))
        if not 1 <= th <= 100:
            raise ValueError
    except ValueError:
        return None, u'임계치는 1~100 숫자여야 합니다.'
    return Target(name, ip, port_n, user, pw, path, th), None


# ---------------------------------------------------------------- 읽기/저장
def _read_text(path):
    fp = open(path, 'rb')
    try:
        data = fp.read()
    finally:
        fp.close()
    if data.startswith(codecs.BOM_UTF8):
        data = data[len(codecs.BOM_UTF8):]
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('mbcs', 'replace')


def load_config(path=CONFIG_FILE):
    """(Config, 오류메시지 리스트). 파일이 없으면 빈 설정 파일을 만든다."""
    cfg = Config()
    errors = []
    if not os.path.isfile(path):
        try:
            save_config(cfg, path)
        except Exception as ex:
            errors.append(u'설정 파일을 만들 수 없습니다: %s' % to_unicode(ex))
        return cfg, errors

    text = _read_text(path)
    seen = set()
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(u'#'):
            continue
        if SEP not in line and u'=' in line:
            key, val = [x.strip() for x in line.split(u'=', 1)]
            key = key.upper()
            if key == u'TIME_SERVER':
                cfg.time_server = val
            elif key == u'WAIT_MIN':
                try:
                    n = int(val)
                    if not 1 <= n <= MAX_WAIT_MIN:
                        raise ValueError
                    cfg.wait_min = n
                except ValueError:
                    errors.append(u'%d번째 줄: WAIT_MIN 은 1~%d 숫자여야 합니다.' % (no, MAX_WAIT_MIN))
            else:
                errors.append(u'%d번째 줄: 알 수 없는 설정 %s' % (no, key))
            continue
        cols = line.split(SEP)
        if len(cols) != 7:
            errors.append(u'%d번째 줄: 항목이 7개가 아닙니다 (%d개).' % (no, len(cols)))
            continue
        t, err = make_target(*cols)
        if err:
            errors.append(u'%d번째 줄: %s' % (no, err))
            continue
        if (t.name, t.path) in seen:
            errors.append(u'%d번째 줄: %s %s 가 중복되어 건너뜁니다.' % (no, t.name, t.path))
            continue
        seen.add((t.name, t.path))
        cfg.targets.append(t)

    if not cfg.time_server and cfg.targets:
        cfg.time_server = cfg.targets[0].name
    return cfg, errors


def save_config(cfg, path=CONFIG_FILE):
    lines = [HEADER, u'TIME_SERVER=%s' % cfg.time_server,
             u'WAIT_MIN=%d' % cfg.wait_min, u'']
    for t in cfg.targets:
        lines.append(t.to_line())
    text = u'\r\n'.join(l.replace(u'\n', u'\r\n') for l in lines) + u'\r\n'
    tmp = path + u'.tmp'
    fp = codecs.open(tmp, 'w', encoding='utf-8')
    try:
        fp.write(text)
    finally:
        fp.close()
    if os.path.isfile(path):
        os.remove(path)
    os.rename(tmp, path)


DEMO_LINES = [
    u'WEB1|10.0.0.11|22|root|1234|/home/nojae/good|85',
    u'WEB1|10.0.0.11|22|root|1234|/var/log|90',
    u'DB1|10.0.0.21|22|root|1234|/data|80',
    u'BATCH_FAIL|10.0.0.31|22|root|1234|/batch/output|85',
    u'APP1|10.0.0.41|22|root|1234|/opt/app|85',
    u'APP2|10.0.0.42|2222|admin|1234|/opt/app|85',
    u'APP2|10.0.0.42|2222|admin|1234|/home|70',
]


def make_demo_config(path):
    """데모 모드용 설정 파일이 없으면 예시 서버로 만든다."""
    if os.path.isfile(path):
        return
    cfg = Config()
    cfg.time_server = u'WEB1'
    for line in DEMO_LINES:
        t, err = make_target(*line.split(SEP))
        cfg.targets.append(t)
    save_config(cfg, path)
