"""
Software License Agreement (Apache 2.0)

Copyright (c) 2020, The MITRE Corporation.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This project was developed by The MITRE Corporation.
If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
"""

"""
Script that captures data over a list of crawls and aggregates that data into
one csv file. Designed to be used to compare metrics/data across crawls.
"""

import argparse
from pathlib import Path
import sys
import json

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()

    # Should be specified in configuration; here only as convenience to
    # support testing
    parser.add_argument('crawl_dirs', type=str,
                        help='Path that contains all demodocus output '
                             'directories to get data from OR Path and filename'
                             ' of a txt file where each line represents a '
                             'single demodocus output directory or a single'
                             'demodocus output directory.')
    parser.add_argument('-o', '--output_fpath', type=str,
                        default="./aggregated_metrics.csv",
                        help='Path and filename to write the aggregated metrics'
                             ' to. (default is "aggregated_metrics.csv" in '
                             'the current directory)')
    args = parser.parse_args()

    # Make sure the output_fpath is a csv
    output_fpath = Path(args.output_fpath)
    assert output_fpath.suffix == ".csv", "Unable to continue, the output_fpa" \
                                          "th specified is not a .csv"

    # Get crawl directories
    crawl_dirs_path_ob = Path(args.crawl_dirs)
    if crawl_dirs_path_ob.suffix == "":
        # We are in a single output directory
        if (crawl_dirs_path_ob / "analyzed_data.json").is_file():
            crawl_dirs = [crawl_dirs_path_ob]

        # We are in an directory of demodocus outputs, we want to get all
        #  subdirectories to get data from
        else:
            crawl_dirs = [x for x in crawl_dirs_path_ob.iterdir() if x.is_dir()]
    elif crawl_dirs_path_ob.suffix == ".txt":
        # Txt file. Load it in and
        with open(crawl_dirs_path_ob) as f:
            lines = f.readlines()
        crawl_dirs = [Path(l.strip()) for l in lines]
    else:
        sys.exit(f'Cannot load path below (needs to be a directory or a txt '
                 f'file):\n\t{str(crawl_dirs_path_ob)}')

    return crawl_dirs, output_fpath


if __name__ == '__main__':
    # Get crawl directories
    crawl_dirs, output_fpath = parse_args()

    # Initialize the aggregate dataframe to None. This will track data for each
    #  crawl.
    aggregate_df = None

    # Iterate over crawl directories and record data
    for crawl_dir in crawl_dirs:

        data_for_crawl = dict()

        # Load relevant data from "crawl.csv" (assumes one entry point per csv)
        crawl_data_fpath = crawl_dir / "crawl.csv"
        if not crawl_data_fpath.exists():
            print(f"Cannot find 'crawl.csv' at the directory below. Skipping "
                  f"this crawl:\n\t{crawl_dir}")
            continue
        crawl_data_df = pd.read_csv(crawl_data_fpath)
        data_for_crawl["entry_point"] = crawl_data_df["entry_point"][0]
        data_for_crawl["users_crawled"] = crawl_data_df["users_crawled"].max()
        data_for_crawl["total_runtime"] = crawl_data_df["duration_sec"].max()
        data_for_crawl["build_runtime"] = crawl_data_df[crawl_data_df["users_crawled"] == "OmniUser"]["duration_sec"][0]
        data_for_crawl["num_states"] = crawl_data_df["num_nodes"][0]
        data_for_crawl["num_edges"] = crawl_data_df["num_edges"][0]

        # Load relevant data from "analyzed_data.json"
        analyzed_data_fpath = crawl_dir / "analyzed_data.json"
        if not analyzed_data_fpath.exists():
            print(f"Cannot find 'analyzed_data.json' at the directory below. "
                  f"Skipping this crawl:\n\t{crawl_dir}")
            continue
        with open(analyzed_data_fpath) as json_file:
            analyzed_data = json.load(json_file)
        data_for_crawl["page_elements"] = len(analyzed_data["els_states"]["unique_el_xpaths"])
        for user in analyzed_data["network_metrics"].keys():
            # capture these just once
            if "num_dynamic_states" not in data_for_crawl:
                data_for_crawl["num_dynamic_states"] = data_for_crawl["num_states"] - analyzed_data["network_metrics"][user]["builduser_stub_nodes"] - 1
            data_for_crawl[f"{user}_num_states"] = analyzed_data["network_metrics"][user]["crawluser_nodes"]
            data_for_crawl[f"{user}_num_edges"] = analyzed_data["network_metrics"][user]["crawluser_edges"]
            data_for_crawl[f"{user}_num_dead_end_edges"] = len(analyzed_data["accessibility"][user].keys())

        # Load relevant data from "element_map.json"
        element_map_fpath = crawl_dir / "element_map.json"
        if not element_map_fpath.exists():
            print(
                f"Cannot find 'element_map.json' at the directory below. "
                f"Skipping this crawl:\n\t{crawl_dir}")
            continue
        with open(element_map_fpath) as json_file:
            element_map = json.load(json_file)
        for value in element_map.values():
            for violation in value["violations"]:
                if violation["type"] == "atomic":
                    category = violation["category"].replace(" ", "_")
                    if category in data_for_crawl:
                        data_for_crawl[category] += 1
                    else:
                        data_for_crawl[category] = 1
        violation_types = ["S.C._2.5.5", "S.C._2.1.1", "S.C._2.4.3",
                           "S.C._2.4.7", "S.C._1.4.3"]
        for violation_type in violation_types:
            if violation_type not in data_for_crawl:
                data_for_crawl[violation_type] = 0

        # Append values to aggregate_df
        crawl_dir_df = pd.DataFrame([data_for_crawl])
        if aggregate_df is None:
            aggregate_df = crawl_dir_df
            aggregate_df = aggregate_df[list(data_for_crawl.keys())]
        else:
            aggregate_df = pd.concat([aggregate_df, crawl_dir_df], sort=False)

    # Write the csv to the specified path
    aggregate_df.to_csv(output_fpath, index=False)
