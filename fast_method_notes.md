# Notes on the quick CRS/Pew-style estimate

This version was prepared quickly, without a hand-coded biographical classification of every member of Congress. Member categories are intended to follow published CRS/Pew-style group membership: African American/Black, Hispanic/Latino, Asian/Pacific Islander, Native American/American Indian, or other. Members not in those reported groups are coded as `other`.

The calculation is population-weighted by congressional district. For each district, the estimated share represented by someone of a different broad race/ethnicity category equals total district population minus the district population in the representative's matching category set, divided by total district population. State estimates aggregate the numerator and denominator across districts, rather than averaging district percentages.

The population categories use ACS table B03002, Hispanic or Latino Origin by Race. Hispanic/Latino residents are placed in a Hispanic any-race bucket. Non-Hispanic Black, Asian/Pacific Islander, and American Indian/Alaska Native residents are placed in their respective single-race buckets. Everyone else, including non-Hispanic White residents and non-Hispanic multiracial residents, is placed in `other`.

Multiracial representatives are treated under an any-match rule. For example, a representative coded `black;hispanic` is treated as same-category for both non-Hispanic Black residents and Hispanic residents. This avoids mechanically labeling one part of a multiracial member's identified background as irrelevant. A stricter alternative would assign each member to only one category; that should be reported as a sensitivity check if the estimate is used in a formal column.

Vacant seats should be excluded from the main estimate because residents of those districts are not currently represented by a voting House member. A separate appendix line may report the population in vacant districts.

Recommended caption:

> Fast estimate using CRS/Pew-style racial and ethnic categories for House members, not a hand-audited biographical coding. Population denominators use ACS 2024 5-year congressional-district data, table B03002, on 119th Congress district boundaries. Multiracial members are counted under an any-match rule. Vacant seats are excluded from the main estimate.
