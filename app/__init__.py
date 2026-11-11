"""Local RUGD Analyze 0.2 browser application.

The package calls the 0.1 engine. It does not change scoring or the gate.
"""

from app.http_cleanup import install as _install_http_cleanup

APP_VERSION = "0.2-prototype"
_install_http_cleanup()
