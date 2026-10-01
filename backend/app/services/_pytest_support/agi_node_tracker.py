import os

_EVENTS_PATH = os.environ.get("AGI_NODE_EVENTS")


def _emit(kind, nodeid, extra=""):
    if not _EVENTS_PATH:
        return
    try:
        line = kind + "\t" + str(nodeid) + (("\t" + extra) if extra else "") + "\n"
        with open(_EVENTS_PATH, "a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        pass


def pytest_runtest_logstart(nodeid, location):
    _emit("START", nodeid)


def pytest_runtest_logreport(report):
    if report.when == "call":
        _emit("RESULT", report.nodeid, report.outcome)
    elif report.when == "setup" and report.outcome in ("failed", "skipped"):
        _emit("RESULT", report.nodeid, "error" if report.outcome == "failed" else "skipped")


def pytest_runtest_logfinish(nodeid, location):
    _emit("FINISH", nodeid)
