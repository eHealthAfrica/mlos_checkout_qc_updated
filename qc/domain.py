"""Domain constants relocated verbatim from app.py, per D-07: every function this phase moves
references at least one of these symbols, so leaving them in app.py would require qc/ to import
app, which imports the UI framework and makes ENGINE-05 unachievable.

The one deliberate change (D-10's first level): ``YN_NA_COLS`` becomes a tuple in the order
highrisk, slums, densely_populated, hard2reach, border, nomadic, riverine, fulani — matching the
convention this repository already set for itself in the adjacent ``FLAG_COLS`` list, per D-11.
A set literal at that position was the anomaly; a registry-declared order (the re-sort helper
qc/__init__.py exposes) is the load-bearing backstop, per D-12.
"""

import re

VALID_DAY   = {"1","1_2","1_2_3","1_2_3_4","2","2_3","2_3_4","3","3_4","4","NA"}
VALID_YN_NA = {"Y","N","NA"}
VALID_YN    = {"Y","N"}
# Absence sentinel tokens (D-04, D-05): a value is absent when it is pandas NA/None/NaN, the
# empty string, whitespace-only, or one of these five case-insensitive tokens. Matching is
# case-insensitive against a stripped, lower-cased projection of the cell — except the exact
# literal "NA", which is exempted case-sensitively in qc.predicates.vec_is_absent, because "NA"
# is simultaneously a valid flag value in every FLAG_COLS column and Nasarawa's state_code.
# Lowercase "na" is not a member of this set and is therefore not swept up as absent either — it
# survives for a different reason than "NA" does (it is simply not one of these five tokens,
# distinct from "nan"), not because of the exemption.
ABSENCE_SENTINELS = frozenset({"null", "none", "n/a", "nan", "-"})
VALID_ACC   = {"Fully Accessible","Partially Accessible","Inaccessible"}
VALID_HAB   = {"Abandoned","Migrated","Inhabited","Partially Inhabited"}
UUID_RE     = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
EDITOR_RE   = re.compile(r'^[a-z]+\.[a-z]+$')
# Nullable MLoS fields (can be null — not subject to null checks):
# primarysettlement_name, alternate_name, reasons_for_inaccessibility
YN_NA_COLS = ("highrisk", "slums", "densely_populated", "hard2reach",
              "border", "nomadic", "riverine", "fulani")

MLOS_REQUIRED_COLS = {
    "state_code", "state_name", "lga_code", "lga_name", "ward_name", "ward_code",
    "takeoffpoint", "takeoffpoint_code", "settlement_name", "primarysettlement_name",
    "alternate_name", "latitude", "longitude", "security_compromised",
    "accessibility_status", "reasons_for_inaccessibility", "habitational_status",
    "set_population", "set_target", "number_of_household", "noncompliant_household",
    "team_code", "day_of_activity", "urban", "rural", "highrisk", "slums",
    "densely_populated", "hard2reach", "border", "nomadic", "scattered",
    "riverine", "fulani", "timestamp", "source", "last_updated", "editor",
    "validation_status", "master_id", "mlos_id", "eha_guid", "settlementarea_globalid",
}
TAKEOFF_REQUIRED_COLS = {"name", "code", "wardcode", "globalid"}

FLAG_COLS = [
    "highrisk", "slums", "densely_populated", "hard2reach",
    "border", "nomadic", "scattered", "riverine", "fulani",
]
