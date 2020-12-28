#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
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


def main():
    servers = 8
    vsb_path = "./UC_5.1_SmartCity_CNIT/vsb_cnit_smart_city.yaml"
    #  vsb_path = "./UC_1.2_SmartTransport_A2T/ARES2T_VSB_V7.yaml"
    ctx_passt_path = "./common/ctx_delay/ctx_delay.yaml"
    ctx_connect_path = "./UC_5.1_SmartCity_CNIT/ctx_smartcity_traffic.yaml"
    with open(vsb_path) as vsb_file:
        vsb = yaml.safe_load(vsb_file)
        vsb_requests = [
            {
                "vsBlueprint": vsb,
                "nsds": [post("http://localhost:8086/nsd/generate", json=vsb).json()],
            }
        ]
        tracker_copy = vsb["atomicComponents"][0].copy()
        for i in range(1, servers + 1):
            tracker_copy["componentId"] = f"tracker_copy_{i}"
            tracker_copy["endPointIds"] = [
                f"cp_tracker_copy_{i}_data",
                f"cp_tracker_copy_{i}_mgmt",
            ]
            vsb["atomicComponents"].append(tracker_copy)
            vsb["endPoints"].append(
            )
            vsb_requests.append(
                {
                    "vsBlueprint": vsb,
                    "nsds": [
                        post("http://localhost:8086/nsd/generate", json=vsb).json()
                    ],
                }
            )
    with open(ctx_passt_path) as ctx_passt_file:
        ctx_passt = yaml.safe_load(ctx_passt_file)
        ctxb_passt_request = {
            "ctxBlueprint": ctx_passt,
            "nsds": [post("http://localhost:8086/nsd/generate", json=ctx_passt).json()],
            "translationRules": [],
        }
    with open(ctx_connect_path) as ctx_connect_file:
        ctx_connect = yaml.safe_load(ctx_connect_file)
        ctxb_connect_request = {
            "ctxBlueprint": ctx_connect,
            "nsds": [
                post("http://localhost:8086/nsd/generate", json=ctx_connect).json()
            ],
            "translationRules": [],
        }
    time.sleep(5)
    data_matrix = []
    max_connects = 101
    for i in range(0, servers):
        print(f"test with {i+1} trackers")
        print(
            f"count atomicComponents: {len(vsb_requests[i]['nsds'][0]['nsDf'][0]['vnfProfile'])}"
        )
        compose_req = {
            "vsbRequest": vsb_requests[i],
            "contexts": [{"ctxbRequest": ctxb_passt_request}],
        }
        times = []
        for j in range(0, max_connects):
            #  print(f"1 passthrough, {j} connect")
            start = time.perf_counter_ns()
            resp = post("http://localhost:8086/nsd/compose", json=compose_req)
            request_time = time.perf_counter_ns() - start
            resp.raise_for_status()
            #  print(resp.json())
            #  print(f"Request completed in {request_time/1000000} ms")
            times.append(request_time)
            compose_req["contexts"].append({"ctxbRequest": ctxb_connect_request})
        #  for t in times:
        #      print(t / 1000000)
        data_matrix.append(times)
    with open("comp_test_data.csv", mode="w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow([f"{i} connect" for i in range(0, max_connects)])
        writer.writerows(data_matrix)


if __name__ == "__main__":
    main()
