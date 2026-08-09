from nlp.hours_parser import parse_hours
import json

raw = "Mon - Sun 06:00-23:59; Remarks: Mon: Closes at 3:00 AM, Tue: Closes at 3:00 AM, Wed: Closes at 3:00 AM, Thu: Closes at 3:00 AM, Fri: Closes at 3:00 AM, Sat: Closes at 3:00 AM, Sun: Closes at 3:00 AM;"
print(json.dumps(parse_hours(raw), indent=2))