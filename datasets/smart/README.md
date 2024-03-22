# SMART dataset
This directory contains the code needed to download, parse and create a historical, [SMART](https://en.wikipedia.org/wiki/Self-Monitoring,_Analysis_and_Reporting_Technology) hard drive dataset. The data is from disk drives in [Backblaze](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data) data centers.


## Usage
To run the script for all data
```shell
python download.py
```

Or for specific years
```shell
python download.py --min-year 2016 --max-year 2018
```

And to name the final parquet dataset
```shell
python download.py --output-parquet /a/nother/location/output.parquet
```
