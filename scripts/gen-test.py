#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import statistics
import time
from os import scandir

import yaml
from requests import HTTPError, get, patch, post, put


def scantree(path):
    """Recursively yield DirEntry objects for given directory."""
    for entry in scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scantree(entry.path)  # see below for Python 2.x
        else:
            yield entry


def build_info(files):
    info = [["atomicComponents"], ["endPoints"], ["connectivityServices"]]
    for entry in files:
        with open(entry.path) as f:
            vsb = yaml.safe_load(f)
            try:
                info[0].append(len(vsb["atomicComponents"]))
            except KeyError:
                info[0].append(None)
            try:
                info[1].append(len(vsb["endPoints"]))
            except KeyError:
                info[1].append(None)
            try:
                info[2].append(len(vsb["connectivityServices"]))
            except KeyError:
                info[2].append(None)
    with open("gen_test_info.csv", mode="w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(["feature/file"] + [n.name for n in files])
        writer.writerows(info)


def main():
    files = []
    for entry in scantree("."):
        if (
            entry.is_file
            and "vsb" in entry.name.lower()
            and "nsd" not in entry.name.lower()
            and "_tr" not in entry.name.lower()
            and entry.name.endswith(("yml", "yaml"))
        ):
            files.append(entry)
    build_info(files)
    data_matrix = []
    for i in range(0, 100):
        row = []
        for entry in files:
            print(f"Processing {entry.path}")
            with open(entry.path) as f:
                vsb = yaml.safe_load(f)
                #  print(vsb)
                try:
                    start = time.perf_counter_ns()
                    resp = post("http://localhost:8086/nsd/generate", json=vsb)
                    request_time = time.perf_counter_ns() - start
                    resp.raise_for_status()
                    print(f"Request completed in {request_time/1000000} ms")
                    row.append(request_time)
                except HTTPError as e:
                    print(e)
                    row.append(None)
            print()
        data_matrix.append(row)
    mean_row = []
    for i in range(0, len(data_matrix[0])):
        column = [row[i] for row in data_matrix]
        try:
            mean_row.append(statistics.mean(c for c in column if c is not None))
        except statistics.StatisticsError:
            mean_row.append(None)
    print(f"mean_row: {mean_row}")
    mean = statistics.mean(s for s in mean_row if s is not None) / 1000000
    pstdev = statistics.pstdev(s for s in mean_row if s is not None) / 1000000
    print(f"mean: {mean:.3f} ms")
    print(f"standard deviation: {pstdev:.3f} ms")
    with open("gen_test_data.csv", mode="w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow([n.name for n in files])
        writer.writerows(data_matrix)


if __name__ == "__main__":
    main()
