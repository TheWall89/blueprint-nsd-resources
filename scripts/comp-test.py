#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import time
import json
import math
import sys
from copy import deepcopy
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
    max_connects = 101
    vsb_path = "./UC_5.1_SmartCity_CNIT/vsb_cnit_smart_city.yaml"
    #  vsb_path = "./UC_1.2_SmartTransport_A2T/ARES2T_VSB_V7.yaml"
    ctx_passt_path = "./common/ctx_delay/ctx_delay.yaml"
    ctx_connect_path = "./UC_5.1_SmartCity_CNIT/ctx_smartcity_traffic.yaml"
    with open(vsb_path) as vsb_file:
        vsb = yaml.safe_load(vsb_file)
        print(f"# acs: {len(vsb['atomicComponents'])}")
        vsb_requests = [
            {
                "vsBlueprint": vsb,
                "nsds": [post("http://localhost:8086/nsd/generate", json=vsb).json()],
            }
        ]
        vsb_copy = deepcopy(vsb)
        for i in range(1, servers + 1):
            vsb_copy = deepcopy(vsb_copy)
            tracker = [
                ac
                for ac in vsb_copy["atomicComponents"]
                if ac["componentId"] == "mobility_tracker"
            ][0]
            tracker_copy = deepcopy(tracker)
            data = [
                vl
                for vl in vsb_copy["connectivityServices"]
                if vl["name"] == "vl_smart_city_data"
            ][0]
            mgmt = [
                vl
                for vl in vsb_copy["connectivityServices"]
                if vl["name"] == "vl_smart_city_mgmt"
            ][0]
            tracker_copy["componentId"] = f"tracker_copy_{i}"
            tracker_copy["endPointsIds"] = [
                f"cp_tracker_copy_{i}_data",
                f"cp_tracker_copy_{i}_mgmt",
            ]
            vsb_copy["atomicComponents"].append(tracker_copy)
            vsb_copy["endPoints"].append(
                {
                    "endPointId": tracker_copy["endPointsIds"][0],
                    "external": False,
                    "management": False,
                    "ranConnection": False,
                }
            )
            vsb_copy["endPoints"].append(
                {
                    "endPointId": tracker_copy["endPointsIds"][1],
                    "external": True,
                    "management": True,
                    "ranConnection": False,
                }
            )
            data["endPointIds"].append(tracker_copy["endPointsIds"][0])
            mgmt["endPointIds"].append(tracker_copy["endPointsIds"][1])
            #  if i ==3:
            #      print(json.dumps(vsb))
            #      sys.exit(1)
            print(f"# acs: {len(vsb_copy['atomicComponents'])}")
            vsb_requests.append(
                {
                    "vsBlueprint": vsb_copy,
                    "nsds": [
                        post("http://localhost:8086/nsd/generate", json=vsb_copy).json()
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
        ctxb_connect_requests = []
        for i in range(0, max_connects):
            ctx_connect_copy = deepcopy(ctx_connect)
            ctx_connect_copy["blueprintId"] += f"_{i}"
            ctx_connect_copy["atomicComponents"][0]["componentId"] += f"_{i}"
            for i in range(0, len(ctx_connect_copy["atomicComponents"][0]["endPointsIds"])):
                ctx_connect_copy["atomicComponents"][0]["endPointsIds"][i] += f"_{i}"
            #  print(json.dumps(ctx_connect_copy["atomicComponents"][0]["endPointsIds"],indent=2))
            for ep in ctx_connect_copy["endPoints"]:
                ep["endPointId"] += f"_{i}"
            for cs in ctx_connect_copy["connectivityServices"]:
                for i in range(0, len(cs["endPointIds"])):
                    cs["endPointIds"][i] += f"_{i}"
            #  print(json.dumps(ctx_connect_copy, indent=2))
            ctxb_connect_requests.append(
                {
                    "ctxBlueprint": ctx_connect_copy,
                    "nsds": [
                        post(
                            "http://localhost:8086/nsd/generate", json=ctx_connect_copy
                        ).json()
                    ],
                    "translationRules": [],
                }
            )
    #  time.sleep(5)
    vsb_lines_effort = []
    nsd_effort = []
    nsd_lines = []
    times_matrix = []
    for i in range(0, servers):
        print(f"test with {i+1} tracker")
        print(
            f"count atomicComponents: {len(vsb_requests[i]['nsds'][0]['nsDf'][0]['vnfProfile'])}"
        )
        vsb_lines = len(yaml.safe_dump(vsb_requests[i]["vsBlueprint"]).splitlines())
        vsb_lines_nsd = len(yaml.safe_dump(vsb_requests[i]["nsds"]).splitlines())
        #  print(f"i: {i}")
        print(f"vsb_lines: {vsb_lines}")
        vsb_pms = math.pow(0.85 * 3.2 * (vsb_lines / 1000), 1.05)
        vsb_lines_effort.append([vsb_lines, vsb_pms, vsb_lines_nsd])
        compose_req = {
            "vsbRequest": vsb_requests[i],
            "contexts": [{"ctxbRequest": ctxb_passt_request}],
        }
        times = []
        pms = []
        lines = []
        for j in range(0, max_connects):
            #  print(f"1 passthrough, {j} connect")
            #  print(json.dumps(compose_req))
            start = time.perf_counter_ns()
            resp = post("http://localhost:8086/nsd/compose", json=compose_req)
            request_time = time.perf_counter_ns() - start
            resp.raise_for_status()
            times.append(request_time/1000000)
            resp_lines = len(yaml.safe_dump(resp.json()).splitlines())
            #  print(f"lines: {resp_lines})
            #  print(resp.json())
            print(f"Request completed in {request_time/1000000} ms")
            pms.append(math.pow(1.3 * 3.2 * (resp_lines / 1000), 1.05))
            lines.append(resp_lines)
            compose_req["contexts"].append({"ctxbRequest": ctxb_connect_requests[j]})
            #  print(json.dumps(compose_req))
        #  for t in pms:
        #      print(t / 1000000)
        nsd_effort.append(pms)
        nsd_lines.append(lines)
        times_matrix.append(times)
    with open("comp_test_effort_vsb.csv", mode="w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(["vsb lines", "vsb effort", "vsb nsd lines"])
        writer.writerows(vsb_lines_effort)
    with open("comp_test_effort_nsd.csv", mode="w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow([f"{i} connect" for i in range(0, max_connects)])
        writer.writerows(nsd_effort)
    with open("comp_test_lines_nsd.csv", mode="w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow([f"{i} connect" for i in range(0, max_connects)])
        writer.writerows(nsd_lines)
    with open("comp_test_times.csv", mode="w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow([f"{i} connect" for i in range(0, max_connects)])
        writer.writerows(times_matrix)


if __name__ == "__main__":
    main()
