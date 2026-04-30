#!/usr/bin/env python3
"""
Fast cross-racial representation estimate for U.S. House districts.

Purpose
-------
Implements the rapid version requested by John Spry: classify each House
member into CRS/Pew-style race/ethnicity groups (African American, Hispanic/
Latino, Asian/Pacific Islander, Native American, or Other) without a full
hand-coded biography audit, merge those categories to congressional-district
race/Hispanic-origin data, and compute the share of residents represented by a
member whose CRS/Pew-style category does not match their own simplified bucket.

The script is deliberately transparent and conservative: it writes district,
state, and national outputs and a method note that can accompany a Barone-style
column or memo. It does not infer a member's race from a name or photograph.

Inputs
------
1. house_members.csv, one row per 50-state House district. Required columns:
   state_fips,district,member,vacant
   - state_fips: two-digit FIPS string, e.g. 27
   - district: two-digit congressional district code; at-large districts usually 00
   - member: member name, used only for audit display
   - vacant: TRUE/FALSE, 1/0, or yes/no

2. member_categories_fast.csv, one row per district or member. Required columns:
   state_fips,district,member,rep_categories,source_note
   - rep_categories: semicolon-separated subset of
       black;hispanic;api;native;other
     Examples: "black", "hispanic", "black;hispanic", "other".
   - For the rapid version, assign categories using published CRS/Pew category
     membership rather than a fresh hand audit. Everyone not in those reported
     groups should be "other".

3. Optional: census_b03002_cd119.csv, district demographic file with columns:
   state_fips,district,total_pop,hispanic_any,nh_black,nh_asian_pi,nh_aian,other

   If omitted and --fetch-census is supplied, the script tries to fetch ACS
   2024 5-year B03002 district data via the Census API.

Outputs
-------
- district_results_fast.csv
- state_results_fast.csv
- national_results_fast.csv
- method_notes_fast.txt

Important caveat
----------------
This is a fast estimate. It collapses race/ethnicity into a small number of
CRS/Pew-style buckets and should be labeled accordingly. A publication-grade
version should replace member_categories_fast.csv with a hand-audited member
crosswalk and report sensitivity checks for multiracial members.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Set

import pandas as pd

CATEGORIES = {"black", "hispanic", "api", "native", "other"}
CENSUS_API = "https://api.census.gov/data/2024/acs/acs5"
CENSUS_VARS = [
    "NAME",
    "B03002_001E",  # total population
    "B03002_004E",  # not Hispanic: Black alone
    "B03002_005E",  # not Hispanic: American Indian / Alaska Native alone
    "B03002_006E",  # not Hispanic: Asian alone
    "B03002_007E",  # not Hispanic: Native Hawaiian / Pacific Islander alone
    "B03002_012E",  # Hispanic/Latino, any race
]

STATE_ABBR_TO_FIPS = {
    "AL":"01","AK":"02","AZ":"04","AR":"05","CA":"06","CO":"08","CT":"09","DE":"10",
    "FL":"12","GA":"13","HI":"15","ID":"16","IL":"17","IN":"18","IA":"19","KS":"20",
    "KY":"21","LA":"22","ME":"23","MD":"24","MA":"25","MI":"26","MN":"27","MS":"28",
    "MO":"29","MT":"30","NE":"31","NV":"32","NH":"33","NJ":"34","NM":"35","NY":"36",
    "NC":"37","ND":"38","OH":"39","OK":"40","OR":"41","PA":"42","RI":"44","SC":"45",
    "SD":"46","TN":"47","TX":"48","UT":"49","VT":"50","VA":"51","WA":"53","WV":"54",
    "WI":"55","WY":"56","DC":"11","PR":"72"
}

STATE_FIPS_TO_ABBR = {v:k for k, v in STATE_ABBR_TO_FIPS.items()}


def z2(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(2)


def truthy(x) -> bool:
    return str(x).strip().lower() in {"1", "true", "t", "yes", "y", "vacant"}


def parse_categories(s: str) -> Set[str]:
    if pd.isna(s) or str(s).strip() == "":
        return {"other"}
    cats = {c.strip().lower() for c in str(s).replace(",", ";").split(";") if c.strip()}
    bad = cats - CATEGORIES
    if bad:
        raise ValueError(f"Unknown rep_categories value(s): {sorted(bad)} in {s!r}")
    if "other" in cats and len(cats) > 1:
        raise ValueError(f"Do not mix 'other' with named categories: {s!r}")
    return cats or {"other"}


def fetch_census(path: Path) -> pd.DataFrame:
    import requests

    params = {
        "get": ",".join(CENSUS_VARS),
        "for": "congressional district:*",
        "in": "state:*",
    }
    r = requests.get(CENSUS_API, params=params, timeout=60)
    r.raise_for_status()
    rows = r.json()
    header, data = rows[0], rows[1:]
    raw = pd.DataFrame(data, columns=header)
    raw.to_csv(path.with_suffix(".raw_api.csv"), index=False)
    out = normalize_census_api(raw)
    out.to_csv(path, index=False)
    return out


def normalize_census_api(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["state_fips"] = df["state"].map(z2)
    df["district"] = df["congressional district"].map(z2)
    for col in ["B03002_001E", "B03002_004E", "B03002_005E", "B03002_006E", "B03002_007E", "B03002_012E"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    out = pd.DataFrame({
        "state_fips": df["state_fips"],
        "state": df["state_fips"].map(STATE_FIPS_TO_ABBR).fillna(df["state_fips"]),
        "district": df["district"],
        "district_name": df["NAME"],
        "total_pop": df["B03002_001E"],
        "hispanic_any": df["B03002_012E"],
        "nh_black": df["B03002_004E"],
        "nh_asian_pi": df["B03002_006E"] + df["B03002_007E"],
        "nh_aian": df["B03002_005E"],
    })
    out["other"] = out["total_pop"] - out[["hispanic_any", "nh_black", "nh_asian_pi", "nh_aian"]].sum(axis=1)
    return out


def load_census(path: Path | None, fetch: bool, outdir: Path) -> pd.DataFrame:
    if path and path.exists():
        df = pd.read_csv(path, dtype={"state_fips": str, "district": str})
    elif fetch:
        path = outdir / "census_b03002_cd119.csv"
        df = fetch_census(path)
    else:
        raise SystemExit("Provide --census census_b03002_cd119.csv or use --fetch-census.")
    df["state_fips"] = df["state_fips"].map(z2)
    df["district"] = df["district"].map(z2)
    need = {"state_fips", "district", "total_pop", "hispanic_any", "nh_black", "nh_asian_pi", "nh_aian", "other"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"Census file missing columns: {sorted(missing)}")
    for c in ["total_pop", "hispanic_any", "nh_black", "nh_asian_pi", "nh_aian", "other"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def load_members(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"state_fips": str, "district": str})
    need = {"state_fips", "district", "member", "vacant"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"Members file missing columns: {sorted(missing)}")
    df["state_fips"] = df["state_fips"].map(z2)
    df["district"] = df["district"].map(z2)
    df["vacant"] = df["vacant"].map(truthy)
    return df


def load_categories(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"state_fips": str, "district": str})
    need = {"state_fips", "district", "member", "rep_categories", "source_note"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"Category file missing columns: {sorted(missing)}")
    df["state_fips"] = df["state_fips"].map(z2)
    df["district"] = df["district"].map(z2)
    df["rep_categories"] = df["rep_categories"].fillna("other")
    df["category_set"] = df["rep_categories"].map(parse_categories)
    return df


def same_population(row) -> float:
    cats = row["category_set"]
    same = 0.0
    if "hispanic" in cats:
        same += row["hispanic_any"]
    if "black" in cats:
        same += row["nh_black"]
    if "api" in cats:
        same += row["nh_asian_pi"]
    if "native" in cats:
        same += row["nh_aian"]
    if "other" in cats:
        same += row["other"]
    return min(same, row["total_pop"])


def compute(census: pd.DataFrame, members: pd.DataFrame, cats: pd.DataFrame, exclude_vacancies: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Merge members + categories using district. Member names are retained for audit but not used as keys.
    m = members.merge(
        cats[["state_fips", "district", "rep_categories", "source_note", "category_set"]],
        on=["state_fips", "district"], how="left"
    )
    m["rep_categories"] = m["rep_categories"].fillna("other")
    m["source_note"] = m["source_note"].fillna("No CRS/Pew named-category row supplied; defaulted to other.")
    m["category_set"] = m["category_set"].apply(lambda x: x if isinstance(x, set) else {"other"})

    d = census.merge(m, on=["state_fips", "district"], how="left", validate="one_to_one")
    missing = d["member"].isna().sum()
    if missing:
        raise SystemExit(f"{missing} Census districts did not match a member row. Check at-large district coding, FIPS, and vacancies.")

    if exclude_vacancies:
        d = d.loc[~d["vacant"]].copy()

    d["same_race_fast_pop"] = d.apply(same_population, axis=1)
    d["different_race_fast_pop"] = d["total_pop"] - d["same_race_fast_pop"]
    d["pct_different_race_fast"] = d["different_race_fast_pop"] / d["total_pop"]

    group_cols = ["state_fips"]
    if "state" in d.columns:
        group_cols.append("state")
    state = d.groupby(group_cols, as_index=False).agg(
        total_pop=("total_pop", "sum"),
        same_race_fast_pop=("same_race_fast_pop", "sum"),
        different_race_fast_pop=("different_race_fast_pop", "sum"),
        districts=("district", "count")
    )
    state["pct_different_race_fast"] = state["different_race_fast_pop"] / state["total_pop"]
    nat = pd.DataFrame({
        "scope": ["United States, 50-state House districts"],
        "total_pop": [d["total_pop"].sum()],
        "same_race_fast_pop": [d["same_race_fast_pop"].sum()],
        "different_race_fast_pop": [d["different_race_fast_pop"].sum()],
        "districts": [len(d)],
    })
    nat["pct_different_race_fast"] = nat["different_race_fast_pop"] / nat["total_pop"]
    return d, state, nat


def write_method_note(path: Path, exclude_vacancies: bool) -> None:
    txt = f"""Fast CRS/Pew-style cross-racial representation estimate

