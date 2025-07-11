"""Test fancytail module"""

import pytest
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

from fancytail.fancytail import WatchedFile, divide_screen, filter_most_recent


def test_watched_file_update_line():
    """Test WatchedFile.update_line method"""
    wf = WatchedFile(path=Path("test.log"), total_size=5, max_errors=2)

    # Add normal lines
    wf.update_line("line1\n")
    wf.update_line("line2\n")
    assert list(wf.last_lines) == ["line1\n", "line2\n"]

    # Add error line
    wf.update_line("error occurred\n")
    assert list(wf.last_lines) == ["line1\n", "line2\n", "error occurred\n"]
    assert list(wf.last_errors) == []

    wf.update_line("line4\n")
    wf.update_line("line5\n")
    # error has not yet scrolled out, so it is sitll in the normal buffer
    assert list(wf.last_lines) == ["line2\n", "error occurred\n", "line4\n", "line5\n"]

    # Add more lines to trigger buffer management
    wf.update_line("line6\n")
    wf.update_line("line7\n")

    # There is a a header, a single error, and room for 5-1-1=3 lines in the normal buffer
    assert len(wf.last_lines) == 3
    assert "line1\n" not in wf.last_lines
    assert "error occurred\n" in wf.last_errors

    # errors also scroll out if new errors arrive
    wf.update_line("error 2 occurred\n")
    wf.update_line("line8\n")
    wf.update_line("line9\n")
    wf.update_line("line10\n")
    wf.update_line("line11\n")
    assert list(wf.last_errors) == ["error occurred\n", "error 2 occurred\n"]
    wf.update_line("error 3 occurred\n")
    wf.update_line("line12\n")
    wf.update_line("line13\n")
    wf.update_line("line14\n")
    wf.update_line("line15\n")
    assert list(wf.last_errors) == ["error 2 occurred\n", "error 3 occurred\n"]


def test_watched_file_set_size():
    """Test WatchedFile.set_size method"""
    wf = WatchedFile(path=Path("test.log"), total_size=3, max_errors=2)
    wf.update_line("line1\n")
    wf.update_line("line2\n")
    wf.update_line("line3\n")
    wf.update_line("line4\n")
    wf.update_line("line5\n")
    # one header, two lines
    assert list(wf.last_lines) == ["line4\n", "line5\n"]
    wf.set_size(total_size=5, max_errors=2, width=80)
    assert list(wf.last_lines) == ["line4\n", "line5\n"]
    wf.update_line("line6\n")
    # one header, three lines 1+3 < 5
    assert list(wf.last_lines) == ["line4\n", "line5\n", "line6\n"]
    wf.update_line("line7\n")
    # one header, four lines 1+4 == 5
    assert list(wf.last_lines) == ["line4\n", "line5\n", "line6\n", "line7\n"]
    wf.update_line("line8\n")
    # one header, four lines 1+4 == 5
    assert list(wf.last_lines) == ["line5\n", "line6\n", "line7\n", "line8\n"]
    # add error
    wf.update_line("error occurred\n")
    wf.update_line("line9\n")
    wf.update_line("line10\n")
    wf.set_size(total_size=3, max_errors=2, width=80)
    # render to trigger truncation
    wf.render(MagicMock())
    # one header, one error, one line
    assert list(wf.last_errors) == ["error occurred\n"]
    assert list(wf.last_lines) == ["line10\n"]


def test_watched_file_no_truncate_if_hidden():
    """Test that WatchedFile does not truncate if the file is not shown"""
    wf = WatchedFile(path=Path("test.log"), total_size=5, max_errors=2)
    wf.update_line("line1\n")
    wf.update_line("line2\n")
    wf.update_line("line3\n")
    wf.update_line("line4\n")
    # one header, 4 lines
    assert list(wf.last_lines) == ["line1\n", "line2\n", "line3\n", "line4\n"]
    wf.update_line("line5\n")
    # one header, 4 lines
    assert list(wf.last_lines) == ["line2\n", "line3\n", "line4\n", "line5\n"]
    wf.set_size(total_size=0, max_errors=2, width=80)
    wf.update_line("line6\n")
    wf.update_line("line7\n")
    # no truncation
    assert list(wf.last_lines) == ["line2\n", "line3\n", "line4\n", "line5\n", "line6\n", "line7\n"]


