# -*- coding: utf-8 -*-
"""
DiskWatcher - SSH connection test (Python 2.7)

Usage (cmd):
    C:\\anaconda2\\python.exe ssh_test.py IP USER PASSWORD [PATH] [PORT]

Example:
    C:\\anaconda2\\python.exe ssh_test.py 10.0.0.11 root 1234 /home 22

Console output is ASCII only (safe on English Windows cmd).
Full result (with Korean file names) is saved to ssh_test_result.txt (UTF-8).
paramiko debug log is saved to ssh_test_paramiko.log.
"""
import sys
import os
import time
import codecs
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = os.path.join(BASE_DIR, 'ssh_test_result.txt')
PARAMIKO_LOG = os.path.join(BASE_DIR, 'ssh_test_paramiko.log')

_result_fp = None


def to_unicode(s):
    """Convert any str/bytes to unicode without raising."""
    if isinstance(s, unicode):
        return s
    if s is None:
        return u''
    for enc in ('utf-8', 'mbcs'):
        try:
            return s.decode(enc)
        except Exception:
            pass
    return s.decode('utf-8', 'replace')


def out(msg=u''):
    """Write a line to console (ASCII safe) and to the result file (UTF-8)."""
    msg = to_unicode(msg)
    try:
        sys.stdout.write(msg.encode('ascii', 'replace') + '\n')
        sys.stdout.flush()
    except Exception:
        pass
    if _result_fp is not None:
        _result_fp.write(msg + u'\n')
        _result_fp.flush()


def shell_quote(path):
    """Quote a path for the remote shell: abc'd -> 'abc'\\''d'"""
    return u"'" + path.replace(u"'", u"'\\''") + u"'"


def human_kb(kb):
    """KB number -> 310.0G style text (1024 units)."""
    size = float(kb)
    for unit in (u'K', u'M', u'G', u'T', u'P'):
        if size < 1024.0 or unit == u'P':
            return u'%.1f%s' % (size, unit)
        size = size / 1024.0


def run(client, cmd, timeout=None):
    """Run a command, return (exit_code, stdout_unicode, stderr_unicode, seconds)."""
    start = time.time()
    stdin, stdout, stderr = client.exec_command(cmd.encode('utf-8'), timeout=timeout)
    o = stdout.read()
    e = stderr.read()
    code = stdout.channel.recv_exit_status()
    sec = time.time() - start
    return code, o.decode('utf-8', 'replace'), e.decode('utf-8', 'replace'), sec


def print_versions():
    out(u'== Versions ==')
    out(u'python   : ' + to_unicode(sys.version.split()[0]))
    try:
        import paramiko
        out(u'paramiko : ' + to_unicode(paramiko.__version__))
    except ImportError:
        out(u'paramiko : NOT INSTALLED')
        return False
    for name in ('Crypto', 'cryptography', 'ecdsa'):
        try:
            mod = __import__(name)
            out(u'%-9s: %s' % (name, to_unicode(getattr(mod, '__version__', '?'))))
        except ImportError:
            out(u'%-9s: -' % name)
    return True


def print_transport_info(client):
    t = client.get_transport()
    out(u'== SSH session ==')
    out(u'server   : ' + to_unicode(getattr(t, 'remote_version', '?')))
    out(u'cipher   : ' + to_unicode(getattr(t, 'remote_cipher', '?')))
    out(u'mac      : ' + to_unicode(getattr(t, 'remote_mac', '?')))
    sec = t.get_security_options()
    out(u'client kex list : ' + u', '.join(to_unicode(x) for x in sec.kex))
    out(u'client ciphers  : ' + u', '.join(to_unicode(x) for x in sec.ciphers))


def test_date(client):
    out(u'== 1. Server time ==')
    code, o, e, sec = run(client, u"date '+%Y-%m-%d %H:%M:%S'", timeout=30)
    out(u'result   : ' + o.strip())
    if e.strip():
        out(u'stderr   : ' + e.strip())
    out(u'time     : %.2f sec' % sec)