Definition: For each House district, different-race population equals total district population minus the population in the district's simplified Census race/Hispanic-origin bucket matching the representative's CRS/Pew-style category set.

Population buckets:
- hispanic: Hispanic or Latino, any race (ACS B03002_012E)
- black: Not Hispanic or Latino, Black or African American alone (ACS B03002_004E)
- api: Not Hispanic or Latino, Asian alone plus Native Hawaiian / Other Pacific Islander alone (ACS B03002_006E + B03002_007E)
- native: Not Hispanic or Latino, American Indian / Alaska Native alone (ACS B03002_005E)
- other: all remaining residents, including non-Hispanic White, non-Hispanic some other race, and non-Hispanic two or more races

Representative coding: This fast version uses externally reported CRS/Pew-style membership in African American, Hispanic/Latino, Asian/Pacific Islander, and Native American/American Indian groups. Representatives not in those reported groups are coded other. Multiracial representatives may receive multiple categories; the main estimate uses an any-match rule. No attempt is made to infer categories from names, photos, surnames, or district composition.

Vacancies excluded from main denominator: {exclude_vacancies}.

Caveat for publication: This is not a hand-audited biographical coding of every member. It is suitable for a quick column note only if labeled as a rapid CRS/Pew-style estimate. A publication-grade table should audit each member, resolve vacancies and special elections as of the column date, and include sensitivity checks for multiracial and Hispanic-origin coding.
"""
    path.write_text(txt, encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--members", required=True, type=Path, help="CSV of current 50-state House districts and members")
    ap.add_argument("--categories", required=True, type=Path, help="CSV of fast CRS/Pew-style member categories")
    ap.add_argument("--census", type=Path, help="Optional normalized Census B03002 CD119 CSV")
    ap.add_argument("--fetch-census", action="store_true", help="Fetch ACS 2024 5-year B03002 district data from Census API")
    ap.add_argument("--outdir", type=Path, default=Path("barone_fast_outputs"))
    ap.add_argument("--include-vacancies", action="store_true", help="Include vacancies in denominator; default excludes them")
    args = ap.parse_args(argv)

    args.outdir.mkdir(parents=True, exist_ok=True)
    census = load_census(args.census, args.fetch_census, args.outdir)
    members = load_members(args.members)
    cats = load_categories(args.categories)
    d, state, nat = compute(census, members, cats, exclude_vacancies=not args.include_vacancies)

    d.to_csv(args.outdir / "district_results_fast.csv", index=False)
    state.to_csv(args.outdir / "state_results_fast.csv", index=False)
    nat.to_csv(args.outdir / "national_results_fast.csv", index=False)
    write_method_note(args.outdir / "method_notes_fast.txt", exclude_vacancies=not args.include_vacancies)

    print(json.dumps({
        "districts": int(nat.loc[0, "districts"]),
        "total_pop": float(nat.loc[0, "total_pop"]),
        "pct_different_race_fast": float(nat.loc[0, "pct_different_race_fast"]),
        "outputs": str(args.outdir),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
