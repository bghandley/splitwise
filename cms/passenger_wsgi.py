import sys, os
INTERP = os.path.expanduser("/home/YOUR_CPANEL_USERNAME/public_html/venv/bin/python3")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

from app import app as application
