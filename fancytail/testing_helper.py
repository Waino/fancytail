#!/usr/bin/env python
"""
A testing helper that randomly writes timestamps in multiple log files
"""
import click
import numpy as np
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple


@click.command()
@click.option("--path", "path_str", type=click.Path(exists=True, file_okay=False, dir_okay=True), default=".")
@click.option("-n", "--num-files", type=int, default=10, help="Number of files to create")
@click.option("-m", "--num-lines", type=int, default=100, help="Number of lines to write in total")
@click.option("--sleep", type=float, default=1.0, help="Sleep time between writes")
@click.option("--append", type=str, default="", help="String to append to each line")
@click.option(
    "-p", "--probabilities",
    type=float,
    multiple=True,
    default=[1.0],
    help="Probabilities for each log file to be selected"
)
def main(path_str: str, num_files: int, num_lines: int, probabilities: Tuple[float, ...], sleep: float, append: str):
    path = Path(path_str)
    files = [path / f"log_{i}.txt" for i in range(num_files)]
    if len(probabilities) > num_files:
        raise ValueError(f"Number of probabilities ({len(probabilities)}) must match number of files ({num_files})")
    elif len(probabilities) < num_files:
        if sum(probabilities) >= 1.0:
            raise ValueError(
                "If less probabilities are given than files, "
                f"the sum of probabilities ({sum(probabilities)}) must be less than 1.0"
            )
        remaining_prob = 1.0 - sum(probabilities)
        split_prob = remaining_prob / (num_files - len(probabilities))
        probabilities_list = list(probabilities)
        probabilities_list += [split_prob] * (num_files - len(probabilities))
        probabilities = tuple(probabilities_list)
    p = np.array(probabilities)
    p /= p.sum()
    print(f"Writing {num_lines} lines to {num_files} files with probabilities {p}")
    for _ in range(num_lines):
        i = np.random.choice(np.arange(num_files), p=p)
        file = files[i]
        with open(file, "a") as f:
            f.write(f"{datetime.now()} {append}\n")
        time.sleep(sleep)


if __name__ == "__main__":
    main()
