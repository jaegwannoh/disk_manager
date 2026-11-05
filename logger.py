# -*- coding: utf-8 -*-
"""
DiskWatcher - 로그 기록

- logs\\disk_YYYY-MM-DD.log : 용량 체크 결과 (하루 한 파일, UTF-8)
- logs\\error.log           : 프로그램 내부 오류
- 30일이 지난 disk_*.log 는 자동 삭제
"""
import os
import re
import sys
import codecs
import datetime
import threading
import traceback

from common import LOG_DIR, to_unicode

KEEP_DAYS = 30
ERROR_LOG = u'error.log'
ERROR_LOG_OLD = u'error.old.log'
ERROR_LOG_MAX = 1024 * 1024   # 1MB 넘으면 error.old.log 로 바꿈

_lock = threading.RLock()
_name_re = re.compile(u'^disk_(\\d{4}-\\d{2}-\\d{2})\\.log$')


def ensure_log_dir():
    if not os.path.isdir(LOG_DIR):
        os.makedirs(LOG_DIR)


def now_text():
    return to_unicode(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


def _append(filename, text):
    """logs 폴더의 파일 끝에 text(unicode)를 덧붙인다. 줄바꿈은 \\r\\n (메모장 호환)."""
    text = text.replace(u'\r\n', u'\n').replace(u'\n', u'\r\n')
    with _lock:
        ensure_log_dir()
        fp = codecs.open(os.path.join(LOG_DIR, filename), 'a', encoding='utf-8')
        try:
            fp.write(text)
        finally:
            fp.close()


def disk_log_path(date_text=None):
    if date_text is None:
        date_text = now_text()[:10]
    return os.path.join(LOG_DIR, u'disk_%s.log' % date_text)


def write_disk_log(lines):
    """체크 결과 여러 줄을 오늘 날짜 로그에 기록. lines: unicode 리스트 (시각 없이)."""
    stamp = now_text()
    text = u''.join(u'%s %s\n' % (stamp, to_unicode(line)) for line in lines)
    try:
        _append(os.path.basename(disk_log_path(stamp[:10])), text)
    except Exception:
        log_error(u'disk 로그 기록 실패')


def log_error(msg, with_trace=True):
    """error.log 에 기록. 예외 처리 중이면 traceback 도 함께 남긴다. 절대 예외를 내지 않는다."""
    try:
        text = u'%s %s\n' % (now_text(), to_unicode(msg))
        if with_trace and sys.exc_info()[0] is not None:
            text += to_unicode(traceback.format_exc())
        with _lock:
            ensure_log_dir()
            path = os.path.join(LOG_DIR, ERROR_LOG)
            try:
                if os.path.isfile(path) and os.path.getsize(path) > ERROR_LOG_MAX:
                    old = os.path.join(LOG_DIR, ERROR_LOG_OLD)
                    if os.path.isfile(old):
                        os.remove(old)
                    os.rename(path, old)
            except Exception:
                pass
            _append(ERROR_LOG, text)
    except Exception:
        pass


def cleanup_old_logs(days=KEEP_DAYS):
    """파일 이름의 날짜가 days 일보다 오래된 disk_*.log 삭제. 삭제한 개수를 돌려준다."""
    count = 0
    try:
        ensure_log_dir()
        today = datetime.date.today()
        for name in os.listdir(LOG_DIR):
            m = _name_re.match(name)
            if not m:
                continue
            try:
                day = datetime.datetime.strptime(m.group(1), '%Y-%m-%d').date()
            except ValueError:
                continue
            if (today - day).days > days:
                try:
                    os.remove(os.path.join(LOG_DIR, name))
                    count += 1
                except Exception:
                    log_error(u'오래된 로그 삭제 실패: ' + name)
    except Exception:
        log_error(u'로그 정리 실패')
    return count
