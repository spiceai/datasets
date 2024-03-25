import argparse
import glob
import os
import pandas as pd
from typing import List
import wget
import zipfile

columns = ["date", "serial_number", "failure", "smart_194_raw", "smart_12_raw", "smart_9_raw"]

def quarters_for_year(year: int) -> List[int]:
    if year <= 2015:
        return [0]
    return [1, 2, 3, 4]

def quarter_to_zipname(year: int, q: int) -> str:
    if year <= 2015:
        return f"data_{year}.zip"
    return f"data_Q{q}_{year}.zip"

def extract_zip(year: int, q: int, zip_dir: str):
    zip_file = os.path.join(zip_dir, quarter_to_zipname(year, q))
    csv_files = os.path.join(zip_dir, f"{year}*.csv")
    output_parquet = f"parquet_data_Q{q}_{year}.parquet"
    print(f"Processing year={year}, q={q}")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(zip_dir)

    print(f"  [{year}][{q}] Extracted files")
    pd.concat(
        (pd.read_csv(f, usecols=columns) for f in glob.glob(csv_files)), ignore_index=True
        ).to_parquet(output_parquet)

    print(f"  [{year}][{q}] Created Parquet. Size", os.path.getsize(output_parquet)/1024**2)

    os.remove(zip_file)
    print(f"  [{year}][{q}] Removed Zip")
    for f in glob.glob(csv_files):
        os.remove(f)
    print(f"  [{year}][{q}] Removed CSVs")

def download(year: int, q: int, zip_dir: str):
    """Download the ZIP file for a given year and quarter."""
    print(f"Downloading ZIP file for year={year} q={q}")
    wget.download(f"https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/{quarter_to_zipname(year, q)}", os.path.join(zip_dir, quarter_to_zipname(year, q)))
    print()

def lifespan_percentage(group):
    """
    Calculate the percentage of life of a hard drive based on the first failure date.
    """
    group = group.sort_values("date")
    if group["failure"].max() == 0:
        group["life_percentage"] = None
        return group

    failure_date = group[group["failure"] == 1]["date"].iloc[0]
    first_day = group["date"].iloc[0]

    total_lifespan = (failure_date-first_day).days
    group["age"] = (group["date"] - first_day).dt.days
    group["life_percentage"] = group["age"] / total_lifespan
    return group[group["life_percentage"] <= 1.0].drop(columns=["age"])


def convert_raw_parquet_to_failure_dataset(parquet_folder: str, output_parquet_filepath: str = "failures_data.parquet"):
    """ Convert a set of raw SMART parquet data into a dataset that tracks the duration of hard drives (keyed on 'serial_number'). 

    The dataset will have the following columns:
        - ts: timestamp
        - serial_number: hard drive serial number
        - smart_9_raw: Power-On Hours
        - smart_12_raw: Power Cycle Count
        - smart_194_raw: Temperature or Temperature Celsius
        - y: Percentage (as decimal, [0, 1.0]) of life of the hard drive. This represents a normalised
            value of the hard drive's life based on the first failure date. 
    """
    df = pd.concat(pd.read_parquet(p) for p in glob.glob(os.path.join(parquet_folder, "parquet_data_*.parquet")))

    # Handle two formats "%Y-%m-%d" and "%m/%d/%Y"
    df["date2"] = pd.to_datetime(df["date"], errors='coerce')
    mask = pd.isna(df["date2"])
    df.loc[mask, "date2"] = pd.to_datetime(df.loc[mask, "date"], format="%m/%d/%Y", errors='coerce')
    df["date"] = df["date2"]

    df = df.groupby("serial_number").apply(lifespan_percentage)
    df["date"] = (df["date"].astype("int64") / 1000000).astype("int64")
    df = df.rename(columns={"date": "ts", "life_percentage": "y"})
    df = df[["ts", "serial_number", "smart_9_raw", "smart_12_raw", "smart_194_raw", "y"]]
    df = df.reset_index(drop=True)
    df[~df[["smart_9_raw", "smart_12_raw", "smart_194_raw", "y"]].isnull().any(axis=1)].to_parquet(output_parquet_filepath)

def main():
    parser = argparse.ArgumentParser(description="Process data based on a range of years.")
    parser.add_argument("--min-year", type=int, required=False, help="Minimum year to process", default=2016)
    parser.add_argument("--max-year", type=int, required=False, help="Maximum year to process", default=2023)
    parser.add_argument("--output-parquet", type=str, required=False, help="Maximum year to process", default="failures_data.parquet")

    args = parser.parse_args()
    
    for y in range(args.min_year, args.max_year+1):
        for q in quarters_for_year(y):
            download(y, q, "./")
            extract_zip(y, q, "./")

    convert_raw_parquet_to_failure_dataset("./", args.output_parquet)

if __name__ == "__main__":
    main()
