"""Build the practice question bank from the course materials.

Every answer in the bank is computed here from the actual data files, so the
site never shows an answer that has not been checked against the data.

Usage:
    python scripts/build_question_bank.py "<path to materials folder>"

Writes src/data/skills.json, src/data/questions.json, src/data/regression.json
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

MAT = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "src" / "data"
OUT.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Skills: the unit the coverage map tracks. Each question trains exactly one.
# --------------------------------------------------------------------------
SKILLS = [
    ("xl-import", "Excel", "Import and delimiters", "Bring a text file into Excel correctly: delimiter, text qualifier, data types and regional date/number settings."),
    ("xl-clean", "Excel", "Spot and fix data problems", "Find missing, invalid, duplicated or inconsistently formatted values and make them analysable."),
    ("xl-filter-sort", "Excel", "Filter and sort", "Narrow a table to the rows that matter and order them."),
    ("xl-count", "Excel", "Conditional counting", "Count rows that meet one or more conditions (COUNTIFS, distinct counts)."),
    ("xl-aggregate", "Excel", "Conditional totals and averages", "Sum or average a column for a subset of rows (SUMIFS, AVERAGEIFS)."),
    ("xl-pivot", "Excel", "Summarise with a PivotTable", "Group by one or two fields and rank the groups."),
    ("xl-dates", "Excel", "Date arithmetic", "Work with dates and times: durations, lead times, year and month parts."),
    ("xl-text", "Excel", "Extract text from codes", "Pull fields out of a combined code with LEFT, MID, RIGHT, FIND or Flash Fill."),
    ("xl-lookup", "Excel", "Join tables with lookups", "Bring fields from one table into another with XLOOKUP/VLOOKUP, including composite keys."),
    ("sql-select", "SQL", "SELECT with WHERE", "Return chosen columns for rows that meet a condition."),
    ("sql-sort-limit", "SQL", "ORDER BY and LIMIT", "Sort results and keep the top rows."),
    ("sql-aggregate", "SQL", "Aggregate functions", "COUNT, SUM, AVG, MIN and MAX over a set of rows."),
    ("sql-like", "SQL", "Pattern matching", "Match text with LIKE and wildcards, or lists with IN."),
    ("sql-groupby", "SQL", "GROUP BY and HAVING", "Aggregate per group and filter the groups."),
    ("sql-join", "SQL", "JOIN tables", "Combine related tables on their keys."),
    ("sql-subquery", "SQL", "Subqueries", "Use the result of one query inside another."),
    ("sql-calc", "SQL", "Calculated columns", "Derive new columns with arithmetic, CASE, text and date functions."),
    ("reg-predict", "Regression", "Make a prediction", "Plug values into the fitted equation."),
    ("reg-coef", "Regression", "Interpret a coefficient", "Say what a one-unit change means, holding the rest constant."),
    ("reg-signif", "Regression", "Judge significance", "Use the p-value to say whether an effect is distinguishable from zero."),
    ("reg-dummy", "Regression", "Interpret a 0/1 variable", "Read a dummy coefficient as a difference between two groups."),
    ("reg-interaction", "Regression", "Interpret an interaction", "Explain how one variable changes the effect of another."),
    ("reg-fit", "Regression", "Judge model fit", "Use R-squared and sample size to say how far to trust the model."),
]

PAYROLL = "1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_"
PAYROLL_FILES = [PAYROLL + "2015payroll.csv", PAYROLL + "2016payroll.csv", PAYROLL + "jobcodes.csv", PAYROLL + "locations.csv"]
ETL = "1. Excel part 2/ETL Assignment/data/"
SQL1 = "2. SQL part 1/Assignments/"
# key -> (display name, course part, files relative to the materials folder)
DATASETS = {
    "permits": ("NYC film permits", "Excel part 1", ["1. Excel Part 1/PWC Excel Assignment/NYC_Film_Permits.txt"]),
    "etl1": ("Balance sheet extract", "Excel part 2", [ETL + "case 1/Analytics_mindset_case_studies_ETL_Case1.csv"]),
    "etl2": ("Employee codes (clean)", "Excel part 2", [ETL + "case 2/Analytics_mindset_case_studies_ETL_Case2_Excel.xlsx"]),
    "etl3": ("Employee codes (messy)", "Excel part 2", [ETL + "case 3/Analytics_mindset_case_studies_ETL_Case3_Excel.xlsx"]),
    "etl4": ("Journal entries", "Excel part 2", [ETL + "case 4/Analytics_mindset_case_studies_ETL_Case4_Excel.xlsx"]),
    "pay15": ("2015 payroll", "Excel part 3", PAYROLL_FILES),
    "pay16": ("2016 payroll", "Excel part 3", PAYROLL_FILES),
    "songs": ("Songs", "SQL part 1", [SQL1 + "cs50 assignment/songs/songs.db"]),
    "movies": ("Movies", "SQL part 1", [SQL1 + "cs50 assignment/movies/movies.db"]),
    "chinook": ("Chinook", "SQL part 1", [SQL1 + "pwc assignment/Chinook_Sqlite.sqlite"]),
    "pcards": ("Purchasing cards", "SQL part 2", ["2. SQL part 2/Pcards Assignment/pcards.db"]),
}

QUESTIONS = []
PREFIX = {"permits": "PER", "etl1": "BAL", "etl2": "EMP", "etl3": "EMM", "etl4": "JNL", "pay15": "P15",
          "pay16": "P16", "songs": "SNG", "movies": "MOV", "chinook": "CHI", "pcards": "PCD"}
_count = {}


def num(v, dp=2):
    """Format a number the way a student would read it off the screen."""
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    if isinstance(v, (float, np.floating)):
        if float(v).is_integer():
            return f"{int(v):,}"
        return f"{v:,.{dp}f}"
    return str(v)


def snum(v):
    """Format a value as a SQL client shows it: no thousands separator on small integers such as years."""
    if isinstance(v, int):
        return str(v) if abs(v) < 10000 else f"{v:,}"
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    return str(v)


def add(dataset, skill, text, answer, method, minutes=1.5, sql=None):
    _count[dataset] = _count.get(dataset, 0) + 1
    subject = "SQL" if skill.startswith("sql") else "Excel"
    q = {
        "id": f"{PREFIX[dataset]}-{_count[dataset]:02d}",
        "subject": subject,
        "dataset": dataset,
        "skill": skill,
        "minutes": minutes,
        "text": text,
        "answer": answer,
        "method": method,
    }
    if sql:
        q["sql"] = sql
    QUESTIONS.append(q)


# --------------------------------------------------------------------------
# SQL helper: the model query is executed, and its real output becomes the answer
# --------------------------------------------------------------------------
CONN = {}


def sqlq(dataset, skill, text, sql, minutes=1.5, note=None, show=3):
    con = CONN[dataset]
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        raise SystemExit(f"Query returned nothing, question would be pointless:\n{sql}")
    if len(rows) == 1 and len(cols) == 1:
        answer = snum(rows[0][0])
    elif len(rows) == 1:
        answer = "; ".join(f"{c} = {snum(v)}" for c, v in zip(cols, rows[0]))
    else:
        head = " | ".join(", ".join(snum(v) for v in r) for r in rows[:show])
        k = min(show, len(rows))
        lead = (f"First {k}" if k < len(rows) else "They are") if "ORDER BY" in sql else "For example (row order is not guaranteed without ORDER BY)"
        answer = f"{len(rows):,} rows ({', '.join(cols)}). {lead}: {head}"
    if note:
        answer += f" {note}"
    add(dataset, skill, text, answer, "Other queries are equally correct if they return the same result.", minutes, sql=" ".join(sql.split()))


# ==========================================================================
# EXCEL PART 1: NYC film permits
# ==========================================================================
def build_permits():
    p = pd.read_csv(MAT / "1. Excel Part 1/PWC Excel Assignment/NYC_Film_Permits.txt", dtype=str, keep_default_na=False)
    for c in ("StartDateTime", "EndDateTime", "EnteredOn"):
        p[c] = pd.to_datetime(p[c], format="%m/%d/%Y %H:%M")
    p["hours"] = (p.EndDateTime - p.StartDateTime).dt.total_seconds() / 3600
    p["lead"] = (p.StartDateTime - p.EnteredOn).dt.total_seconds() / 86400
    assert p.shape == (33502, 14 + 2)
    shoot = p[p.EventType == "Shooting Permit"]
    D = "permits"

    add(D, "xl-import",
        "Import NYC_Film_Permits.txt into Excel so every field sits in its own column. Which delimiter and text qualifier does the file use, and how many records and columns do you end up with?",
        f"Comma-delimited with double quotes as the text qualifier. {len(p):,} records and 14 columns.",
        "Data > From Text/CSV, delimiter Comma. The qualifier matters because EventAgency (\"Mayor's Office of Film, Theatre & Broadcasting\") contains a comma; without the quotes that value would split into two columns. Check the row count in the status bar or with =COUNTA(A:A)-1.",
        2)
    add(D, "xl-import",
        "StartDateTime is written month-first (for example 7/18/2016 6:00). Explain what goes wrong if your computer uses Danish regional settings, and how you import the column so the dates are right.",
        "Excel reads 7/18/2016 as day 7, month 18, which is not a date, so the value stays as text; a value such as 3/4/2016 is silently read as 3 April instead of 4 March.",
        "In Power Query, right-click the column > Change Type > Using Locale > Date/Time, English (United States). In the legacy Text Import Wizard, set the column data format to Date: MDY. Check afterwards that the column is right-aligned and that no month exceeds 12.",
        2)
    missing = (p.ZipCode == "N/A").sum()
    invalid = ((p.ZipCode != "N/A") & (p.ZipCode.str.len() != 5)).sum()
    add(D, "xl-clean",
        "How many permits have a missing zip code, and how many have a zip code that is present but invalid?",
        f"{missing} missing (recorded as N/A) and {invalid} invalid (the value 83, which is not five digits).",
        "Filter ZipCode and scan the dropdown list, or add a helper column =LEN(N2) and count the lengths with a PivotTable: 5 is valid, 3 is the text N/A, 2 is invalid.",
        1.5)
    add(D, "xl-clean",
        "One column holds the same value in every record and so adds nothing to an analysis. Which column is it, and how do you prove it?",
        "EventAgency: all 33,502 rows read \"Mayor's Office of Film, Theatre & Broadcasting\".",
        "Open the filter dropdown on each text column and look for one with a single entry, or use =COUNTIF(F:F,F2) and compare it with the record count.",
        1)
    add(D, "xl-clean",
        "The Country column should describe where the production company is based. How many permits are for a country other than the United States of America, and which countries are they?",
        f"{(p.Country != 'United States of America').sum()} permits: " + ", ".join(f"{k} ({v})" for k, v in p.Country.value_counts().items() if k != "United States of America") + ".",
        "PivotTable with Country in Rows and Count of EventID in Values, or =COUNTIF(M2:M33503,\"<>United States of America\"). Limit the range to the data rows: on a whole column, empty cells also count as 'not equal'.",
        1.5)

    for bb in ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]:
        sub = p[p.Borough == bb]
        b = "the Bronx" if bb == "Bronx" else bb
        s = (sub.EventType == "Shooting Permit").sum()
        add(D, "xl-count",
            f"How many permits in {b} are shooting permits, and how many are of any other type?",
            f"{s:,} shooting permits and {len(sub) - s:,} others ({len(sub):,} in total).",
            f"=COUNTIFS(H:H,\"{bb}\",B:B,\"Shooting Permit\") for the first number; subtract it from =COUNTIF(H:H,\"{bb}\") for the second.",
            1.5)
        cat = sub[sub.EventType == "Shooting Permit"].Category.value_counts()
        add(D, "xl-pivot",
            f"Show the number of shooting permits in {b} for each Category, largest first. Which category leads, and by how much over the second?",
            f"{cat.index[0]} leads with {cat.iloc[0]:,}; {cat.index[1]} is second with {cat.iloc[1]:,} (a gap of {cat.iloc[0] - cat.iloc[1]:,}).",
            "PivotTable: Category in Rows, Count of EventID in Values, filters Borough and EventType. Sort the count column descending.",
            2)
        sh = sub[sub.EventType == "Shooting Permit"]
        add(D, "xl-dates",
            f"What is the average duration, in hours, of a shooting permit in {b}?",
            f"{sh.hours.mean():.2f} hours.",
            "Add a helper column =(D2-C2)*24 (EndDateTime minus StartDateTime, converted from days to hours), then =AVERAGEIFS(helper,H:H,\"" + bb + "\",B:B,\"Shooting Permit\").",
            2)
        first = sh.sort_values(["StartDateTime", "EventID"], key=lambda s: s if s.name == "StartDateTime" else s.astype(int)).iloc[0]
        add(D, "xl-filter-sort",
            f"Filter to shooting permits in {b} and sort by StartDateTime, earliest first (ties by EventID, smallest first). What are the EventID and start date of the first row?",
            f"EventID {first.EventID}, starting {first.StartDateTime:%d %B %Y at %H:%M}.",
            "Turn on filters (Ctrl+Shift+L), filter Borough and EventType, then Data > Sort with two levels: StartDateTime oldest to newest, then EventID smallest to largest.",
            1.5)
        longn = (sh.hours > 24).sum()
        add(D, "xl-dates",
            f"How many shooting permits in {b} last longer than 24 hours?",
            f"{longn:,} permits.",
            "Helper column =(D2-C2)*24, then =COUNTIFS(H:H,\"" + bb + "\",B:B,\"Shooting Permit\",helper,\">24\").",
            2)

    for y in [2013, 2014, 2015, 2016, 2017]:
        ys = shoot[shoot.StartDateTime.dt.year == y]
        add(D, "xl-dates",
            f"How many shooting permits started in {y}?",
            f"{len(ys):,} permits.",
            f"=COUNTIFS(B:B,\"Shooting Permit\",C:C,\">=\"&DATE({y},1,1),C:C,\"<\"&DATE({y + 1},1,1)). Using the upper bound of 1 January next year keeps permits that start late on 31 December.",
            1.5)
        add(D, "xl-dates",
            f"For shooting permits starting in {y}, what is the average lead time in days between EnteredOn and StartDateTime?",
            f"{ys.lead.mean():.2f} days.",
            f"Helper column =C2-E2 (already in days), then AVERAGEIFS with the same {y} date bounds on StartDateTime and EventType = Shooting Permit.",
            2)
        rank = ys.Borough.value_counts()
        add(D, "xl-pivot",
            f"Rank the boroughs by the number of shooting permits that started in {y}.",
            "; ".join(f"{i + 1}. {k} ({v:,})" for i, (k, v) in enumerate(rank.items())) + ".",
            "Add a helper column =YEAR(C2). PivotTable: Borough in Rows, Count of EventID in Values, filters year and EventType; sort descending.",
            2)

    for street in ["BROADWAY", "5 AVENUE", "WALL STREET", "BEDFORD AVENUE", "LEXINGTON AVENUE"]:
        n = shoot.ParkingHeld.str.upper().str.contains(street, regex=False).sum()
        add(D, "xl-text",
            f"How many shooting permits mention {street} anywhere in ParkingHeld, ignoring upper and lower case?",
            f"{n:,} permits.",
            f"=COUNTIFS(B:B,\"Shooting Permit\",G:G,\"*{street}*\"). The asterisks are wildcards for any text before and after, and COUNTIFS is not case-sensitive.",
            1.5)
    multi = shoot["CommunityBoard(s)"].str.contains(",").mean()
    assert abs(multi - 0.0784) < 0.0001
    add(D, "xl-text",
        "What percentage of shooting permits needed approval from more than one Community Board?",
        f"{multi * 100:.2f}%.",
        "Several boards are listed in one cell separated by commas, so count cells containing a comma: =COUNTIFS(B:B,\"Shooting Permit\",I:I,\"*,*\") divided by =COUNTIF(B:B,\"Shooting Permit\").",
        2)
    for sc in ["Student Film", "Pilot", "News", "Feature", "Reality"]:
        n = (shoot.SubCategoryName == sc).sum()
        if sc == "Student Film":
            assert n == 193
        add(D, "xl-count",
            f"How many shooting permits were granted where SubCategoryName is \"{sc}\"?",
            f"{n:,} permits.",
            f"=COUNTIFS(B:B,\"Shooting Permit\",L:L,\"{sc}\").",
            1)
    for cat in ["Television", "Film", "Commercial", "Still Photography"]:
        s = shoot[shoot.Category == cat]
        add(D, "xl-aggregate",
            f"What is the average duration in hours of shooting permits in the {cat} category, and how does it compare with the average for all shooting permits?",
            f"{s.hours.mean():.2f} hours, against {shoot.hours.mean():.2f} hours for all shooting permits.",
            f"Helper column =(D2-C2)*24, then =AVERAGEIFS(helper,B:B,\"Shooting Permit\",K:K,\"{cat}\") and the same without the Category condition.",
            2)
    et = p.EventType.value_counts()
    add(D, "xl-pivot",
        "Show the number of permits for each EventType, largest first.",
        "; ".join(f"{k} ({v:,})" for k, v in et.items()) + ".",
        "PivotTable: EventType in Rows, Count of EventID in Values, sorted descending.",
        1.5)
    ct = pd.crosstab(p.EventType, p.Borough)
    add(D, "xl-pivot",
        "Build a table of permit counts with EventType down the side and Borough across the top. Which single combination is the largest?",
        f"Shooting Permit in Manhattan with {ct.loc['Shooting Permit', 'Manhattan']:,} permits; Shooting Permit in Brooklyn is next with {ct.loc['Shooting Permit', 'Brooklyn']:,}.",
        "PivotTable: EventType in Rows, Borough in Columns, Count of EventID in Values.",
        2)
    add(D, "xl-dates",
        "What are the oldest and the newest EnteredOn values in the file? Give the full date and time.",
        f"Oldest {p.EnteredOn.min():%d %B %Y %H:%M}; newest {p.EnteredOn.max():%d %B %Y %H:%M}.",
        "=MIN(E:E) and =MAX(E:E), formatted as date and time. This only works if the column was imported as real dates, not text.",
        1)


# ==========================================================================
# EXCEL PART 2: ETL cases
# ==========================================================================
def build_etl():
    etl = MAT / "1. Excel part 2/ETL Assignment/data"
    D = "etl1"
    add(D, "xl-import",
        "Open Analytics_mindset_case_studies_ETL_Case1.csv. One company's rows shift one column to the right when the file is split on commas. Which company, why, and what would have prevented it?",
        "Apple, Inc.: the comma inside the name is read as a delimiter because the name is not wrapped in a text qualifier. Quoting the name (\"Apple, Inc.\") or exporting with a pipe delimiter would have prevented it.",
        "Compare the number of fields per row: the header has 8, the Apple rows have 9. Fix by merging the two name cells back together and shifting the rest left.",
        2)
    add(D, "xl-clean",
        "The Cash column in the balance sheet extract cannot be summed as it stands. Name the formatting problems you see in that column and state Apple's 2018 cash as a plain number.",
        "Values mix plain numbers with abbreviated text: \"25900 M\" means millions and \"900 K\" means thousands. Apple's 2018 cash is 25,900,000,000.",
        "Split the number from the suffix (Text to Columns on the space, or =LEFT(D2,FIND(\" \",D2)-1)), then multiply by 1,000,000 for M and 1,000 for K with an IF.",
        2)
    add(D, "xl-clean",
        "List at least four different data problems in the balance sheet extract that must be fixed before analysis, other than the Cash column.",
        "Any four of: missing tickers (Armada Hoffler); tickers with stray spaces (A M Z N, AM ZN); a duplicated row (Aptevo 2018); numbers stored as text with thousands separators; negatives shown two ways, in brackets and with a minus sign; blanks, spaces and dashes all used for zero in Inventories; Total Current Assets in a different scale from the other columns.",
        "Scan each column with a filter dropdown, sort to bring oddities together, and use Remove Duplicates and Find & Replace for the fixes.",
        2.5)
    add(D, "xl-clean",
        "How many exact duplicate rows does the balance sheet extract contain, and which record is duplicated?",
        "One duplicate: Aptevo Therapeutics Inc. for 2018 appears twice, leaving 20 unique records out of 21.",
        "Data > Remove Duplicates across all columns reports how many were removed; or flag them with =COUNTIFS on ticker and year.",
        1)

    # Case 2: fixed-width codes such as USA1218-17M
    e2 = pd.read_excel(etl / "case 2/Analytics_mindset_case_studies_ETL_Case2_Excel.xlsx", sheet_name="Case 2", dtype=str)
    assert len(e2) == 597
    m = e2.EmployeeCode.str.extract(r"^([A-Z]{3})(\d+)-(\d+)([A-Z]+)$")
    assert m.notna().all().all()
    e2[["loc", "emp", "plant", "pay"]] = m
    D = "etl2"
    add(D, "xl-text",
        "In the clean employee code file, split EmployeeCode (for example USA1218-17M) into Location, EmpID, PlantID and PayPeriod using formulas. Give the four formulas for a code in A2.",
        "Location =LEFT(A2,3); EmpID =MID(A2,4,4); PlantID =MID(A2,FIND(\"-\",A2)+1,2); PayPeriod =RIGHT(A2,1). For USA1218-17M these return USA, 1218, 17 and M.",
        "The codes are fixed width here, so positions can be hard-coded; FIND on the hyphen makes PlantID robust if EmpID ever changes length.",
        2)
    for loc, name in [("USA", "the United States"), ("JAP", "Japan"), ("GER", "Germany"), ("MEX", "Mexico")]:
        n = (e2["loc"] == loc).sum()
        w = ((e2["loc"] == loc) & (e2.pay == "W")).sum()
        add(D, "xl-text",
            f"After extracting Location and PayPeriod from EmployeeCode, how many employees work in {name} ({loc}), and how many of them are paid weekly?",
            f"{n} employees, of whom {w} are paid weekly.",
            f"Location =LEFT(A2,3), PayPeriod =RIGHT(A2,1); then =COUNTIF(loc,\"{loc}\") and =COUNTIFS(loc,\"{loc}\",pay,\"W\").",
            2)
    lp = (e2["loc"] + "-" + e2.plant).value_counts()
    add(D, "xl-text",
        "Create LocationPlantID by joining Location and PlantID with a hyphen (for example USA-12). How many different plants does the company have, and which plant has the most employees?",
        f"{lp.size} different plants. The largest is {lp.index[0]} with {lp.iloc[0]} employees.",
        "=LEFT(A2,3)&\"-\"&MID(A2,FIND(\"-\",A2)+1,2), then a PivotTable counting employees per LocationPlantID. Neither field alone identifies a plant because every country starts numbering at 10.",
        2.5)
    add(D, "xl-clean",
        "Is EmpID on its own a unique identifier in the clean employee code file? Show how you check.",
        f"{'Yes' if e2.emp.is_unique else 'No'}: there are {e2.emp.nunique()} distinct EmpID values for {len(e2)} rows.",
        "Extract EmpID, then compare the row count with the count of distinct values (Remove Duplicates on a copy, or =SUMPRODUCT(1/COUNTIF(range,range))).",
        1.5)

    # Case 3: messy codes such as Japan177-3Mo
    e3 = pd.read_excel(etl / "case 3/Analytics_mindset_case_studies_ETL_Case3_Excel.xlsx", sheet_name="Case 3 data", dtype=str)
    m = e3.EmployeeCode.str.extract(r"^([A-Za-z]+)(\d+)-(\d+)([A-Za-z]+)$")
    assert m.notna().all().all() and len(e3) == 597
    e3[["loc", "emp", "plant", "pay"]] = m
    D = "etl3"
    add(D, "xl-text",
        "In the messy employee code file the Location is no longer three characters (ARG, Canada, Japan, US). Explain how a formula can find where the Location ends, and give the Location and EmpID for Canada351-3W.",
        "Location is Canada and EmpID is 351. The Location ends just before the first digit in the code.",
        "Find the first digit with =MIN(IFERROR(FIND({0,1,2,3,4,5,6,7,8,9},A2),999)); Location is =LEFT(A2,that-1) and EmpID is the text between that position and the hyphen. Flash Fill (Ctrl+E) does the same from two or three typed examples.",
        2.5)
    for loc in ["Japan", "Canada", "US", "ARG"]:
        n = (e3["loc"] == loc).sum()
        add(D, "xl-text",
            f"After extracting Location from the messy employee codes, how many employees have the Location \"{loc}\"?",
            f"{n} employees.",
            "Extract Location as the text before the first digit (formula or Flash Fill), then =COUNTIF(loc,\"" + loc + "\"). Test with exact match so US is not confused with AUS.",
            2)
    monthly = e3.pay.isin(["M", "Mo"]).sum()
    add(D, "xl-clean",
        "PayPeriod is recorded inconsistently in the messy employee codes (W or We, M or Mo). After standardising it, how many employees are paid monthly and how many weekly?",
        f"{monthly} monthly and {len(e3) - monthly} weekly.",
        "Extract the letters after the PlantID, then standardise on the first letter: =LEFT(pay,1). Count with COUNTIF. Without standardising, M and Mo would be reported as two different groups.",
        2)
    lp3 = (e3["loc"] + "-" + e3.plant).value_counts()
    add(D, "xl-text",
        "Build LocationPlantID (for example US-8) from the messy employee codes. Which plant has the most employees, and how many plants are there?",
        f"{lp3.index[0]} with {lp3.iloc[0]} employees; {lp3.size} plants in total.",
        "PlantID is the digits between the hyphen and the pay period letters. Extract the pay period first (one or two letters at the end), then PlantID =MID(A2,FIND(\"-\",A2)+1,LEN(A2)-FIND(\"-\",A2)-LEN(pay)). Flash Fill does it from a few typed examples. Join Location and PlantID with &.",
        2.5)

    # Case 4: journal entries to be joined to four lookup tables
    f4 = etl / "case 4/Analytics_mindset_case_studies_ETL_Case4_Excel.xlsx"
    je = pd.read_excel(f4, sheet_name="JELineItems")
    bu = pd.read_excel(f4, sheet_name="BusinessUnits")
    coa = pd.read_excel(f4, sheet_name="ChartOfAccounts").iloc[:, :4]
    prep = pd.read_excel(f4, sheet_name="PreparerInfo")
    src = pd.read_excel(f4, sheet_name="Source").dropna().drop_duplicates()
    je["Amount"] = pd.to_numeric(je.Amount)
    D = "etl4"
    j = je.merge(bu, on="BusinessUnitID", how="left").merge(coa, on="GLAccountNumber", how="left")
    assert len(j) == len(je)
    add(D, "xl-count",
        "How many journal entry line items are in JELineItems, and how many distinct journal entries (JENumber) do they make up?",
        f"{len(je):,} line items in {je.JENumber.nunique():,} journal entries.",
        "=COUNTA(A:A)-1 for the lines. For distinct entries use Remove Duplicates on a copy of JENumber, a PivotTable row count, or =COUNTA(UNIQUE(A2:A790)).",
        1.5)
    for unit in ["HOTEL", "FOOD SERVICE", "HOTEL PANTRY"]:
        s = j[j.BusinessUnit == unit]
        add(D, "xl-lookup",
            f"Add the BusinessUnit name to each journal entry line. How many lines belong to {unit}, and what is the total of their Debit column?",
            f"{len(s):,} lines with total debits of {pd.to_numeric(s.Debit, errors='coerce').sum():,.2f}.",
            "=XLOOKUP(C2,BusinessUnits!A:A,BusinessUnits!B:B) or =VLOOKUP(C2,BusinessUnits!A:B,2,FALSE), filled down. Then COUNTIF and SUMIF on the new column.",
            2.5)
    at = j.groupby("AccountType").Amount.sum().round(2)
    add(D, "xl-lookup",
        "Bring AccountType into the journal entry lines from ChartOfAccounts and total the Amount column by AccountType. What do the totals add up to, and why?",
        "; ".join(f"{k} {v:,.2f}" for k, v in at.items()) + f". They sum to {at.sum():,.2f} because every journal entry's debits equal its credits.",
        "The key (GLAccountNumber) is the second column in ChartOfAccounts, so VLOOKUP cannot be used directly; use =XLOOKUP(B2,ChartOfAccounts!B:B,ChartOfAccounts!C:C) or INDEX/MATCH. Then a PivotTable of Sum of Amount by AccountType.",
        3)
    bank = j[j.GLAccountName.str.strip() == "Operating Bank Account"]
    add(D, "xl-lookup",
        "After looking up GLAccountName, how many journal entry lines post to the Operating Bank Account, and what is the net Amount posted to it?",
        f"{len(bank):,} lines with a net amount of {bank.Amount.sum():,.2f}.",
        "=XLOOKUP(B2,ChartOfAccounts!B:B,ChartOfAccounts!A:A), then COUNTIF and SUMIF on the name.",
        2.5)
    pj = je.merge(prep, on=["PreparerID", "BusinessUnitID"], how="left")
    assert len(pj) == len(je)
    add(D, "xl-lookup",
        "PreparerID 101 appears five times in PreparerInfo. Explain why a lookup on PreparerID alone gives wrong names, and what the correct key is.",
        f"PreparerID is only unique within a business unit: ID 101 is a different person in each of five units. The unique key is PreparerID together with BusinessUnitID. A lookup on PreparerID alone returns the first match (Carolyn Slater) for all {int((je.PreparerID == 101).sum())} lines with ID 101.",
        "Build a helper key in both tables, for example =D2&\"-\"&C2, and look up on that; or use XLOOKUP with two conditions: =XLOOKUP(1,(PreparerInfo!B:B=D2)*(PreparerInfo!C:C=C2),PreparerInfo!A:A).",
        2.5)
    pj["who"] = pj.PreparerName.str.split("|").str[0].str.strip()
    top = pj.who.value_counts()
    add(D, "xl-lookup",
        "Using the composite key PreparerID + BusinessUnitID, attach PreparerName to every journal entry line. Which preparer has the most lines?",
        f"{top.index[0]} with {top.iloc[0]:,} lines; {top.index[1]} is next with {top.iloc[1]:,}.",
        "Helper key in both sheets (=PreparerID&\"-\"&BusinessUnitID), XLOOKUP on the helper, then a PivotTable counting lines per preparer.",
        3)
    add(D, "xl-clean",
        "PreparerName holds values such as \"Carolyn Slater|Food Operations Manager\" followed by invisible padding. How do you separate the name from the job title and remove the padding?",
        f"Split on the pipe: the name is the text before | and the title is the text after it. The padding is non-breaking spaces (character 160), which TRIM alone does not remove. {prep.PreparerName.str.contains('|', regex=False).sum()} of the {len(prep)} entries contain a pipe; the others (POS, GUESTSYS) are systems, not people.",
        "Name =LEFT(A2,FIND(\"|\",A2)-1); title =TRIM(SUBSTITUTE(MID(A2,FIND(\"|\",A2)+1,99),CHAR(160),\"\")). Wrap in IFERROR for the entries with no pipe.",
        2.5)
    sj = je.merge(src, on="SourceID", how="left")
    sc = sj.Source.value_counts()
    add(D, "xl-lookup",
        "Look up the Source description for each journal entry line and count the lines per source. Which source is most common?",
        f"{sc.index[0]} with {sc.iloc[0]:,} lines, followed by {sc.index[1]} ({sc.iloc[1]:,}).",
        "=XLOOKUP(E2,Source!A:A,Source!B:B), then a PivotTable. Check the Source sheet for blank or repeated rows first.",
        2)
    je["month"] = pd.to_datetime(je.EffectiveDate).dt.to_period("M")
    add(D, "xl-dates",
        "What are the earliest and latest EffectiveDate in the journal entry lines?",
        f"From {pd.to_datetime(je.EffectiveDate).min():%d %B %Y} to {pd.to_datetime(je.EffectiveDate).max():%d %B %Y}.",
        "=MIN(F:F) and =MAX(F:F), formatted as dates.",
        1)


# ==========================================================================
# EXCEL PART 3: IntegrateCo payroll
# ==========================================================================
def build_payroll():
    base = MAT / "1. Excel part 3/IntegrateCo Assignment"
    p15 = pd.read_csv(base / "Analytics_mindset_case_studies_IntegrateCo_2015payroll.csv", sep="|", dtype={"Job": str})
    p16 = pd.read_csv(base / "Analytics_mindset_case_studies_IntegrateCo_2016payroll.csv", sep="|", dtype={"Project": str})
    jc = pd.read_csv(base / "Analytics_mindset_case_studies_IntegrateCo_jobcodes.csv", sep="|", dtype=str)
    loc = pd.read_csv(base / "Analytics_mindset_case_studies_IntegrateCo_locations.csv", sep="|")
    pat = r"^\d{2}[A-Za-z]?(\d{3})"
    p15["code"] = p15.Job.str.extract(pat)[0]
    p16["code"] = p16.Project.str.extract(pat)[0]
    assert p15.code.notna().all() and p16.code.notna().all()
    p15["gross"] = p15.Reg_Pay + p15.OT_Pay
    p15["date"] = pd.to_datetime(p15.Pay_Date, format="%m/%d/%Y")
    names = dict(zip(jc.Job_Code, jc.Job_Description))
    g15, g16 = p15.gross.sum(), p16.Gross_Wages.sum()
    assert 255000 < g16 - g15 < 275000, g16 - g15  # the case says roughly $266,000

    D = "pay15"
    add(D, "xl-import",
        "The 2015 payroll file is named .csv but does not use commas. Which delimiter does it use, how do you load it, and how many data rows and columns do you get?",
        f"Pipe (|) delimited. {len(p15):,} data rows and 16 columns.",
        "Data > From Text/CSV and choose Custom delimiter |, or Text to Columns > Delimited > Other: |. Opening it by double-click puts each line in one cell because Excel looks for commas.",
        2)
    add(D, "xl-import",
        "When you import the job codes file, the codes 001 to 012 turn into 1 to 12. Why does that matter for this case, and how do you stop it?",
        "Excel converts them to numbers and drops the leading zeros. The case states job codes are three-digit text, and the code you extract from the Job field (for example 005) is text, so a lookup of \"005\" against the number 5 fails.",
        "Set the column's data type to Text during import (Power Query: Change Type > Text; wizard: column data format Text). To repair afterwards use =TEXT(A2,\"000\").",
        2)
    add(D, "xl-text",
        "The Job field combines a two-digit start year, an optional department letter, a three-digit job code and an optional location code. What is the job code in 14S001SG, 15007B and 14005, and what formula extracts it?",
        "001, 007 and 005.",
        "The job code starts at position 3 unless the third character is a letter: =IF(ISNUMBER(VALUE(MID(H2,3,1))),MID(H2,3,3),MID(H2,4,3)). Keep the result as text.",
        2.5)
    for code in ["005", "002", "001", "006"]:
        s = p15[p15.code == code]
        add(D, "xl-text",
            f"Extract the job code from the Job field in the 2015 payroll. How many rows belong to job code {code} ({names[code]}), and what is their total regular pay (Reg_Pay)?",
            f"{len(s):,} rows with total Reg_Pay of {s.Reg_Pay.sum():,.2f}.",
            f"Extract with =IF(ISNUMBER(VALUE(MID(H2,3,1))),MID(H2,3,3),MID(H2,4,3)); then =COUNTIF(code,\"{code}\") and =SUMIF(code,\"{code}\",K:K).",
            2.5)
    add(D, "xl-aggregate",
        "What was total gross pay (Reg_Pay plus OT_Pay) in the 2015 payroll file?",
        f"{g15:,.2f}.",
        "=SUM(K:K)+SUM(L:L), or add a Gross column =K2+L2 so it matches Gross_Wages in the 2016 file.",
        1)
    bad = p15[~p15.code.isin(jc.Job_Code)]
    assert len(bad) == 1
    add(D, "xl-clean",
        "Job codes outside 001 to 012 are errors according to the case. How many 2015 payroll rows carry an invalid job code, and which codes are they?",
        f"{len(bad)} row: Job {bad.Job.iloc[0]} yields the code {bad.code.iloc[0]}, which is not in the job code table. It carries gross pay of {bad.gross.sum():,.2f}.",
        "Extract the code, then =ISNA(MATCH(code,JobCodes!A:A,0)) flags rows with no match; filter on TRUE.",
        2.5)
    pv = p15.groupby("code").gross.sum().sort_values(ascending=False)
    add(D, "xl-pivot",
        "Summarise 2015 gross pay (Reg_Pay plus OT_Pay) by job code. Which three job codes cost the most?",
        "; ".join(f"{c} {names.get(c, 'not in job code table')} ({v:,.2f})" for c, v in pv.head(3).items()) + ".",
        "Add Gross and job code columns, then a PivotTable: job code in Rows, Sum of Gross in Values, sorted descending.",
        2.5)
    hv = p15.groupby("code")[["Reg_Hrs", "OT_Hrs"]].sum().sum(axis=1).sort_values(ascending=False)
    add(D, "xl-pivot",
        "Summarise total hours (Reg_Hrs plus OT_Hrs) by job code for 2015. Which job code has the most hours and what is its average cost per hour?",
        f"Job code {hv.index[0]} ({names.get(hv.index[0])}) with {hv.iloc[0]:,.2f} hours; gross pay of {pv[hv.index[0]]:,.2f} gives {pv[hv.index[0]] / hv.iloc[0]:.2f} per hour.",
        "PivotTable with Sum of hours and Sum of Gross per job code; cost per hour is gross divided by hours, calculated beside the PivotTable or as a calculated field.",
        3)
    add(D, "xl-count",
        "How many different employees were paid in the 2015 file, and on how many different pay dates?",
        f"{p15.Emp_No.nunique()} employees on {p15.Pay_Date.nunique()} pay dates.",
        "=COUNTA(UNIQUE(C2:C" + str(len(p15) + 1) + ")) and the same for Pay_Date, or two PivotTables and count the rows. Use Emp_No, not the name, as the identifier.",
        1.5)
    add(D, "xl-count",
        "How many rows in the 2015 payroll include overtime (OT_Hrs greater than zero), and how many different employees do they cover?",
        f"{(p15.OT_Hrs > 0).sum():,} rows covering {p15[p15.OT_Hrs > 0].Emp_No.nunique()} employees.",
        "=COUNTIF(J:J,\">0\"); for employees, filter OT_Hrs > 0 and count distinct Emp_No.",
        1.5)
    ot = p15[p15.OT_Hrs > 0].groupby(["Emp_No", "First_Name", "Last_Name"])[["OT_Hrs", "OT_Pay"]].sum().sort_values("OT_Pay", ascending=False)
    (e, fn, ln), r = ot.index[0], ot.iloc[0]
    add(D, "xl-pivot",
        "Which employee earned the most overtime pay in the first six months of 2015, and how many overtime hours did that take?",
        f"{fn} {ln} (employee {e}) with {r.OT_Pay:,.2f} of overtime pay for {r.OT_Hrs:,.2f} hours.",
        "PivotTable: Emp_No and name in Rows, Sum of OT_Hrs and Sum of OT_Pay in Values, sorted by OT_Pay descending.",
        2)
    oj = p15.groupby("code")[["OT_Hrs", "OT_Pay"]].sum().sort_values("OT_Pay", ascending=False)
    add(D, "xl-lookup",
        "Which job code had the most overtime pay in 2015? Report its number, its description from the job codes table, the overtime hours and the overtime pay.",
        f"{oj.index[0]} {names.get(oj.index[0])}: {oj.iloc[0].OT_Hrs:,.2f} hours and {oj.iloc[0].OT_Pay:,.2f} of overtime pay.",
        "PivotTable of OT_Hrs and OT_Pay by extracted job code, then =XLOOKUP(code,JobCodes!A:A,JobCodes!B:B) for the description. Both sides of the lookup must be text.",
        3)
    for mth, label in [(1, "January"), (3, "March"), (6, "June")]:
        s = p15[p15.date.dt.month == mth]
        add(D, "xl-dates",
            f"What was total gross pay (Reg_Pay plus OT_Pay) for pay dates in {label} 2015, and how many pay dates fell in that month?",
            f"{s.gross.sum():,.2f} across {s.Pay_Date.nunique()} pay dates.",
            f"=SUMIFS(Gross,A:A,\">=\"&DATE(2015,{mth},1),A:A,\"<\"&DATE(2015,{mth + 1},1)), or add =MONTH(A2) and use a PivotTable. Pay_Date must be imported as a month-first date.",
            2)
    l15 = p15.assign(Employee_Name=p15.First_Name + " " + p15.Last_Name).merge(loc, on="Employee_Name", how="left")
    assert l15.Location.notna().all()
    for L in (1, 2):
        s = l15[l15.Location == L]
        add(D, "xl-lookup",
            f"Add each employee's location from the locations file to the 2015 payroll. What was total gross pay at location {L}, and how many employees worked there?",
            f"{s.gross.sum():,.2f} for {s.Emp_No.nunique()} employees.",
            "The locations file is keyed on the full name, so build it first: =F2&\" \"&G2, then =XLOOKUP(name,Locations!A:A,Locations!B:B). Finish with SUMIF and a distinct count.",
            3)

    D = "pay16"
    add(D, "xl-aggregate",
        "What was total gross pay in the 2016 payroll file, and by how much does it exceed 2015 (Reg_Pay plus OT_Pay)?",
        f"{g16:,.2f} in 2016 against {g15:,.2f} in 2015: an increase of {g16 - g15:,.2f}, the roughly $266,000 the CFO asked about.",
        "=SUM(G:G) on the 2016 sheet. For 2015 add Reg_Pay and OT_Pay, because Gross_Wages in 2016 is defined as their sum.",
        2)
    add(D, "xl-clean",
        "The 2015 and 2016 payroll files come from different systems. Name three differences you must resolve before the two years can be compared.",
        f"Level of detail: 2015 has one row per employee, job and pay date ({len(p15):,} rows), 2016 has no dates and one row per employee and project ({len(p16):,} rows). Field names: Emp_No/Employee_Number, Job/Project, Reg_Hrs/Hours. Structure: 2015 splits First_Name and Last_Name and Reg_Pay and OT_Pay, 2016 has one Employee_Name and one Gross_Wages.",
        "Aggregate 2015 up to employee and job code, build common fields (job code, full name, gross), and add a Year column if you stack the files.",
        2.5)
    for code in ["005", "002", "004"]:
        a, b = p15[p15.code == code].gross.sum(), p16[p16.code == code].Gross_Wages.sum()
        add(D, "xl-aggregate",
            f"Compare gross pay for job code {code} ({names[code]}) between 2015 and 2016. What is the difference?",
            f"2015: {a:,.2f}; 2016: {b:,.2f}; difference (2016 minus 2015): {b - a:,.2f}.",
            f"Extract the job code in both sheets, then =SUMIF(code16,\"{code}\",Gross_Wages) minus =SUMIF(code15,\"{code}\",Gross).",
            3)
    d = (p16.groupby("code").Gross_Wages.sum() - p15.groupby("code").gross.sum()).dropna().sort_values(ascending=False)
    add(D, "xl-pivot",
        "Which three job codes show the largest increase in gross pay from 2015 to 2016? Include only job codes with pay in both years.",
        "; ".join(f"{c} {names.get(c, '')} (+{v:,.2f})" for c, v in d.head(3).items()) + ".",
        "One PivotTable per year of gross pay by job code, placed side by side (or one PivotTable on the stacked data with Year in Columns), then a difference column sorted descending.",
        3)
    h16 = p16.groupby("code")[["Hours", "OT_Hours"]].sum().sum(axis=1)
    w16 = p16.groupby("code").Gross_Wages.sum()
    c = w16.idxmax()
    add(D, "xl-pivot",
        "In the 2016 payroll, which job code has the highest gross wages, and what is its average cost per hour (gross wages divided by Hours plus OT_Hours)?",
        f"{c} {names.get(c)}: {w16[c]:,.2f} over {h16[c]:,.2f} hours, or {w16[c] / h16[c]:.2f} per hour.",
        "Extract the job code from Project, PivotTable with Sum of Gross_Wages, Hours and OT_Hours, then divide.",
        2.5)
    named = p16.dropna(subset=["Employee_Name"])
    blank = p16[p16.Employee_Name.isna()]
    assert len(blank) > 0 and blank.Employee_Number.isna().all()
    n15 = set(p15.Emp_No)
    n16 = set(named.Employee_Number.astype(int))
    add(D, "xl-count",
        "How many different employees appear in the 2016 payroll, and how many of them were not in the 2015 file?",
        f"{len(n16)} employees, of whom {len(n16 - n15)} do not appear in 2015. ({len(n15 - n16)} employees from 2015 are missing from 2016.)",
        "Distinct count of Employee_Number; then =COUNTIF('2015Data'!C:C,number)=0 on the distinct list flags the new employees. Employee_Number is the field that matches Emp_No, not the new Employee_ID. Ignore rows where the number is blank.",
        2.5)
    add(D, "xl-clean",
        "Some rows in the 2016 payroll have no employee name or number. How many rows are affected, and how much gross pay do they carry?",
        f"{len(blank)} rows with gross wages of {blank.Gross_Wages.sum():,.2f}, which is {blank.Gross_Wages.sum() / g16 * 100:.1f}% of the 2016 total. They cannot be assigned to an employee or a location, so they need to be raised with the CFO.",
        "Filter Employee_Name for (Blanks), or =COUNTBLANK(D2:D" + str(len(p16) + 1) + ") and =SUMIF(D:D,\"\",G:G).",
        2)
    l16 = named.merge(loc, on="Employee_Name", how="left")
    assert l16.Location.notna().all()
    for L in (1, 2):
        s = l16[l16.Location == L]
        add(D, "xl-lookup",
            f"Add each employee's location to the 2016 payroll from the locations file. What were total gross wages at location {L}?",
            f"{s.Gross_Wages.sum():,.2f} for {s.Employee_Number.nunique()} employees. The two locations do not add up to the file total because {len(blank)} rows have no employee name and return #N/A.",
            "=XLOOKUP(D2,Locations!A:A,Locations!B:B) on Employee_Name, then =SUMIF(location," + str(L) + ",G:G).",
            2.5)
    o16 = p16.groupby(["Employee_Number", "Employee_Name"]).OT_Hours.sum().sort_values(ascending=False)
    add(D, "xl-filter-sort",
        "Sort the 2016 payroll to find the single row with the highest Gross_Wages. Which employee and project is it?",
        (lambda r: f"{r.Employee_Name}, project {r.Project}, with gross wages of {r.Gross_Wages:,.2f}.")(p16.sort_values("Gross_Wages", ascending=False).iloc[0]),
        "Data > Sort on Gross_Wages, largest to smallest, with 'My data has headers' ticked so whole rows move together.",
        1)
    add(D, "xl-filter-sort",
        "Filter the 2016 payroll to rows with overtime (OT_Hours greater than zero). How many rows remain, and which employee has the most overtime hours in total?",
        f"{(p16.OT_Hours > 0).sum():,} rows. {o16.index[0][1]} has the most with {o16.iloc[0]:,.2f} hours.",
        "Number filter > Greater Than 0 on OT_Hours; the status bar shows the row count. Then a PivotTable or SUMIF per employee.",
        2)


# ==========================================================================
# SQL PART 1: songs, movies, Chinook
# ==========================================================================
def build_songs():
    D = "songs"
    for col, cut in [("tempo", 150), ("danceability", 0.85), ("energy", 0.8)]:
        sqlq(D, "sql-select", f"List the names of all songs with {col} greater than {cut}.",
             f"SELECT name FROM songs WHERE {col} > {cut}", 1)
    sqlq(D, "sql-select", "List the names of songs whose danceability, energy and valence are all greater than 0.7.",
         "SELECT name FROM songs WHERE danceability > 0.7 AND energy > 0.7 AND valence > 0.7", 1.5)
    sqlq(D, "sql-sort-limit", "List the names of the five longest songs, longest first.",
         "SELECT name FROM songs ORDER BY duration_ms DESC LIMIT 5", 1, show=5)
    sqlq(D, "sql-sort-limit", "Show the name and tempo of the three slowest songs, slowest first.",
         "SELECT name, tempo FROM songs ORDER BY tempo ASC LIMIT 3", 1)
    sqlq(D, "sql-sort-limit", "Show the name and energy of the five most energetic songs, highest first.",
         "SELECT name, energy FROM songs ORDER BY energy DESC LIMIT 5", 1, show=5)
    sqlq(D, "sql-aggregate", "What is the average energy of all songs in the database?",
         "SELECT ROUND(AVG(energy), 4) AS avg_energy FROM songs", 1)
    sqlq(D, "sql-aggregate", "How many songs are longer than four minutes (240,000 ms)?",
         "SELECT COUNT(*) AS n FROM songs WHERE duration_ms > 240000", 1)
    sqlq(D, "sql-aggregate", "What are the lowest and highest tempo in the database?",
         "SELECT MIN(tempo) AS slowest, MAX(tempo) AS fastest FROM songs", 1)
    sqlq(D, "sql-like", "List the names of songs that feature another artist (the name contains \"feat.\").",
         "SELECT name FROM songs WHERE name LIKE '%feat.%'", 1)
    sqlq(D, "sql-like", "How many song names start with the letter S?",
         "SELECT COUNT(*) AS n FROM songs WHERE name LIKE 'S%'", 1)
    for artist in ["Drake", "Post Malone", "Ed Sheeran"]:
        sqlq(D, "sql-join", f"List the names of the songs by {artist}, without assuming you know the artist's id.",
             f"SELECT s.name FROM songs s JOIN artists a ON a.id = s.artist_id WHERE a.name = '{artist}'", 1.5, show=6)
    for artist in ["Post Malone", "XXXTENTACION"]:
        sqlq(D, "sql-join", f"What is the average energy of songs by {artist}?",
             f"SELECT ROUND(AVG(s.energy), 4) AS avg_energy FROM songs s JOIN artists a ON a.id = s.artist_id WHERE a.name = '{artist}'", 1.5)
    sqlq(D, "sql-groupby", "Show each artist's name and number of songs, most songs first, and keep the top five.",
         "SELECT a.name, COUNT(*) AS songs FROM songs s JOIN artists a ON a.id = s.artist_id GROUP BY a.name ORDER BY songs DESC, a.name LIMIT 5", 2, show=5)
    sqlq(D, "sql-groupby", "Which artists have more than three songs in the database? Show the name and the number of songs.",
         "SELECT a.name, COUNT(*) AS songs FROM songs s JOIN artists a ON a.id = s.artist_id GROUP BY a.name HAVING COUNT(*) > 3 ORDER BY songs DESC, a.name", 2, show=5)
    sqlq(D, "sql-subquery", "How many songs have an energy above the average energy of all songs?",
         "SELECT COUNT(*) AS n FROM songs WHERE energy > (SELECT AVG(energy) FROM songs)", 1.5)
    sqlq(D, "sql-subquery", "List the names of Drake's songs using a subquery instead of a JOIN.",
         "SELECT name FROM songs WHERE artist_id = (SELECT id FROM artists WHERE name = 'Drake')", 1.5, show=4)
    sqlq(D, "sql-calc", "Show each song's name and its length in minutes rounded to two decimals, longest first, top three.",
         "SELECT name, ROUND(duration_ms / 60000.0, 2) AS minutes FROM songs ORDER BY duration_ms DESC LIMIT 3", 1.5)


def build_movies():
    D = "movies"
    for y in [2008, 2012]:
        sqlq(D, "sql-select", f"List the titles of all movies released in {y}. How many rows does the query return?",
             f"SELECT title FROM movies WHERE year = {y}", 1, show=2)
    for person in ["Emma Stone", "Tom Hanks"]:
        sqlq(D, "sql-select", f"In what year was {person} born?",
             f"SELECT birth FROM people WHERE name = '{person}'", 1)
    sqlq(D, "sql-sort-limit", "List the titles of all movies released in 2019 or later in alphabetical order. What are the first three?",
         "SELECT title FROM movies WHERE year >= 2019 ORDER BY title", 1.5)
    for cut in [9.5, 9.0]:
        sqlq(D, "sql-aggregate", f"How many movies have a rating of {cut} or higher?",
             f"SELECT COUNT(*) AS n FROM ratings WHERE rating >= {cut}", 1)
    for series in ["Harry Potter", "Star Wars", "Toy Story"]:
        sqlq(D, "sql-like", f"List the title and year of every movie whose title begins with \"{series}\", in chronological order.",
             f"SELECT title, year FROM movies WHERE title LIKE '{series}%' ORDER BY year, title", 1.5)
    for y in [2010, 2015]:
        sqlq(D, "sql-join", f"What is the average rating of movies released in {y}?",
             f"SELECT ROUND(AVG(r.rating), 2) AS avg_rating FROM movies m JOIN ratings r ON r.movie_id = m.id WHERE m.year = {y}", 1.5)
    for title in ["Toy Story", "The Dark Knight"]:
        sqlq(D, "sql-join", f"List the names of the people who starred in the movie titled exactly \"{title}\" (take the earliest movie with that title).",
             f"SELECT p.name FROM people p JOIN stars s ON s.person_id = p.id WHERE s.movie_id = (SELECT id FROM movies WHERE title = '{title}' ORDER BY year LIMIT 1)", 2.5, show=5)
    sqlq(D, "sql-join", "List the titles of the five highest-rated movies in which Tom Hanks starred, best first (ties in alphabetical order).",
         "SELECT m.title FROM movies m JOIN stars s ON s.movie_id = m.id JOIN people p ON p.id = s.person_id JOIN ratings r ON r.movie_id = m.id WHERE p.name = 'Tom Hanks' ORDER BY r.rating DESC, m.title LIMIT 5", 3, show=5)
    sqlq(D, "sql-groupby", "How many movies were released in each year from 2015 to 2019? Show the year and the count.",
         "SELECT year, COUNT(*) AS movies FROM movies WHERE year BETWEEN 2015 AND 2019 GROUP BY year ORDER BY year", 1.5, show=5)
    sqlq(D, "sql-groupby", "For movies released in 2012, show how many received each rating from 8.5 upwards, highest rating first.",
         "SELECT r.rating, COUNT(*) AS movies FROM movies m JOIN ratings r ON r.movie_id = m.id WHERE m.year = 2012 AND r.rating >= 8.5 GROUP BY r.rating ORDER BY r.rating DESC", 2.5)
    sqlq(D, "sql-subquery", "List the titles of all movies in which both Johnny Depp and Helena Bonham Carter starred.",
         "SELECT title FROM movies WHERE id IN (SELECT movie_id FROM stars WHERE person_id = (SELECT id FROM people WHERE name = 'Johnny Depp')) AND id IN (SELECT movie_id FROM stars WHERE person_id = (SELECT id FROM people WHERE name = 'Helena Bonham Carter')) ORDER BY title", 3, show=6)
    sqlq(D, "sql-subquery", "How many different people have directed a movie with a rating of at least 9.0?",
         "SELECT COUNT(DISTINCT person_id) AS n FROM directors WHERE movie_id IN (SELECT movie_id FROM ratings WHERE rating >= 9.0)", 2)


def build_chinook():
    D = "chinook"
    for c in ["France", "Germany", "Canada", "Brazil"]:
        sqlq(D, "sql-join", f"Show each customer's first name, last name, the invoice id and the total for every invoice billed to {c}, largest total first (ties by invoice id).",
             f"SELECT c.FirstName, c.LastName, i.InvoiceId, i.Total FROM Invoice i JOIN Customer c ON c.CustomerId = i.CustomerId WHERE i.BillingCountry = '{c}' ORDER BY i.Total DESC, i.InvoiceId", 2)
    for cut in [5, 10, 15]:
        sqlq(D, "sql-aggregate", f"How many invoices have a total greater than ${cut}?",
             f"SELECT COUNT(*) AS n FROM Invoice WHERE Total > {cut}", 1)
    sqlq(D, "sql-select", "How many invoices have a total greater than $5 and less than $10?",
         "SELECT COUNT(*) AS n FROM Invoice WHERE Total > 5 AND Total < 10", 1)
    sqlq(D, "sql-select", "List the first name, last name and company of customers who have a company recorded.",
         "SELECT FirstName, LastName, Company FROM Customer WHERE Company IS NOT NULL", 1.5)
    sqlq(D, "sql-like", "How many invoices come from customers billed in the USA, Canada or Mexico?",
         "SELECT COUNT(*) AS n FROM Invoice WHERE BillingCountry IN ('USA', 'Canada', 'Mexico')", 1)
    for letter in ["B", "S", "I"]:
        sqlq(D, "sql-like", f"How many invoices have a billing country that starts with \"{letter}\"?",
             f"SELECT COUNT(*) AS n FROM Invoice WHERE BillingCountry LIKE '{letter}%'", 1)
    sqlq(D, "sql-sort-limit", "Sort the customers by last name. Show the first and last name of the first five.",
         "SELECT FirstName, LastName FROM Customer ORDER BY LastName, FirstName LIMIT 5", 1, show=5)
    sqlq(D, "sql-sort-limit", "Show the five largest invoices: invoice id, billing country and total.",
         "SELECT InvoiceId, BillingCountry, Total FROM Invoice ORDER BY Total DESC, InvoiceId LIMIT 5", 1, show=5)
    sqlq(D, "sql-aggregate", "What are the earliest and latest invoice dates in the database?",
         "SELECT MIN(InvoiceDate) AS first_invoice, MAX(InvoiceDate) AS last_invoice FROM Invoice", 1)
    sqlq(D, "sql-aggregate", "How many distinct unit prices appear on invoice lines, and what are the lowest and highest?",
         "SELECT COUNT(DISTINCT UnitPrice) AS prices, MIN(UnitPrice) AS lowest, MAX(UnitPrice) AS highest FROM InvoiceLine", 1.5)
    sqlq(D, "sql-groupby", "List the billing countries by total invoice value, highest first. Show the top five.",
         "SELECT BillingCountry, ROUND(SUM(Total), 2) AS revenue FROM Invoice GROUP BY BillingCountry ORDER BY revenue DESC LIMIT 5", 1.5, show=5)
    sqlq(D, "sql-groupby", "How many invoice lines were sold at each unit price?",
         "SELECT UnitPrice, COUNT(*) AS lines FROM InvoiceLine GROUP BY UnitPrice ORDER BY UnitPrice", 1.5)
    sqlq(D, "sql-groupby", "Which billing countries have more than 30 invoices? Show the country and the number of invoices.",
         "SELECT BillingCountry, COUNT(*) AS invoices FROM Invoice GROUP BY BillingCountry HAVING COUNT(*) > 30 ORDER BY invoices DESC, BillingCountry", 2, show=5)
    sqlq(D, "sql-join", "Which genre has sold the most tracks? Show the three best-selling genres with the number of invoice lines.",
         "SELECT g.Name, COUNT(*) AS sold FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId GROUP BY g.Name ORDER BY sold DESC LIMIT 3", 3)
    sqlq(D, "sql-join", "Show the five artists with the most albums in the catalogue: artist name and number of albums.",
         "SELECT ar.Name, COUNT(*) AS albums FROM Album al JOIN Artist ar ON ar.ArtistId = al.ArtistId GROUP BY ar.Name ORDER BY albums DESC, ar.Name LIMIT 5", 2, show=5)
    sqlq(D, "sql-subquery", "How many invoices have a total above the average invoice total?",
         "SELECT COUNT(*) AS n FROM Invoice WHERE Total > (SELECT AVG(Total) FROM Invoice)", 1.5)
    sqlq(D, "sql-subquery", "How many tracks in the catalogue have never appeared on an invoice line?",
         "SELECT COUNT(*) AS n FROM Track WHERE TrackId NOT IN (SELECT TrackId FROM InvoiceLine)", 2)
    sqlq(D, "sql-calc", "How many characters long is the longest customer last name, and whose is it?",
         "SELECT LastName, LENGTH(LastName) AS letters FROM Customer ORDER BY letters DESC, LastName LIMIT 1", 1.5)
    sqlq(D, "sql-calc", "How old, in whole years, was each employee when hired? Show first name, last name and age at hire, oldest first.",
         "SELECT FirstName, LastName, CAST((julianday(HireDate) - julianday(BirthDate)) / 365.25 AS INTEGER) AS age_at_hire FROM Employee ORDER BY (julianday(HireDate) - julianday(BirthDate)) DESC", 2.5)
    sqlq(D, "sql-calc", "On which weekday was each employee born? Count the employees per weekday (0 = Sunday).",
         "SELECT strftime('%w', BirthDate) AS weekday, COUNT(*) AS employees FROM Employee GROUP BY weekday ORDER BY weekday", 2.5, show=7)


# ==========================================================================
# SQL PART 2: purchasing cards
# ==========================================================================
def build_pcards():
    D = "pcards"
    sqlq(D, "sql-aggregate", "What is the total number of P-card transactions in the database? Label the column TotalTrans.",
         "SELECT COUNT(*) AS TotalTrans FROM pcards", 1)
    for cut in [5000, 10000, 25000]:
        sqlq(D, "sql-aggregate", f"How many P-card transactions have an amount of ${cut:,} or more?",
             f"SELECT COUNT(*) AS n FROM pcards WHERE Amount >= {cut}", 1)
    for y in [2012, 2013, 2014]:
        sqlq(D, "sql-sort-limit", f"Show the five most expensive transactions of {y} (Year = {y}): cardholder name, amount and vendor, most expensive first.",
             f"SELECT FullName, Amount, Vendor FROM pcards WHERE Year = {y} ORDER BY Amount DESC, FullName LIMIT 5", 1.5)
        sqlq(D, "sql-select", f"How many {y} transactions (Year = {y}) were for more than $3,000?",
             f"SELECT COUNT(*) AS n FROM pcards WHERE Year = {y} AND Amount > 3000", 1)
        sqlq(D, "sql-aggregate", f"Returns are recorded as negative amounts. What is the total dollar amount returned from January to March of {y} (Year = {y}, Month 1 to 3)?",
             f"SELECT ROUND(SUM(Amount), 2) AS TotalReturns FROM pcards WHERE Year = {y} AND Month BETWEEN 1 AND 3 AND Amount < 0", 1.5)
        sqlq(D, "sql-groupby", f"Which five cardholders made the most transactions in {y}? Show the name and the number of transactions as NumTrans.",
             f"SELECT FullName, COUNT(*) AS NumTrans FROM pcards WHERE Year = {y} GROUP BY FullName ORDER BY NumTrans DESC, FullName LIMIT 5", 2)
        sqlq(D, "sql-subquery", f"How many {y} transactions are greater than the average transaction amount for {y}?",
             f"SELECT COUNT(*) AS n FROM pcards WHERE Year = {y} AND Amount > (SELECT AVG(Amount) FROM pcards WHERE Year = {y})", 2)
    for vendor in ["Amazon", "Walmart", "Staples"]:
        sqlq(D, "sql-like", f"How many 2014 transactions (Year = 2014) came from a vendor with \"{vendor}\" anywhere in the name, and what did they total?",
             f"SELECT COUNT(*) AS n, ROUND(SUM(Amount), 2) AS total FROM pcards WHERE Year = 2014 AND Vendor LIKE '%{vendor}%'", 1.5)
    sqlq(D, "sql-groupby", "How many transactions are there for each year? Most recent year first; label the count TotalTrans.",
         "SELECT Year, COUNT(*) AS TotalTrans FROM pcards GROUP BY Year ORDER BY Year DESC", 1.5, show=5)
    for n in [500, 1000]:
        sqlq(D, "sql-groupby", f"Which cardholders made more than {n:,} transactions in 2014? Show the name and NumTrans, highest first.",
             f"SELECT FullName, COUNT(*) AS NumTrans FROM pcards WHERE Year = 2014 GROUP BY FullName HAVING COUNT(*) > {n} ORDER BY NumTrans DESC, FullName", 2)
    sqlq(D, "sql-groupby", "Who returned the greatest dollar amount of goods in 2014? Show the top three with ReturnedGoodsValue and ReturnedGoodsCount.",
         "SELECT FullName, ROUND(SUM(Amount), 2) AS ReturnedGoodsValue, COUNT(*) AS ReturnedGoodsCount FROM pcards WHERE Year = 2014 AND Amount < 0 GROUP BY FullName ORDER BY ReturnedGoodsValue ASC LIMIT 3", 2.5)
    sqlq(D, "sql-groupby", "Which five merchant categories (MCC) had the highest total spend in 2014?",
         "SELECT MCC, ROUND(SUM(Amount), 2) AS spend FROM pcards WHERE Year = 2014 GROUP BY MCC ORDER BY spend DESC LIMIT 5", 2, show=5)
    sqlq(D, "sql-calc", "OSU does not pay the 4.5% state sales tax. For each year, show total spend and the sales tax avoided (SalesTaxSaved), most recent year first.",
         "SELECT Year, ROUND(SUM(Amount), 2) AS TotalSpent, ROUND(SUM(Amount) * 0.045, 2) AS SalesTaxSaved FROM pcards GROUP BY Year ORDER BY Year DESC", 2, show=5)
    sqlq(D, "sql-calc", "Classify 2014 returns by risk: High if the return is $1,000 or more, Medium if $500 or more, otherwise Low. How many returns fall in each class?",
         "SELECT CASE WHEN Amount <= -1000 THEN 'High' WHEN Amount <= -500 THEN 'Medium' ELSE 'Low' END AS RiskRanking, COUNT(*) AS returns FROM pcards WHERE Year = 2014 AND Amount < 0 GROUP BY RiskRanking ORDER BY returns DESC", 3)
    sqlq(D, "sql-calc", "Assume OSU earns 0.75% on Amazon.com purchases of $500 or more and 0.50% on smaller ones. What would it have earned on 2014 purchases (positive amounts) from vendors with \"Amazon\" in the name? Label it AmazonEarnings.",
         "SELECT ROUND(SUM(CASE WHEN Amount >= 500 THEN Amount * 0.0075 ELSE Amount * 0.005 END), 2) AS AmazonEarnings FROM pcards WHERE Year = 2014 AND Vendor LIKE '%Amazon%' AND Amount > 0", 3)
    sqlq(D, "sql-subquery", "Which vendors received more in 2014 than the top vendor of 2013 received in 2013? Show the vendor and TotalSpent, highest first.",
         "SELECT Vendor, ROUND(SUM(Amount), 2) AS TotalSpent FROM pcards WHERE Year = 2014 GROUP BY Vendor HAVING SUM(Amount) > (SELECT SUM(Amount) FROM pcards WHERE Year = 2013 GROUP BY Vendor ORDER BY SUM(Amount) DESC LIMIT 1) ORDER BY TotalSpent DESC", 3)
    sqlq(D, "sql-subquery", "By what percentage did the number of transactions in 2014 differ from 2011? Round to two decimals.",
         "SELECT ROUND((COUNT(*) - (SELECT COUNT(*) FROM pcards WHERE Year = 2011)) * 100.0 / (SELECT COUNT(*) FROM pcards WHERE Year = 2011), 2) AS PercDiffFrom2011 FROM pcards WHERE Year = 2014", 3)
    sqlq(D, "sql-select", "List the cardholder name, amount and vendor of 2014 transactions described as \"AIR TRAVEL\" that cost more than $2,000, most expensive first.",
         "SELECT FullName, Amount, Vendor FROM pcards WHERE Year = 2014 AND Description = 'AIR TRAVEL' AND Amount > 2000 ORDER BY Amount DESC, FullName", 2)


# ==========================================================================
# EXCEL PART 4: regression interpretation, fitted on the restaurant data
# ==========================================================================
def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X)
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = resid @ resid / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    p = 2 * stats.t.sf(np.abs(beta / se), n - k)
    r2 = 1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))
    return [{"term": t, "b": float(b), "p": float(pv)} for t, b, pv in zip(["Intercept"] + names, beta, p)], float(r2), int(n)


def sig(x, digits=3):
    """Round to a few significant figures, as regression software prints."""
    if x == 0:
        return 0.0
    return float(f"{x:.{digits}g}")


def ptxt(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def build_regression():
    f = MAT / "1. Excel part 4/Regression Assignment/Restaurant/data.xlsm"
    sales = pd.read_excel(f, sheet_name="salesData")
    weather = pd.read_excel(f, sheet_name="weatherData")
    game = pd.read_excel(f, sheet_name="gameData")
    d = sales.groupby("date")[["netTotal", "netTotal_364", "netTotal_28", "quantity", "quantity_364"]].sum().reset_index()
    d = d.merge(weather, on="date", how="left").merge(game[["date", "gameDay", "homeGame"]], on="date", how="left")
    d[["gameDay", "homeGame"]] = d[["gameDay", "homeGame"]].fillna(0)
    d["weekend"] = (d.date.dt.dayofweek >= 5).astype(float)
    d["rain"] = (d.prcp > 0).astype(float)
    d = d.dropna(subset=["tmax", "prcp"]).reset_index(drop=True)
    INTER = {"ly_x_game": ("netTotal_364", "gameDay"), "ly_x_weekend": ("netTotal_364", "weekend"), "tmax_x_game": ("tmax", "gameDay")}
    for k, (a, b) in INTER.items():
        d[k] = d[a] * d[b]

    V = {  # variable -> (label, unit, kind)
        "tmax": ("Maximum temperature", "degrees Fahrenheit", "num", "degree Fahrenheit of maximum temperature"),
        "prcp": ("Precipitation", "inches", "num", "inch of precipitation"),
        "netTotal_364": ("Sales 364 days ago", "dollars", "num", "dollar of sales 364 days ago"),
        "netTotal_28": ("Sales 28 days ago", "dollars", "num", "dollar of sales 28 days ago"),
        "quantity_364": ("Items sold 364 days ago", "items", "num", "item sold 364 days ago"),
        "gameDay": ("Game day", "1 = football game that day, 0 = no game", "dummy", "a game day", "a day without a game"),
        "homeGame": ("Home game", "1 = home game that day, 0 = otherwise", "dummy", "a home game day", "any other day"),
        "weekend": ("Weekend", "1 = Saturday or Sunday, 0 = weekday", "dummy", "a weekend day", "a weekday"),
        "rain": ("Rainy day", "1 = any precipitation, 0 = dry", "dummy", "a rainy day", "a dry day"),
        "ly_x_game": ("Sales 364 days ago x Game day", "interaction", "inter"),
        "ly_x_weekend": ("Sales 364 days ago x Weekend", "interaction", "inter"),
        "tmax_x_game": ("Maximum temperature x Game day", "interaction", "inter"),
    }
    Y = {"netTotal": ("Daily net sales", "dollars"), "quantity": ("Daily items sold", "items")}
    specs = [
        ("Does temperature move sales?", "netTotal", ["tmax"]),
        ("Game days and sales", "netTotal", ["gameDay"]),
        ("Last year's sales and game days", "netTotal", ["netTotal_364", "gameDay", "ly_x_game"]),
        ("Forecasting from past sales", "netTotal", ["netTotal_364", "netTotal_28"]),
        ("Weather and game days together", "netTotal", ["tmax", "prcp", "gameDay"]),
        ("Weekends and temperature", "netTotal", ["weekend", "tmax"]),
        ("Home games and last year's sales", "netTotal", ["netTotal_364", "homeGame"]),
        ("Items sold, temperature and game days", "quantity", ["tmax", "gameDay"]),
        ("Rainy days and weekends", "netTotal", ["rain", "weekend"]),
        ("Items sold from last year's volume", "quantity", ["quantity_364", "weekend"]),
        ("Do weekends change how last year predicts this year?", "netTotal", ["netTotal_364", "weekend", "ly_x_weekend"]),
        ("Does temperature matter more on game days?", "netTotal", ["tmax", "gameDay", "tmax_x_game"]),
    ]
    exams = []
    for i, (title, yv, xs) in enumerate(specs, 1):
        coefs, r2, n = ols(d[yv].to_numpy(float), [d[x].to_numpy(float) for x in xs], xs)
        ylab, yunit = Y[yv]
        rows = []
        for c in coefs:
            c["b"] = sig(c["b"])
            lab = "Intercept" if c["term"] == "Intercept" else V[c["term"]][0]
            rows.append({"term": lab, "estimate": c["b"], "p": ptxt(c["p"])})
        B = {c["term"]: c for c in coefs}
        eq = f"Predicted {ylab.lower()} = b0 + " + " + ".join(f"b{j}[{V[x][0]}]" for j, x in enumerate(xs, 1))
        variables = [{"name": V[x][0], "unit": V[x][1],
                      "range": None if V[x][2] != "num" else f"{d[x].quantile(.05):,.0f} to {d[x].quantile(.95):,.0f}"} for x in xs]
        # A realistic scenario: medians for numbers, 1 for the first dummy
        scen = {}
        for x in xs:
            kind = V[x][2]
            if kind == "num":
                scen[x] = float(round(d[x].median(), 0 if d[x].median() > 20 else 1))
            elif kind == "dummy":
                scen[x] = 1.0
        ix = next((x for x in xs if x in INTER), None)
        if ix:
            scen[ix] = scen[INTER[ix][0]] * scen[INTER[ix][1]]
        pred = B["Intercept"]["b"] + sum(B[x]["b"] * scen[x] for x in xs)
        parts = [f"{V[x][0].lower()} of {scen[x]:,.10g} {V[x][1]}" for x in xs if V[x][2] == "num"]
        dparts = [V[x][3] for x in xs if V[x][2] == "dummy"]
        desc = (" that is " + " and ".join(dparts) if dparts else "") + (" with " + " and ".join(parts) if parts else "")
        work = f"{B['Intercept']['b']:,.10g}" + "".join(f" + ({B[x]['b']:,.10g} x {scen[x]:,.10g})" for x in xs)
        qs = [{"skill": "reg-predict",
               "text": f"Predict {ylab.lower()} for a day{desc}.",
               "answer": f"About {pred:,.0f} {yunit}. Working: {work} = {pred:,.2f}.",
               "say": "State the equation, substitute each value, and give the unit. Mention that the prediction is only as good as the model's fit."}]
        numx = [x for x in xs if V[x][2] == "num"]
        dumx = [x for x in xs if V[x][2] == "dummy"]
        others = " holding the other variables constant" if len(xs) > 1 else ""
        if numx:
            x = numx[0]
            b = B[x]["b"]
            ix0 = next((k for k in xs if k in INTER and INTER[k][0] == x), None)
            scope = f" on {V[INTER[ix0][1]][4]} (the interaction term changes this slope on {V[INTER[ix0][1]][3]})" if ix0 else others
            qs.append({"skill": "reg-coef",
                       "text": f"Interpret the coefficient on {V[x][0]}.",
                       "answer": f"Each additional {V[x][3]} is associated with {'an increase' if b > 0 else 'a decrease'} of {abs(b):,.10g} {yunit} in {ylab.lower()}{scope}.",
                       "say": "Give direction, size and unit, and say 'associated with' rather than 'causes'."})
        sx = ix if ix else (dumx[0] if dumx else numx[-1])
        pv = B[sx]["p"]
        verdict = ("is statistically significant at the 5% level: the p-value is below 0.05, so an effect this large would be unlikely if the true effect were zero"
                   if pv < 0.05 else
                   "is not statistically significant at the 5% level: the p-value is above 0.05, so the data cannot distinguish this effect from zero")
        qs.append({"skill": "reg-signif",
                   "text": f"Is the effect of {V[sx][0]} statistically significant at the 5% level? Explain to Bob what that means.",
                   "answer": f"With a p-value {'below 0.001' if pv < 0.001 else 'of ' + ptxt(pv)}, {V[sx][0].lower()} {verdict}.",
                   "say": "Compare the p-value with 0.05, then translate it into plain language for a restaurant owner. Not significant does not prove there is no effect."})
        if ix:
            nv, dv = INTER[ix]
            b1, b2, b3 = B[nv]["b"], B[dv]["b"], B[ix]["b"]
            one, ref = V[dv][3], V[dv][4]
            qs.append({"skill": "reg-interaction",
                       "text": f"How does {one} change the relationship between {V[nv][0].lower()} and {ylab.lower()}?",
                       "answer": f"On {ref}, each additional {V[nv][3]} is associated with a change of {b1:,.10g} {yunit}. On {one} the slope becomes {b1:,.10g} + ({b3:,.10g}) = {b1 + b3:,.10g}, and the starting level shifts by {b2:,.10g} {yunit}. The interaction's p-value is {ptxt(B[ix]['p'])}, so the difference in slopes is {'statistically significant' if B[ix]['p'] < 0.05 else 'not statistically significant'} at the 5% level.",
                       "say": "Explain that the interaction coefficient changes the slope, while the dummy coefficient changes the starting level. Check the interaction's p-value before leaning on it."})
        elif dumx:
            x = dumx[0]
            b = B[x]["b"]
            one, ref = V[x][3], V[x][4]
            qs.append({"skill": "reg-dummy",
                       "text": f"Interpret the coefficient on {V[x][0]}. What is the comparison group?",
                       "answer": f"Predicted {ylab.lower()} on {one} is {abs(b):,.10g} {yunit} {'higher' if b > 0 else 'lower'} than on {ref}, which is the comparison group{',' + others if others else ''}.",
                       "say": "Name the reference group (the 0 category) and express the coefficient as a difference between the two groups, not as a slope."})
        else:
            qs.append({"skill": "reg-fit",
                       "text": f"The model's R-squared is {r2:.3f} with {n} daily observations. How confident should Bob be in predictions from this model?",
                       "answer": f"The model explains {r2 * 100:.1f}% of the day-to-day variation in {ylab.lower()}, leaving {100 - r2 * 100:.1f}% unexplained. " + ("That is a reasonable basis for planning, with a margin for error." if r2 >= 0.5 else "Predictions will often miss by a wide margin, so Bob should treat them as a rough guide."),
                       "say": "Translate R-squared into 'share of variation explained', then give a practical judgement about ordering ingredients and scheduling staff."})
        if len(qs) < 4:
            qs.append({"skill": "reg-fit",
                       "text": f"The model's R-squared is {r2:.3f} with {n} daily observations. What does that tell Bob about relying on it?",
                       "answer": f"The model explains {r2 * 100:.1f}% of the variation in {ylab.lower()}; the remaining {100 - r2 * 100:.1f}% comes from factors not in the model. " + ("It is a usable planning tool." if r2 >= 0.5 else "On its own it is a weak basis for decisions."),
                       "say": "Translate R-squared into plain language and link it to Bob's decisions about ingredients and shifts."})
        for k, q in enumerate(qs[:4], 1):
            q["id"] = f"REG-{i:02d}-{k}"
        exams.append({"id": f"REG-{i:02d}", "title": title, "minutes": 5, "dependent": f"{ylab} ({yunit})",
                      "equation": eq, "variables": variables, "output": rows, "r2": round(r2, 3), "n": n, "questions": qs[:4]})
    return exams


def describe_datasets():
    """Column and table names per dataset, given to the AI tutor so its hints name real fields."""
    out = {}
    for key in ("songs", "movies", "chinook", "pcards"):
        con = CONN[key]
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        out[key] = "SQLite tables: " + "; ".join(
            f"{t}({', '.join(r[1] for r in con.execute(f'PRAGMA table_info({t})'))})" for t in tables)
    permits = pd.read_csv(MAT / DATASETS["permits"][2][0], nrows=0)
    out["permits"] = "Comma-delimited text file, columns A to N: " + ", ".join(permits.columns)
    out["etl1"] = "Comma-separated file, columns: Ticker, Name, Year, Cash, Accounts Receivables, Inventories, Total Current Assets, Total Depreciation"
    out["etl2"] = "Excel sheet 'Case 2', columns: EmployeeCode (for example USA1218-17M), FirstName, LastName"
    out["etl3"] = "Excel sheet 'Case 3 data', columns: EmployeeCode (for example Japan177-3Mo), FirstName, LastName"
    out["etl4"] = ("Excel workbook. JELineItems(JENumber, GLAccountNumber, BusinessUnitID, PreparerID, SourceID, EffectiveDate, JEDescription, Debit, Credit, Amount); "
                   "BusinessUnits(BusinessUnitID, BusinessUnit, BUDescription); ChartOfAccounts(GLAccountName, GLAccountNumber, AccountType, AccountClass); "
                   "PreparerInfo(PreparerName, PreparerID, BusinessUnitID); Source(SourceID, Source)")
    payroll = ("Pipe-delimited files. 2015 payroll, columns A to P: Pay_Date, Payroll_ID, Emp_No, Home_Div, Work_Div, First_Name, Last_Name, Job, Reg_Hrs, OT_Hrs, Reg_Pay, OT_Pay, Futa, Suta, Fica_Medc, Work_Comp. "
               "2016 payroll, columns A to K: Project, Employee_ID, Employee_Number, Employee_Name, Hours, OT_Hours, Gross_Wages, SocSec_Medicare, FUTA, SUTA, Work_Comp. "
               "Job codes: Job_Code, Job_Description. Locations: Employee_Name, Location.")
    out["pay15"] = out["pay16"] = payroll
    return out


def main():
    paths = {
        "songs": "2. SQL part 1/Assignments/cs50 assignment/songs/songs.db",
        "movies": "2. SQL part 1/Assignments/cs50 assignment/movies/movies.db",
        "chinook": "2. SQL part 1/Assignments/pwc assignment/Chinook_Sqlite.sqlite",
        "pcards": "2. SQL part 2/Pcards Assignment/pcards.db",
    }
    for k, v in paths.items():
        CONN[k] = sqlite3.connect(f"file:{MAT / v}?mode=ro", uri=True)
    build_permits()
    build_etl()
    build_payroll()
    build_songs()
    build_movies()
    build_chinook()
    build_pcards()
    reg = build_regression()

    (OUT / "skills.json").write_text(json.dumps(
        [{"id": i, "subject": s, "name": n, "description": desc} for i, s, n, desc in SKILLS], indent=1))
    schemas = describe_datasets()
    (OUT / "datasets.json").write_text(json.dumps(
        {k: {"name": n, "part": p, "schema": schemas[k], "files": [{"name": Path(f).name, "bytes": (MAT / f).stat().st_size} for f in files]}
         for k, (n, p, files) in DATASETS.items()}, indent=1))
    (OUT / "questions.json").write_text(json.dumps(QUESTIONS, indent=1, ensure_ascii=False))
    (OUT / "regression.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False))
    print(f"{len(QUESTIONS)} manipulation questions, {len(reg)} regression exams ({sum(len(e['questions']) for e in reg)} questions)")


if __name__ == "__main__":
    main()
