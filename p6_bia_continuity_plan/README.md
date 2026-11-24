# P6 - Business impact analysis and continuity plan (same-day delivery)

**Document:** [BIA_and_Continuity_Plan_Same_Day_Delivery.pdf](BIA_and_Continuity_Plan_Same_Day_Delivery.pdf) (7 pages)

**Problem.** A dependency map shows where a process is fragile, but leaders need a plan: how bad is a disruption after 1, 4, 8
and 24 hours, how fast must each step recover, and what do we do while it recovers?

**What the document covers.**
1. Scope and method for a business impact analysis (BIA)
2. Impact over time by process step, with maximum tolerable period of disruption (MTPD), recovery time objective (RTO) and minimum service level
3. Impact by area: customer, colleague, financial, regulatory and reputational
4. Dependencies and single points of failure (taken from [P3](../p3_dependency_network/README.md))
5. Recovery time conflicts, where something recovers more slowly than the step that relies on it
6. Workarounds and recovery strategies for seven disruption scenarios
7. Invocation triggers, roles and communication rhythm
8. Recovery timeline from the first hour to the post-incident review
9. Six owned gaps and actions
10. Testing and maintenance plan with key risk indicators

**Key findings.**
- Order capture and payment are the most time-critical steps (1 hour RTO, severe impact within 4 hours at peak trading).
- Four recovery time conflicts, for example order management (2 hours) supports steps that must recover in 1 hour, and the only same-day site (8 hours) supports pick and pack (4 hours).
- Highest-priority actions: wire up the unused DC South as a tested fallback, test a second cloud region and payment route, and resolve the conflicting RTOs.

**Limitations.** Fictional retailer. Impact ratings, RTOs, MTPDs and the GBP 12m peak-day revenue basis are illustrative assumptions.
A real BIA needs workshops with process owners and sign-off from the accountable executive.