def test_df(client, path):
    out(u'== 2. Partition (df) : ' + path + u' ==')
    code, o, e, sec = run(client, u'df -P -k ' + shell_quote(path), timeout=60)
    out(o.rstrip())
    if e.strip():
        out(u'stderr   : ' + e.strip())
    lines = [x for x in o.splitlines() if x.strip()]
    if code == 0 and len(lines) >= 2:
        # df -P can wrap only if device name has spaces; take last line
        cols = lines[-1].split()
        if len(cols) >= 6:
            device, total, used, avail, pct = cols[0], cols[1], cols[2], cols[3], cols[4]
            mount = u' '.join(cols[5:])
            out(u'-> device=%s mount=%s used=%s / total=%s  use=%s' % (
                device, mount, human_kb(used), human_kb(total), pct))
    out(u'time     : %.2f sec' % sec)


def test_du(client, path):
    out(u'== 3. Top 10 (du) : ' + path + u' ==')
    cmd = u'cd ' + shell_quote(path) + u' && du -sk -- * .[!.]* 2>/dev/null'
    code, o, e, sec = run(client, cmd)   # no timeout, same as real program
    items = []
    for line in o.splitlines():
        parts = line.split(u'\t', 1)
        if len(parts) != 2:
            continue
        try:
            items.append((int(parts[0]), parts[1]))
        except ValueError:
            pass
    total = sum(x[0] for x in items)
    items.sort(reverse=True)
    out(u'items    : %d   total: %s' % (len(items), human_kb(total)))
    for i, (kb, name) in enumerate(items[:10]):
        pct = (kb * 100.0 / total) if total else 0.0
        out(u'%2d. %-30s %10s %5.1f%%' % (i + 1, name, human_kb(kb), pct))
    out(u'time     : %.2f sec' % sec)


def main():
    global _result_fp
    args = [to_unicode(a) for a in sys.argv[1:]]
    if len(args) < 3:
        out(__doc__)
        return 1
    ip, user, pw = args[0], args[1], args[2]
    path = args[3] if len(args) > 3 else u'/'
    port = int(args[4]) if len(args) > 4 else 22

    _result_fp = codecs.open(RESULT_FILE, 'w', encoding='utf-8')
    out(u'DiskWatcher SSH test  ' + to_unicode(time.strftime('%Y-%m-%d %H:%M:%S')))
    out(u'target   : %s@%s:%d  path=%s' % (user, ip, port, path))
    out()

    if not print_versions():
        out(u'')
        out(u'[FAIL] paramiko is not installed in this Python.')
        return 2

    import paramiko
    paramiko.util.log_to_file(PARAMIKO_LOG)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    out()
    out(u'== Connect ==')
    start = time.time()
    try:
        client.connect(ip, port=port, username=user, password=pw, timeout=10,
                       allow_agent=False, look_for_keys=False)
    except Exception as ex:
        out(u'[FAIL] connect error: %s: %s' % (to_unicode(type(ex).__name__), to_unicode(str(ex))))
        out(to_unicode(traceback.format_exc()))
        out(u'Hint: "Incompatible ssh peer" / "no acceptable kex" = paramiko too old for this server.')
        out(u'      Send me ssh_test_result.txt and ssh_test_paramiko.log.')
        return 3
    out(u'[OK] connected in %.2f sec' % (time.time() - start))
    print_transport_info(client)

    steps = ((test_date, ()), (test_df, (path,)), (test_du, (path,)))
    for func, fargs in steps:
        out()
        try:
            func(client, *fargs)
        except Exception as ex:
            out(u'[FAIL] %s: %s' % (to_unicode(type(ex).__name__), to_unicode(str(ex))))
            out(to_unicode(traceback.format_exc()))

    client.close()
    out()
    out(u'Done. Result saved: ' + to_unicode(RESULT_FILE))
    return 0


if __name__ == '__main__':
    code = 1
    try:
        code = main()
    finally:
        if _result_fp is not None:
            _result_fp.close()
    sys.exit(code)
