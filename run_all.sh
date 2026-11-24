#!/usr/bin/env bash
# Re-creates every dataset, chart and table in this portfolio (fixed random seeds, ~1 minute).
set -e
for d in p1_kri_early_warning p2_incident_nlp p3_dependency_network p4_disruption_montecarlo p5_ai_risk_assessment; do
  echo "=== $d ==="; (cd "$d" && python3 *.py)
done
