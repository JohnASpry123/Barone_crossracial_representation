# Fast CRS/Pew-style cross-racial representation estimate

This is the rapid version requested for a Michael Barone-style column note. It intentionally avoids a full hand-coded biographical audit of every House member.

## What this package does

It calculates, for each U.S. House district, the share of residents whose simplified race/Hispanic-origin bucket differs from the representative's CRS/Pew-style category:

\[
\text{different-race share}_{s}=\frac{\sum_i(T_i-S_i)}{\sum_i T_i}
\]

where \(T_i\) is total district population and \(S_i\) is the district population in the representative's category set.

## Fast member coding rule

Use CRS/Pew-style categories:

- `black` = African American / Black member
- `hispanic` = Hispanic or Latino member
- `api` = Asian American, South Asian American, Native Hawaiian, or Pacific Islander member
- `native` = Native American / American Indian member
- `other` = everyone else

Multiracial members may have multiple categories, for example `black;hispanic`. The main estimate uses an **any-match** rule. If a resident falls into any one of the representative's reported categories, that resident is counted as represented by someone in the same broad category.

## Census population buckets

The script uses ACS table B03002, Hispanic or Latino Origin by Race:

- `hispanic_any`: Hispanic or Latino, any race = `B03002_012E`
- `nh_black`: Not Hispanic or Latino, Black or African American alone = `B03002_004E`
- `nh_asian_pi`: Not Hispanic or Latino, Asian alone plus Native Hawaiian / Pacific Islander alone = `B03002_006E + B03002_007E`
- `nh_aian`: Not Hispanic or Latino, American Indian / Alaska Native alone = `B03002_005E`
- `other`: total minus the four buckets above

This is a pragmatic simplification. It does not attempt to allocate non-Hispanic multiracial residents to multiple categories.

## Files

- `compute_barone_fast.py`: calculation script
- `house_members_template.csv`: input schema for current House members by district
- `member_categories_fast_template.csv`: input schema for fast CRS/Pew-style category coding
- `census_b03002_cd119_template.csv`: normalized Census input schema, if not fetching directly from Census API
- `fast_method_notes.md`: memo notes to paste into the work product

## Run

```bash
python compute_barone_fast.py \
  --members house_members_current.csv \
  --categories member_categories_fast.csv \
  --fetch-census \
  --outdir out_barone_fast
```

Or, if the Census API is blocked, download/create the normalized Census file and run:

```bash
python compute_barone_fast.py \
  --members house_members_current.csv \
  --categories member_categories_fast.csv \
  --census census_b03002_cd119.csv \
  --outdir out_barone_fast
```

Outputs:

- `district_results_fast.csv`
- `state_results_fast.csv`
- `national_results_fast.csv`
- `method_notes_fast.txt`

## Important note

This is not a hand-audited final table. It is a fast CRS/Pew category estimate. The written work product should say so.
