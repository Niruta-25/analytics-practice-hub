"""Copy the downloadable data files from the course materials into public/datasets.

Usage:
    python scripts/copy_datasets.py "<path to materials folder>"

The two large databases (movies.db, pcards.db) are copied too, so downloads work
when the site runs locally. They are listed in .gitignore because they exceed
what the repository and the host accept; see the README for where they are hosted.
"""
import shutil
import sys
from pathlib import Path

MAT = Path(sys.argv[1])
DEST = Path(__file__).resolve().parent.parent / "public" / "datasets"
DEST.mkdir(parents=True, exist_ok=True)

# Same file list as the question bank builder, kept here so this script has no heavy imports.
FILES = [
    "1. Excel Part 1/PWC Excel Assignment/NYC_Film_Permits.txt",
    "1. Excel part 2/ETL Assignment/data/case 1/Analytics_mindset_case_studies_ETL_Case1.csv",
    "1. Excel part 2/ETL Assignment/data/case 2/Analytics_mindset_case_studies_ETL_Case2_Excel.xlsx",
    "1. Excel part 2/ETL Assignment/data/case 3/Analytics_mindset_case_studies_ETL_Case3_Excel.xlsx",
    "1. Excel part 2/ETL Assignment/data/case 4/Analytics_mindset_case_studies_ETL_Case4_Excel.xlsx",
    "1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_2015payroll.csv",
    "1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_2016payroll.csv",
    "1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_jobcodes.csv",
    "1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_locations.csv",
    "2. SQL part 1/Assignments/cs50 assignment/songs/songs.db",
    "2. SQL part 1/Assignments/cs50 assignment/movies/movies.db",
    "2. SQL part 1/Assignments/pwc assignment/Chinook_Sqlite.sqlite",
    "2. SQL part 2/Pcards Assignment/pcards.db",
]
for f in FILES:
    src = MAT / f
    shutil.copy2(src, DEST / src.name)
    print(f"copied {src.name} ({src.stat().st_size / 1e6:.1f} MB)")
