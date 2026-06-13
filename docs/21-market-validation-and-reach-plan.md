# Market Validation And Reach Plan

_Research date: 2026-06-12_

## Executive Verdict

Data Party Logistics is solving a real problem, but not a broadly unsolved one.

The real problem is that ocean freight is still exposed to volatile port congestion,
route disruption, unreliable arrival timing, and manual exception management. The
market already contains mature visibility products, so DPL should not position itself
as a replacement for project44, FourKites, Shippeo, Vizion, or enterprise TMS/control
tower platforms.

The credible wedge is narrower:

> A transparent, low-cost, port-centric early-warning signal for teams that do not
> already have premium ocean visibility tooling, plus an open research/portfolio-grade
> system that proves real data engineering and ML discipline.

The platform is worth continuing as a focused pilot if it can recruit a few design
partners who currently monitor ports, vessels, and carrier portals manually. It is
not yet proven as a commercial product until those users show repeat usage.

## What DPL Actually Does

DPL predicts whether a covered port is likely to be congested 24 hours ahead using
public/low-cost signals:

- AIS vessel positions from AISStream.
- Port-local weather and wave features.
- Tide data where available.
- Hourly feature generation and a LightGBM congestion classifier.
- Static dashboard output instead of a heavy always-on API.

This is a good technical shape for a low-cost public intelligence layer. The product
claim should stay close to that shape: "port congestion early warning," not
"end-to-end global shipment visibility."

## Evidence That The Problem Is Real

### 1. Maritime trade is economically important and still fragile

UNCTAD says global shipping moves more than 80% of world merchandise trade, while
its 2025 maritime transport release describes fragile growth, rising costs, route
uncertainty, skipped port calls, and longer journeys caused by geopolitical and trade
policy disruption.

