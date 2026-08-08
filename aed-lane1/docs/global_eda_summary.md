# Global EDA — SCDF Public Access AEDs
Run against: data/scdf_aed_frozen.geojson (see checksum in data/scdf_aed_frozen.sha256)

## Headline numbers
- Total records: 9,644
- OPERATING_HOURS missing: 7, blank: 0
- Always-open pattern (00:00-23:59): 6,573 records
- Records with multiple hour segments: 705
- UNIT_NUMBER missing: 9,301
- BUILDING_NAME missing: 5,265
- FLOOR_LEVEL missing: 205

## Ambiguous-language frequency (AED_LOCATION_DESCRIPTION)
- "near": 708
- "beside": 206
- "opposite": 48
- "level": 9,261
- "vicinity": 0
- "around": 0
- "behind": 28

## Key finding — informs nlp/location_flagger.py design
"level" appears in the vast majority of records (9,261 / 9,644) because floor descriptions
naturally contain it (e.g. "Level 3"). It is NOT a genuine ambiguity signal and must not be
treated as one. Real ambiguity signals are relational terms: "near", "beside", "opposite", "behind".
