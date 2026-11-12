"""Close HTTP sockets when a response is discarded.

urllib can close the file descriptor through a makefile and leave the socket
object itself open. A finalizer closes that socket object without replacing
the response, so a chained read() still works.
"""

from __future__ import annotations

import urllib.error
import urllib.request
import weakref

_INSTALLED = False


def _socket_of(response):
    current = response
    for _ in range(4):
        if current is None:
            return None
        fp = getattr(current, "fp", None)
        raw = getattr(fp, "raw", None)
        sock = getattr(raw, "_sock", None)
        if sock is None:
            sock = getattr(fp, "_sock", None)
        if sock is not None:
            return sock
        current = fp
    return None


def _finalize(response) -> None:
    """Close the body, then the socket, when the response is discarded.

    A bound close() on the response itself would keep that response alive.
    The makefile close is kept instead. Closing the socket while a makefile
    still exists can leave the file descriptor open until a later collection,
    which is the unclosed-socket warning.
    """
    closers = []
    nested = getattr(response, "fp", None)
    if nested is not None and nested is not response and hasattr(nested, "close"):
        closers.append(nested.close)
    sock = _socket_of(response)
    if sock is not None:
        closers.append(sock.close)
    if not closers:
        return

    def release() -> None:
        for closer in closers:
            try:
                closer()
            except Exception:
                continue

    weakref.finalize(response, release)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    urlopen = urllib.request.urlopen
    opener_open = urllib.request.OpenerDirector.open

    def closing_urlopen(*args, **kwargs):
        try:
            response = urlopen(*args, **kwargs)
        except urllib.error.HTTPError as exc:
            _finalize(exc)
            raise
        _finalize(response)
        return response

    def closing_open(self, *args, **kwargs):
        try:
            response = opener_open(self, *args, **kwargs)
        except urllib.error.HTTPError as exc:
            _finalize(exc)
            raise
        _finalize(response)
        return response

    urllib.request.urlopen = closing_urlopen
    urllib.request.OpenerDirector.open = closing_open  # type: ignore[method-assign]
    _INSTALLED = True
