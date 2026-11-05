# -*- coding: utf-8 -*-
"""
DiskWatcher - 공통 함수와 경로

한글 처리 원칙
- 프로그램 내부 문자열은 모두 unicode 로 다룬다.
- 바이트 문자열이 들어오면 to_unicode() 로 바꾼다.
"""
import os
import sys


def to_unicode(s, encodings=('utf-8', 'mbcs')):
    """str/bytes/기타 객체를 오류 없이 unicode 로 바꾼다."""
    if isinstance(s, unicode):
        return s
    if s is None:
        return u''
    if not isinstance(s, str):
        try:
            return unicode(s)
        except Exception:
            try:
                s = str(s)
            except Exception:
                return u'?'
    for enc in encodings:
        try:
            return s.decode(enc)
        except Exception:
            pass
    return s.decode('utf-8', 'replace')


def _fs_path(p):
    """파일 시스템 경로(bytes)를 unicode 로. 윈도우 경로는 mbcs 우선."""
    if isinstance(p, unicode):
        return p
    enc = sys.getfilesystemencoding() or 'mbcs'
    return to_unicode(p, (enc, 'mbcs', 'utf-8'))


# ---------------------------------------------------------------- 경로
BASE_DIR = os.path.dirname(os.path.abspath(_fs_path(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, u'servers.txt')
DEMO_CONFIG_FILE = os.path.join(BASE_DIR, u'demo_servers.txt')
LOG_DIR = os.path.join(BASE_DIR, u'logs')
SETTINGS_FILE = os.path.join(BASE_DIR, u'window.ini')

APP_NAME = u'DiskWatcher'


# ---------------------------------------------------------------- 표시용
def human_kb(kb):
    """KB 숫자 -> '310.0G' 형식 (1024 단위)."""
    try:
        size = float(kb)
    except (TypeError, ValueError):
        return u'-'
    for unit in (u'K', u'M', u'G', u'T', u'P'):
        if size < 1024.0 or unit == u'P':
            return u'%.1f%s' % (size, unit)
        size = size / 1024.0


def shell_quote(text):
    """리눅스 셸용 작은따옴표 처리: abc'd -> 'abc'\\''d'"""
    return u"'" + to_unicode(text).replace(u"'", u"'\\''") + u"'"


def exc_text(ex):
    """예외를 'Name: 메시지' 형태의 unicode 로."""
    name = to_unicode(type(ex).__name__)
    msg = u''
    try:
        msg = unicode(ex)
    except Exception:
        try:
            msg = to_unicode(str(ex))
        except Exception:
            try:
                msg = u' '.join(to_unicode(a) for a in ex.args)
            except Exception:
                msg = u''
    msg = msg.strip()
    if msg:
        return u'%s: %s' % (name, msg)
    return name
