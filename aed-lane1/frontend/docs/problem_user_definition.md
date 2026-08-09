# Problem & User Definition

## Intended User

The primary user is a **member of the public in Greater London** who needs to find an open pharmacy nearby — for example, to collect a prescription, buy urgent over-the-counter medication, or seek pharmacist advice.

Secondary users include **carers or family members** searching on behalf of someone else.

## The Decision This Tool Supports

The user must answer: **"Which pharmacy should I walk to right now?"**

This is a time-sensitive decision. The user wants:
1. A pharmacy that is **open** (not just listed as existing)
2. That is **physically reachable** in a reasonable walk (≤15–20 min)
3. That can **fulfil their need** (the right type of pharmacy)

## What This Prototype Does

- Accepts a free-text location query (postcode, address, or area name)
- Sends it to an AI ranking backend that scores and ranks nearby pharmacies
- Displays ranked results with:
  - Distance and estimated walk time
  - Snap-quality label (how precisely the location was matched)
  - Hours confidence badge (when available)
  - Registry anomaly flags (when available)
  - A walking route on an OpenStreetMap map
- Gracefully abstains (shows a designed "no result" screen) when the system cannot produce a trustworthy answer

## Prototype Limits

| Limit | Detail |
|---|---|
| Geographic scope | Greater London only |
| Data freshness | Pharmacy registry data may be stale; hours confidence score indicates this |
| Pharmacy types | General community pharmacies; does not cover specialist dispensing units |
| Real-time data | No live "is this pharmacy open right now" check; relies on registered opening hours |
| Accessibility info | Not included in this prototype |
| Wheelchair / transport routing | Walking routes only |

## Success Criteria

The prototype is successful if:
1. A user can input a location and receive a ranked list within 2 seconds
2. The top result is an open pharmacy within 1 km
3. The safety banner is visible on every page load
4. The system abstains (rather than guessing) when confidence is insufficient
5. A walking route is shown for the top-ranked result

## What We Would Improve

1. Real-time opening hours verification (call/scrape pharmacy websites)
2. NHS API integration for live dispensing capability data
3. Expand coverage beyond Greater London
4. Accessibility routing (step-free, transport links)
5. Medication availability checking