@pytest.mark.parametrize(
    "filename, input, expected, total_size, max_errors, width",
    [
        (
            "test.log",
            ["line1", "line2", "line3"],
            ["[bold cyan]==> test.log <==[/bold cyan]", "line1", "line2", "line3"],
            5, 1, 80,
        ),
        (
            "foobar.log",
            ["line1", "line2", "line3"],
            ["[bold cyan]==> foobar.log <==[/bold cyan]", "line2", "line3"],
            3, 1, 80,
        ),
        (
            "quux.log",
            ["line1", "line2", "line3"],
            ["[[bold cyan]quux.log[/bold cyan]] line2", "[[bold cyan]quux.log[/bold cyan]] line3"],
            2, 1, 80,
        ),
        (
            "looooooooongfilename.log",
            ["line1", "line2", "line3"],
            [
                "[[bold cyan]oooooongfilename.log[/bold cyan]] line2",
                "[[bold cyan]oooooongfilename.log[/bold cyan]] line3",
            ],
            2, 1, 80,
        ),
        (
            "errorlast.log",
            ["line1", "line2", "line3", "error occurred"],
            ["[bold cyan]==> errorlast.log <==[/bold cyan]", "line1", "line2", "line3", "[red]error occurred[/red]"],
            5, 1, 80,
        ),
        (
            "errorfirst.log",
            ["error occurred", "line2", "line3", "line4"],
            ["[bold cyan]==> errorfirst.log <==[/bold cyan]", "[red]error occurred[/red]", "line3", "line4"],
            4, 1, 80,
        ),
        (
            "truncate_long_line.log",
            ["line1", "line2", "line3", "line4", "123456789ABCDEFGH", "line6"],
            ["[bold cyan]==> truncate_long_line.log <==[/bold cyan]", "line2", "line3", "line4", "123456789ABC", "line6"],
            6, 1, 12,
        ),
    ]
)
def test_watched_file_render(
    filename: str,
    input: List[str],
    expected: List[str],
    total_size: int,
    max_errors: int,
    width: int,
):
    """Test WatchedFile.render method"""
    wf = WatchedFile(path=Path(filename), total_size=total_size, max_errors=max_errors, width=width)
    for line in input:
        wf.update_line(line)
    table = MagicMock()
    wf.render(table)
    for call, exp in zip(table.add_row.call_args_list, expected):
        assert call[0][0] == exp
    assert table.add_row.call_count == len(expected)


@pytest.mark.parametrize(
    "n_files, screen_size, expected",
    [
        (0, 10, []),
        (1, 10, [10]),
        (2, 10, [5, 5]),
        (3, 10, [4, 3, 3]),
        (4, 10, [3, 3, 2, 2]),
        (5, 10, [2, 2, 2, 2, 2]),
        (10, 10, [1] * 10),
        (11, 10, [1] * 10),
        (1, 7, [7]),
        (2, 7, [4, 3]),
        (3, 7, [3, 2, 2]),
        (4, 7, [2, 2, 2, 1]),
        (5, 7, [2, 2, 1, 1, 1]),
        (6, 7, [2, 1, 1, 1, 1, 1]),
        (7, 7, [1] * 7),
    ]
)
def test_divide_screen(n_files, screen_size, expected):
    """Test divide_screen function"""
    result = divide_screen(n_files, screen_size)
    assert result == expected
    if n_files > 0:
        assert sum(result) == screen_size


def test_filter_most_recent():
    """Test filter_most_recent function"""
    watched_files = OrderedDict(
        [
            (Path("a"), WatchedFile(path=Path("a"), last_modified=datetime.now())),
            (Path("b"), WatchedFile(path=Path("c"), last_modified=datetime.now() - timedelta(seconds=2))),
            (Path("c"), WatchedFile(path=Path("d"), last_modified=datetime.now() - timedelta(seconds=3))),
            (Path("d"), WatchedFile(path=Path("b"), last_modified=datetime.now() - timedelta(seconds=1))),
        ]
    )
    assert filter_most_recent(watched_files, 2) == [Path("a"), Path("d")]
    assert filter_most_recent(watched_files, 3) == [Path("a"), Path("b"), Path("d")]
    assert filter_most_recent(watched_files, 4) == [Path("a"), Path("b"), Path("c"), Path("d")]
    assert filter_most_recent(watched_files, 5) == [Path("a"), Path("b"), Path("c"), Path("d")]
