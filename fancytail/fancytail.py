"""fancytail."""
import click
import sys
import time
from datetime import datetime
from inotify_simple import INotify, flags   # type: ignore
from pathlib import Path
from pydantic import BaseModel
from rich.live import Live
from rich.table import Table
from typing import Optional, List, Dict, TextIO


class WatchedFile(BaseModel):
    path: Path
    last_modified: datetime
    last_lines: List[str] = []
    last_error: Optional[str] = None
    fobj: Optional[TextIO] = None


class DirectoryWatcher:
    def __init__(self, path: Path):
        self.path = path
        self.inotify = INotify()
        mask = flags.CLOSE_WRITE | flags.MODIFY | flags.MOVED_TO
        self.wd = self.inotify.add_watch(path, mask=mask)
        self.watched_files: Dict[Path, WatchedFile] = {}

    def watch(self):
        for event in self.inotify.read():
            wd, mask, cookie, name = event
            path = Path(name)
            if mask & flags.MOVED_TO:
                self.add_file(path)
                self.update_file(path)
            elif mask & flags.CLOSE_WRITE or mask & flags.MODIFY:
                self.update_file(path)

    def add_file(self, path: Path):
        if path in self.watched_files:
            return
        self.watched_files[path] = WatchedFile(path=path, last_modified=datetime.now())
        f = open(path, "r")
        f.seek(0, 2)  # Seek to the end of the file
        self.watched_files[path].fobj = f

    def update_file(self, path: Path):
        if path not in self.watched_files:
            self.add_file(path)
        wfile = self.watched_files[path]
        wfile.last_modified = datetime.now()
        assert wfile.fobj is not None
        # read to the new end of the file


class Funky:
    def __init__(self):
        self.contents = [
            ('foo',),
            ('foo', 'bar'),
            ('a', 'b', 'c'),
            ('shorter',),
            ('and', 'longer', 'again'),
        ]

    def render(self):
        if len(self.contents) > 1:
            self.contents.pop(0)
        t = Table.grid()
        t.add_column()
        for line in self.contents[0]:
            t.add_row(f"[red]{line}[/red]")
        return t


f = Funky()
with Live(f.render(), auto_refresh=False) as live:
    for _ in range(12):
        time.sleep(0.4)  # arbitrary delay
        live.update(f.render(), refresh=True)


@click.command()
def main(args=None):
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
