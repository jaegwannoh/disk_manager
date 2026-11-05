# -*- coding: utf-8 -*-
"""
DiskWatcher - 리눅스 서버 디스크 용량 감시

실행:  pythonw.exe main.py           (실제 서버)
       pythonw.exe main.py --demo    (서버 없이 화면 시험, demo_servers.txt 사용)
"""
import sys
import os
import warnings

# paramiko/cryptography 의 Python 2 지원 종료 경고 등 숨김
warnings.filterwarnings('ignore')

# PyQt4 를 QString/QVariant 없이 파이썬 unicode 로 쓰기 (PyQt4 import 전에 해야 함)
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)


class _NullWriter(object):
    """pythonw 에는 콘솔이 없어서 print/stderr 출력이 오류가 날 수 있으므로 버린다."""
    def write(self, text):
        pass

    def flush(self):
        pass


def _install_guards():
    import logger
    if os.path.basename(sys.executable).lower().startswith('pythonw'):
        sys.stdout = _NullWriter()
        sys.stderr = _NullWriter()

    def hook(exc_type, exc, tb):
        import traceback
        from common import to_unicode
        text = u''.join(to_unicode(x) for x in traceback.format_exception(exc_type, exc, tb))
        logger.log_error(u'처리되지 않은 오류\n' + text, with_trace=False)

    sys.excepthook = hook


def main():
    _install_guards()
    from PyQt4 import QtGui
    from ui_main import MainWindow

    demo = '--demo' in sys.argv
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName(u'DiskWatcher')
    app.setFont(QtGui.QFont(u'Malgun Gothic', 10))
    win = MainWindow(demo=demo)
    win.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