Source: [UNCTAD Review of Maritime Transport 2025 press release](https://unctad.org/press-material/stormy-seas-global-shipping-unctad-warns-uncertainty-volatility-and-rising-costs)

### 2. Chokepoint disruption creates downstream port stress

UNCTAD's 2024 maritime review describes the Suez, Red Sea, and Panama Canal as
increasingly vulnerable chokepoints. It reports large drops in Suez/Gulf of Aden
capacity during the Red Sea disruption, rising Cape of Good Hope arrivals, longer
routes, higher ton-mile demand, and higher freight costs. It also explicitly calls
for better monitoring and early-warning systems for ports.

Source: [UNCTAD Review of Maritime Transport 2024](https://unctad.org/publication/review-maritime-transport-2024)

### 3. Ports are still operational bottlenecks

UNCTAD's 2024 report notes that container ship port calls reached record levels in
late 2023 and that Singapore experienced nearly double waiting times amid rerouted
vessels and rising volumes. UNCTAD's 2025 release says ports are under strain from
disruptions, congestion, and longer waiting times.

Sources: [UNCTAD 2024](https://unctad.org/publication/review-maritime-transport-2024),
[UNCTAD 2025](https://unctad.org/press-material/stormy-seas-global-shipping-unctad-warns-uncertainty-volatility-and-rising-costs)

### 4. Predictive visibility is a recognized software category

Gartner's 2026 Real-Time Transportation Visibility Platforms page lists predictive
ETA as a mandatory feature of the category and includes project44, GoComet, Shippeo,
FourKites, Transporeon, and others. That confirms the need is recognized, but also
confirms the market is crowded.

Source: [Gartner Peer Insights: Real-Time Transportation Visibility Platforms](https://www.gartner.com/reviews/market/real-time-transportation-visibility-platforms)

## Practical Cases

| Case | What happened | Why it matters for DPL |
|---|---|---|
| Red Sea / Suez disruption, 2024-2025 | Rerouting, skipped port calls, longer voyages, volatile freight rates, and downstream port strain. | DPL can show abnormal queue buildup and port-level risk even when it cannot solve the geopolitical cause. |
| Singapore congestion, 2024 | UNCTAD reported nearly double waiting times during rerouting and high volume pressure. | DPL's vessel-count and anchorage features match this kind of near-port congestion signal. |
| Baltimore bridge collapse, 2024 | The Fort McHenry channel was fully reopened after about 11 weeks, with large-scale debris removal and rerouted cargo. | DPL would not predict an accident, but a port-status layer could quickly flag abnormal vessel behavior and recovery. |
| Panama Canal drought, 2023-2024 | Transit restrictions and lower draft capacity forced route planning changes and delays. | DPL can become useful when canal disruption creates secondary congestion at destination and transshipment ports. |
| LA/Long Beach congestion, 2021 | Container ships waiting near Southern California ports peaked at high levels during the pandemic supply-chain crunch. | Historical congestion episodes are good backtesting stories and content hooks for public credibility. |

Sources:
[UNCTAD 2024](https://unctad.org/publication/review-maritime-transport-2024),
[UNCTAD 2025](https://unctad.org/press-material/stormy-seas-global-shipping-unctad-warns-uncertainty-volatility-and-rising-costs),
[AP on Baltimore reopening](https://apnews.com/article/51b1fa8e46f58ca93e1fc7b2be7f27b6),
[Guardian on Panama Canal drought](https://www.theguardian.com/business/2023/aug/14/drought-causes-queues-and-delays-for-ships-passing-through-panama-canal),
[Axios on LA/Long Beach backlog](https://www.axios.com/2021/12/07/backlog-container-ship-california-port-holiday)

## Competitive Reality

The broad category is already served.

- project44 offers ocean visibility, carrier/forwarder connections, predictive ETAs,
  port intelligence, terminal milestones, and global container coverage.
- Shippeo offers multimodal visibility, ocean disruption alerts, lane analytics, and
  ETA workflows.
- Vizion offers container tracking APIs and trade visibility products.
- Gartner lists dozens of real-time visibility products.

Sources:
[project44 Ocean Visibility](https://www.project44.com/platform/visibility/ocean/),
[Shippeo Ocean Freight Software](https://www.shippeo.com/platform/multimodal-network/ocean-sea-barge-roro),
[Vizion](https://www.vizionapi.com/),
[Gartner RTTVP reviews](https://www.gartner.com/reviews/market/real-time-transportation-visibility-platforms)

This means DPL should not compete on "we have visibility." It should compete on:

- Transparency: open model card, feature logic, and limitations.
- Cost: free/public dashboard or low-cost alerts.
- Focus: port risk, not full shipment execution.
- Speed to value: no carrier integration project required.
- Honesty: show freshness, confidence, and data gaps clearly.

## Best Initial Users

### Strongest design-partner targets

| Segment | Likely pain | Why DPL may fit |
|---|---|---|
| Small/mid-market freight forwarders | Manual checking across carrier portals, AIS maps, emails, and spreadsheets. | They may lack enterprise visibility tooling but still need exception awareness. |
| Importers/exporters with a few critical lanes | Customer commitments and staffing depend on arrival timing. | A small watchlist and daily risk digest may be enough to start. |
| NVOCC/ocean operations coordinators | Need to prioritize which shipments or ports deserve attention today. | Port-level alerts reduce scan time before vessel-level features exist. |
| Supply-chain analysts and researchers | Need transparent port signals and reproducible data. | DPL's open-source positioning is a feature, not a weakness. |
| Logistics educators / portfolio reviewers | Need proof of real pipeline, deployment, and evaluation. | This is a strong secondary audience but not the commercial buyer. |

### Weak initial targets

- Large shippers already using project44, FourKites, Shippeo, Transporeon, or an
  internal control tower.
- Port authorities that need berth/terminal-level operational truth.
- Users who need legally reliable ETAs or guaranteed SLA-backed data.
- Anyone needing true satellite-grade global AIS coverage.

## Positioning

### One-line positioning

DPL is an open port-congestion early-warning dashboard that shows which major
container ports may degrade tomorrow, why they are flagged, and how fresh the signal is.

### Landing page offer

Get a weekly "Port Congestion Risk Digest" for the ports you care about, built from
live vessel, weather, and tide signals.

### What to avoid saying

- Avoid "real-time global visibility."
- Avoid "replacement for project44/FourKites."
- Avoid "accurate ETA for every shipment."
- Avoid "port truth" if the model only sees AIS-derived proxies.

## How To Get Enough Reach And Potential Users

### Phase 1: Turn the project into a public asset, 1 week

Ship the smallest credible public package:

- A public dashboard for the 10 covered ports.
- A short landing page with one CTA: "Get weekly port risk digest."
- A public model card and coverage page.
- A sample weekly digest archive.
- A feedback form asking for watched ports, workflows, and current tools.

The CTA should collect:

- Role and company type.
- Ports or lanes watched.
- Current tracking method.
- Whether they already use a visibility platform.
- Permission to send a weekly risk digest.

### Phase 2: Direct discovery outreach, 2 weeks

Target 100 highly relevant people, not a broad audience.

Where to find them:

- [NCBFAA](https://www.ncbfaa.org/) member/company ecosystem for US customs brokers,
  freight forwarders, OTIs, NVOCCs, and import/export operators.
- [WCAworld](https://www.wcaworld.com/) directory and event ecosystem for independent
  freight forwarders.
- LinkedIn search for "ocean import coordinator," "export operations manager,"
  "NVOCC operations," "supply chain analyst," "freight forwarding operations," and
  "drayage dispatcher."
- Local logistics associations near covered ports: Rotterdam, Singapore, LA/Long
  Beach, Hamburg, Antwerp, Felixstowe, Dubai, New York/New Jersey, Kaohsiung.
- Freight/logistics newsletters and comment sections where operators discuss actual
  delays: FreightWaves, The Loadstar, Journal of Commerce, Port Technology.

Outreach target mix:

- 40 freight forwarder/NVOCC operators.
- 25 import/export operations people.
- 15 supply-chain analysts.
- 10 drayage/port-adjacent operators.
- 10 logistics educators/recruiters for secondary credibility.

### Phase 3: Offer a manual concierge pilot, 30 days

Do not wait for more features. Offer five design partners:

- A weekly risk digest for their watched ports.
- A one-page explanation of each alert.
- A feedback link: useful, not useful, wrong, already knew it.
- One 20-minute debrief after two weeks.

This validates the workflow before building accounts, watchlists, or paid tiers.

### Phase 4: Convert repeat interest into product features

Build only after users repeat the same demand:

- Email/Slack alerts for watched ports.
- Saved watchlists.
- CSV/API export.
- "Why flagged" reason codes.
- Freshness and confidence panel.
- User feedback logging.
- Optional vessel watchlist only if users ask for it repeatedly.

## Outreach Templates

### Cold email / LinkedIn DM

Subject: Quick question on port congestion monitoring

Hi {{name}},

I'm building an open dashboard that predicts 24-hour congestion risk for major
container ports using live vessel, weather, and tide signals. I am not selling a
visibility platform; I am trying to learn whether small ocean ops teams would use a
simple early-warning digest.

Do you currently check port congestion or vessel arrival risk manually? If yes, I can
send a free weekly risk note for one or two ports you care about and ask for quick
feedback on whether it is useful.

Thanks,
Loic

### LinkedIn post

I am testing a small idea for ocean logistics teams:

Can a transparent, public-data port congestion signal reduce manual checking for
freight forwarders, importers, and analysts?

The first version covers 10 container ports and predicts whether congestion risk is
elevated 24 hours ahead using AIS-derived vessel counts, anchorage signals, weather,
and tide data. It is not a full shipment visibility platform, and it is not trying to
replace enterprise tools.

I am looking for 5 operators or analysts who will receive a free weekly port-risk
digest and tell me whether it matches their real workflow.

Comment or message me with one port you care about.

## Validation Metrics

### Green-light signals

- 30 user conversations completed.
- 10 users describe a recurring manual tracking workflow.
- 5 users agree to receive a weekly digest.
- 3 users open/use the digest for at least 3 consecutive weeks.
- 2 users forward the digest or ask to add a teammate.
- At least 60% of rated alerts are "useful" or "worth watching."
- At least one user says it would save 30 minutes or more per week.

### Red-light signals

- Most target users already have sufficient visibility tools.
- Users find port-level signals interesting but not actionable.
- Alerts are mostly obvious from public news or carrier notices.
- AIS coverage is too sparse for the ports users care about.
- Users ask for shipment/container-level truth before port-level risk has value.

## Product Recommendations

### Keep

- 24-hour port congestion forecast.
- Public dashboard.
- Model card and data dictionary.
- Freshness and confidence labels.
- Low-cost serverless architecture.

### Add next

- Weekly digest generated from current predictions.
- Alert reason codes: anchorage buildup, vessel count spike, low average speed,
  severe wave conditions, stale data, sparse coverage.
- User feedback capture.
- Coverage matrix by port.
- Backtest page using known disruption periods.

### Delay

- Vessel-level ETA product.
- Paid API.
- Team accounts.
- LLM disruption narratives.
- Broad global expansion beyond ports with sufficient coverage.

## Key Risks

### Data coverage

AISStream coverage is primarily coastal, roughly 200 km from much of the world's
coastlines, and AISStream states that the service is beta with no uptime SLA. DPL
must avoid implying global continuous vessel visibility.

Sources:
[AISStream coverage](https://aisstream.io/coverage),
[AISStream documentation](https://aisstream.io/documentation)

### Model confidence

The repo's model card already notes evaluation caveats. The public narrative should
say "early-warning signal" and "risk indicator," not "ground truth."

### Competitive pull

If the buyer already uses project44, Shippeo, FourKites, or an internal control tower,
DPL should not try to displace it. Instead, DPL can be a public benchmark, backup
signal, or analyst-facing layer.

### Actionability

Port-level risk only matters if users can act on it: prioritize calls, warn customers,
adjust staffing, plan drayage, or update internal dashboards. Discovery should measure
actions taken, not just curiosity.

## Final Recommendation

Continue the platform, but treat the next milestone as market validation, not more
infrastructure.

The fastest path to useful reach is:

1. Publish a clear public dashboard and weekly risk digest.
2. Contact 100 targeted operators/analysts.
3. Run a five-user concierge pilot.
4. Measure repeat use and alert usefulness.
5. Build watchlists and alerts only after repeat demand is proven.

If this works, DPL becomes a focused port-intelligence product. If it does not, it
still remains a strong open-source ML/data engineering portfolio project with honest
market framing.
