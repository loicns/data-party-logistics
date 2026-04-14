# Problem Framing

## The business problem

Global shipping moves 90% of world trade. When a vessel arrives at a port, everything downstream depends on that arrival time: factory production schedules, warehouse staffing, truck dispatches, retail shelf restocking.

**The problem:** carrier-provided ETAs are wrong — often by 24 to 72 hours on long routes. And port congestion is discovered reactively, after ships have already piled up at anchorage.

## Who has the pain

| Stakeholder | Their pain |
|---|---|
| Freight forwarders | Can't make accurate delivery commitments to clients |
| Port operators | Can't plan berth allocation or labor scheduling |
| Shippers (goods owners) | Hold excess safety stock because arrival times are unpredictable |
| Commodity traders | Can't read supply signals from vessel movements |

## What success looks like

1. **ETA prediction:** beat the naive baseline (distance / average speed) by 20%+ RMSE on held-out voyages.
2. **Congestion forecast:** AUC above the "yesterday = tomorrow" baseline for 24h port congestion prediction.
3. **Deployed and monitored:** live API, daily drift reports, automated alerts.

## Success metrics

| Metric | Baseline | Target |
|---|---|---|
| ETA RMSE (hours) | naive distance/speed | 20%+ improvement |
| Congestion AUC | persistence model | > 0.70 |
| API p95 latency | — | < 200ms |
| Data freshness | — | AIS < 2h, batch < 24h |

## Constraints

- **Budget:** < $22/month on AWS.
- **Data:** free/public sources only (no proprietary feeds).
- **Timeline:** 8 weeks at 20+ hours/week.
