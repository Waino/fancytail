"""fancytail."""
import click
import sys
import re
from collections import deque, OrderedDict
from datetime import datetime
from inotify_simple import INotify, flags   # type: ignore
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from rich.console import Console
from rich.live import Live
from rich.table import Table
from typing import Optional, TextIO, Tuple, List

ERROR_RE = re.compile(r"\b(error|fail|exception)\b", re.IGNORECASE)


class WatchedFile(BaseModel):
    """A file being watched."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    path: Path
    last_modified: Optional[datetime] = None
    last_lines: deque[str] = deque()
    last_errors: deque[str] = deque()
    fobj: Optional[TextIO] = None
    total_size: int = 10
    max_errors: int = 1

    def set_size(self, total_size: int, max_errors: int) -> None:
        self.total_size = total_size
        self.max_errors = max_errors

    def update_line(self, line: str) -> None:
        """
        Add a line to the files buffer.
        Then remove old lines if the buffer is too long.
        For each removed line, check if it is an error to be kept in the error buffer.
        """
        self.last_lines.append(line)
        usable_size = self.total_size - len(self.last_errors)
        use_header = self.total_size > 2
        if use_header:
            usable_size -= 1
        if usable_size < 1:
            return
        while len(self.last_lines) > usable_size:
            popped = self.last_lines.popleft()
            if ERROR_RE.search(popped):
                self.last_errors.append(popped)
                while len(self.last_errors) > self.max_errors:
                    self.last_errors.popleft()

    def _get_size(self) -> Tuple[bool, int, int]:
        size_left = self.total_size
        use_header = self.total_size > 2
        if use_header:
            size_left -= 1
        normal_lines = size_left - min(len(self.last_errors), size_left)
        size_left -= normal_lines
        error_lines = min(len(self.last_errors), size_left)
        return use_header, normal_lines, error_lines

    def render(self, table: Table) -> None:
        """Render the file's content into a table"""
        use_header, normal_lines, error_lines = self._get_size()
        if use_header:
            table.add_row(f"[bold cyan]==> {self.path.name} <==[/bold cyan]")
            prefix = ""
        else:
            prefix = f"[[bold cyan]{self.path.name[-10:]}[/bold cyan]] "

        while len(self.last_errors) > error_lines:
            self.last_errors.popleft()
        while len(self.last_lines) > normal_lines:
            self.last_lines.popleft()

        for line in self.last_errors:
            line = line.rstrip("\n")
            table.add_row(f"{prefix}[red]{line}[/red]")
        for line in self.last_lines:
            line = line.rstrip("\n")
            if ERROR_RE.search(line):
                table.add_row(f"{prefix}[red]{line}[/red]")
            else:
                table.add_row(f"{prefix}{line}")


class DirectoryWatcher:
    def __init__(self, path: Path, n: int = 3) -> None:
        self.path = path
        self.n = n
        self.inotify = INotify()
        mask = flags.CLOSE_WRITE | flags.MODIFY | flags.MOVED_TO
        self.wd = self.inotify.add_watch(path, mask=mask)
        self.watched_files: OrderedDict[Path, WatchedFile] = OrderedDict()
        for file in sorted(path.glob("*")):
            if file.is_file():
                self.add_file(file)

    def watch(self) -> None:
        for event in self.inotify.read(timeout=1000):
            wd, mask, cookie, name = event
            path = Path(name)
            if not path.is_file():
                continue
            if mask & flags.MOVED_TO:
                self.add_file(path)
                self.update_file(path)
            elif mask & flags.CLOSE_WRITE or mask & flags.MODIFY:
                self.update_file(path)

    def add_file(self, path: Path) -> None:
        if path in self.watched_files:
            return
        f = open(path, "r")
        last_lines = deque(f.readlines()[-self.n:])
        self.watched_files[path] = WatchedFile(
            path=path,
            last_modified=datetime.fromtimestamp(path.stat().st_mtime),
            last_lines=last_lines,
        )
        self.watched_files[path].fobj = f

    def update_file(self, path: Path) -> None:
        if path not in self.watched_files:
            self.add_file(path)
        wfile = self.watched_files[path]
        wfile.last_modified = datetime.now()
        assert wfile.fobj is not None
        # read to the new end of the file
        while True:
            line = wfile.fobj.readline()
            if len(line) == 0:
                break
            wfile.update_line(line)

    def divide_screen(self, screen_size: int) -> List[int]:
        """Divide the screen among the watched files"""
        n_files = len(self.watched_files)
        if n_files == 0:
            return []
        if n_files > screen_size:
            return [1] * screen_size
        lines_per_file = screen_size // n_files
        extra_lines = screen_size % n_files
        sizes = [lines_per_file] * n_files
        for i in range(extra_lines):
            sizes[i] += 1
        return sizes

    def filter_most_recent(self, n: int) -> List[Path]:
        """Return the n most recently modified files, but do not change their ordering"""
        candidate_files = {key: val for key, val in self.watched_files.items() if val.last_modified is not None}
        if n >= len(candidate_files):
            return list(candidate_files.keys())
        sorted_files = sorted(candidate_files.items(), key=lambda x: x[1].last_modified, reverse=True)  # type: ignore
        selected = {x[0] for x in sorted_files[:n]}
        filtered = [x for x in candidate_files.keys() if x in selected]
        return filtered


@click.command()
@click.argument("path", type=Path, default=".")
@click.option("--max-errors", type=int, default=1, help="Maximum number of errors to keep in view", show_default=True)
@click.option("-n", type=int, default=3, help="Number of original lines to show", show_default=True)
def main(path: Path, max_errors: int = 1, n: int = 3) -> None:
    watcher = DirectoryWatcher(path, n=n)
    console = Console()
    with Live(auto_refresh=False) as live:
        while True:
            watcher.watch()
            table = Table.grid()
            table.add_column()
            sizes = watcher.divide_screen(console.height)
            if len(sizes) == 0:
                table.add_row("[grey30](No files to watch)[/grey30]")
            for (path, size) in zip(watcher.filter_most_recent(len(sizes)), sizes):
                wfile = watcher.watched_files[path]
                wfile.set_size(size, max_errors)
                wfile.render(table)
            live.update(table, refresh=True)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
