#!/usr/bin/env python3
"""
PBS Pakistan Imports — Master Pipeline Runner
Running this script to process all 11 source files and produce a single unified silver CSV covering 2002-03 to 2023-24.

Usage:
    python run_pipeline.py

Files that are missing from input/ are skipped with a warning.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent / 'scripts'
INPUT   = Path(__file__).parent / 'input'
OUTPUTS = Path(__file__).parent / 'outputs'
PY      = sys.executable


def run(cmd: list, label: str) -> bool:
    print(f"\n{'━'*60}")
    print(f"  {label}")
    print('━'*60)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"  ⚠  Exit code {result.returncode} — check output above.")
        return False
    return True


# All source files with their format number and --years argument
SOURCES = [
    (1, 'input\4_imp_2002-03_to_2007-08.pdf',                                          None),
    (1, 'input\5_imp_2008-09_to_2012-13.pdf',                                          None),
    (2, 'input\Import-by-commodities-and-countries-2014-15-2013-14.P6M.pdf',           '2014-2015,2013-2014'),
    (2, 'input\IMPORTS-BY-COMMODITIES-AND-COUNTRIES-2015-2016.txt',                    '2015-2016,2014-2015'),
    (2, 'input\IMPORTS-BY-COMMODITIES-AND-COUNTRIES-PAKISTAN-2016-2017.txt',           '2016-2017,2015-2016'),
    (2, 'input\IMPORTS-BY-COMMODITIES-AND-COUNTRIES-2017-2018.txt',                    '2017-2018,2016-2017'),
    (2, 'input\IMPORTS-BY-COMMODITIES-AND-COUNTRIES-PAKISTAN-2018-2019.txt',               '2018-2019'),
    (2, 'input\IMPORT-BY-COMMODITIES-AND-COUNTRIES-2020-21.txt',                       '2020-2021,2019-2020'),
    (3, 'input\D-10_Import-06-2022.pdf',                                               '2021-2022,2020-2021'),
    (3, 'input\D-10_Import-06-2023.pdf',                                               '2022-2023,2021-2022'),
    (3, 'input\D-10_Import0624.pdf',                                                   '2023-2024,2022-2023'),
]


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    found, skipped = 0, 0

    for (fmt, filename, years) in SOURCES:
        src = INPUT / filename
        if not src.exists():
            print(f"\n SKIPPING (not found): {filename}")
            skipped += 1
            continue

        flag = '--pdf' if src.suffix.lower() == '.pdf' else '--txt'
        cmd  = [PY, str(SCRIPTS / 'extractor.py'),
                '--format', str(fmt),
                flag, str(src),
                '--out', str(OUTPUTS)]
        if years:
            cmd += ['--years', years]

        label = f"Format {fmt}  |  {filename}"
        run(cmd, label)
        found += 1

    """ # Silver layer 
    bronze_files = list(OUTPUTS.glob('*_bronze.csv'))
    if not bronze_files:
        print("\n No bronze CSV files were produced. Check that source files exist in input/")
        return

    run(
        [PY, str(SCRIPTS / 'silver.py'),
         '--bronze', str(OUTPUTS),
         '--out',    str(OUTPUTS / 'silver_all_years.csv')],
        'Silver Layer — consolidating all years'
    )
    */
    
    print(f"  Pipeline complete!")
    print(f"  Files processed : {found}  |  Skipped (missing): {skipped}")
    print(f"  Bronze CSVs     : outputs/*_bronze.csv")
    print(f"  Silver CSV      : outputs/silver_all_years.csv")
"""

if __name__ == '__main__':
    main()
