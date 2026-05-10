# Next Week Demo Calendar

## Purpose

This calendar is for a one-week push to create a credible 3-port demo that can be used in interviews with 5-10 logistics users.

The goal is not to prove product-market fit. The goal is to become credible enough to have better conversations.

## Recommendation

Continue building, but narrow the scope hard.

For next week, build a demo around:

- **NLRTM:** Rotterdam
- **SGSIN:** Singapore
- **USLAX:** Los Angeles

These are a good first set because they are already represented in the warehouse seed data, they are globally recognizable, and they give the demo geographic variety. USLAX also has NOAA tide support in the current codebase.

## What "Production Ready" Means For Next Week

For this project stage, "production ready" should mean:

- the ingestion and transformation path can run repeatedly
- the demo is backed by real recent data where available
- every metric shows freshness and source status
- every prediction-like output is clearly labeled as model, baseline, or fallback
- failures degrade visibly instead of silently
- the dashboard can be shown without apologizing for broken wiring

It should not mean:

- global coverage
- carrier-grade ETA accuracy
- satellite AIS equivalence
- a polished SaaS product
- a trained ML system with proven lift

## Strategic Bet

This is worth doing if the demo is used as a learning instrument.

It is not worth doing if the next week turns into building every planned platform component. The best move is to build just enough real product surface to ask sharper questions:

- Would this change your workflow?
- What do you already use?
- What would make this untrustworthy?
- Which alert would cause you to act?
- What data source do you currently trust most?

## Calendar

### Monday, May 11, 2026: Scope Lock And Data Reality

**Primary outcome:** the demo scope is fixed and honest.

Implementation:

- Lock demo ports to `NLRTM`, `SGSIN`, and `USLAX`.
- Update the dashboard port list to match those three ports.
- Add a visible data freshness/status panel per port.
- Create a small source coverage matrix for AIS, weather, NOAA tides, and warehouse freshness.
- Add a "fallback mode" label for any non-ML output.

Decision rule:

- If a metric is not backed by real data, label it as demo/sample or remove it.

### Tuesday, May 12, 2026: Real Data Path For The Demo

**Primary outcome:** one command can refresh the demo dataset.

Implementation:

- Run or stabilize the batch ingestion flow for the three selected ports.
- Confirm raw S3 output exists for weather, NOAA where available, and AIS snapshots where credentials allow.
- Run the S3-to-Postgres loader for demo-relevant sources.
- Run `dbt build` and confirm the staging and mart models build cleanly.
- Write a short runbook command block for refreshing the demo.

Decision rule:

- Prefer a boring reliable refresh path over a clever incomplete pipeline.

### Wednesday, May 13, 2026: Baseline Intelligence

**Primary outcome:** the dashboard has useful signals even before ML.

Implementation:

- Compute simple congestion baselines from existing mart fields:
  - vessels near port
  - vessels at anchor
  - average speed in zone
  - congestion score
- Add a rules-based risk label:
  - low
  - medium
  - high
  - unknown
- Add reason codes such as:
  - anchorage buildup
  - low average speed
  - stale AIS
  - severe waves
  - missing source

Decision rule:

- Do not train a model this week unless the baseline path is already working.

### Thursday, May 14, 2026: Demo Dashboard Wiring

**Primary outcome:** the dashboard tells the truth from real or clearly marked fallback data.

Implementation:

- Replace mock dashboard data for the three demo ports with a generated JSON artifact from the warehouse or a local demo export.
- Show freshness timestamps on every port.
- Show source status:
  - fresh
  - stale
  - unavailable
  - demo sample
- Add a small "why flagged" panel.
- Keep the UI operational and dense; avoid making it a marketing page.

Decision rule:

- If a user asks "where did this number come from?", the answer should be visible on the screen or one click away.

### Friday, May 15, 2026: Interview Pack

**Primary outcome:** the product can be used to learn from real people.

Implementation:

- Write a 20-minute interview script.
- Prepare 5 concrete demo scenarios:
  - one normal port state
  - one high congestion state
  - one stale data state
  - one missing prediction fallback
  - one uncertainty/confidence example
- Create a feedback capture sheet with:
  - current tools used
  - pain severity
  - trust blockers
  - willingness to try
  - must-have data sources
  - willingness to pay or sponsor pilot
- Record the exact claims the demo is allowed to make.

Decision rule:

- The interview should test user value, not ask users to admire the engineering.

### Saturday, May 16, 2026: Dry Run And Fixes

**Primary outcome:** the demo survives a full rehearsal.

Implementation:

- Run the refresh flow from scratch.
- Open the dashboard as a first-time user would.
- Check every number, status label, and timestamp.
- Remove any unsupported claim.
- Practice the interview flow twice.

Decision rule:

- If something is impressive but confusing, simplify it.

### Sunday, May 17, 2026: Go / No-Go For Interviews

**Primary outcome:** decide whether the demo is ready to show.

Go criteria:

- dashboard loads cleanly
- all three ports appear
- freshness is visible
- missing data is labeled honestly
- at least one real baseline signal is shown
- interview script is ready
- feedback capture sheet is ready

No-go criteria:

- dashboard still relies mostly on unlabeled mock data
- claims imply global or carrier-grade visibility
- refresh path is fragile and undocumented
- the demo cannot explain its own numbers

## Interview Script

### Opening

"I am exploring whether smaller logistics teams need a lightweight port and vessel risk view. This is an early demo, not a finished product. I am trying to learn whether this would actually help your workflow."

### Questions

- What tools do you currently use to track ocean shipments or port delays?
- Which parts are still manual?
- How often do ETA or port delay surprises affect your work?
- Do you already have a vendor or internal system that solves this well?
- Looking at this demo, what would you trust?
- Looking at this demo, what would you distrust?
- Which signal would make you take action?
- Which data source would be mandatory before you could use this?
- Would this be useful if it only covered selected ports?
- What would make this worth using weekly?

### Closing

"Based on what you saw, should I keep building this, narrow it, or stop?"

## End-Of-Week Artifact Checklist

- 3-port demo dashboard
- refresh runbook
- source coverage matrix
- baseline congestion/risk output
- fallback and freshness labels
- interview script
- feedback capture sheet
- list of claims the demo is allowed to make

## Honest Success Definition

The week is successful if you can have better conversations with logistics users.

The week is not successful just because the software looks more complete.

At this stage, credibility comes from three things:

- knowing what is real
- showing the useful part clearly
- being honest about what is still missing
