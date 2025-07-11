Fancytail is a small tool for watching multiple log files in a directory.
It is similar in spirit to running `tail -f` on multiple files,
but provides a more modern experience.

It uses a `rich` live-updating table to display the log lines.
The whole screen is used to display the tail of each log file.
Each file gets an equal share of the screen, and the table is resized as the window is resized.
If too many files are present to fit the screen, the least recently updated files are rotated out of view.
New files are watched automatically as they appear.
Normally, precede each files content lines with a header giving the filename.
However, if the number of files is so large that there is two or less lines per file, the headers are suppressed and the file name is instead prepended to each line.
Error lines are highlighted in red and the last error line is remembered even after rotating out of view.


# Code style

- This project uses `mypy` for type checking: add type annotations to all function arguments and return values.
- Write testable code. If it is possible to extract logic into a pure function, prefer refactoring to use the pure function instead of   mixing logic with side effects.

# Libraries

## click

Use `click` to create the command line interface.

## rich

Use `rich` to produce good-looking live-updating output with color and formatting.

## inotify-simple

Use `inotify-simple` to listen to filesystem writes in the log directory to watch.

## pydantic

Use `pydantic` version 2 to represent data.
