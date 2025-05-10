import logging
import os
import threading
import time
import sys

class ProjectFilter(logging.Filter):
    """Allow only records whose source file is under `project_root`."""
    def __init__(self, project_root: str):
        super().__init__()
        self.root = os.path.abspath(project_root)

    def filter(self, record: logging.LogRecord) -> bool:
        return os.path.abspath(record.pathname).startswith(self.root)

class NotProjectFilter(logging.Filter):
    """Allow only records whose source file is *not* under `project_root`."""
    def __init__(self, project_root: str):
        super().__init__()
        self.root = os.path.abspath(project_root)

    def filter(self, record: logging.LogRecord) -> bool:
        return not os.path.abspath(record.pathname).startswith(self.root)

def setup_logging(
    app_name: str,
    project_root: str = None,
    project_console_level: int = logging.INFO,
    other_console_level:   int = logging.WARNING,
) -> str:
    """
    - **FileHandler** at DEBUG for *only* your code.
    - **StreamHandler** at INFO+ for *only* your code.
    - **StreamHandler** at WARNING+ for everything else.
    """
    if not project_root:
        project_root = os.path.dirname(os.path.abspath(__file__))
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # let handlers do the filtering

    # 1) File handler for *your* code
    tid     = threading.get_ident()
    ts      = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    logfile = os.path.join("logs", f"{app_name}_{ts}_{tid}.log")
    os.makedirs(os.path.dirname(logfile), exist_ok=True)

    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    #fh.setFormatter(logging.Formatter(
    #    "%(asctime)s — %(levelname)s — %(name)s — %(threadName)s — %(message)s"
    #))
    fh.setFormatter(logging.Formatter(
        "%(asctime)s — %(levelname)s — %(message)s"
    ))
    fh.addFilter(ProjectFilter(project_root))
    root.addHandler(fh)

    # 2) Console for *your* code (INFO+)
    ch_proj = logging.StreamHandler(sys.stdout)
    ch_proj.setLevel(project_console_level)
    ch_proj.setFormatter(logging.Formatter(
        "%(asctime)s — %(levelname)s — %(name)s — %(message)s"
    ))
    ch_proj.addFilter(ProjectFilter(project_root))
    root.addHandler(ch_proj)

    # 3) Console for *other* code (WARNING+)
    ch_other = logging.StreamHandler(sys.stdout)
    ch_other.setLevel(other_console_level)
    ch_other.setFormatter(logging.Formatter(
        "%(asctime)s — %(levelname)s — %(name)s — %(message)s"
    ))
    ch_other.addFilter(NotProjectFilter(project_root))
    root.addHandler(ch_other)

    return logfile
