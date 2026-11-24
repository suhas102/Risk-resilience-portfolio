"""
P1 - Predictive KRI early-warning model
---------------------------------------
Business question: can we warn leadership BEFORE a key risk indicator (KRI)
breaches its tolerance, so action can be taken in time?

KRI used: weekly "late delivery rate" (% of orders delivered after promised slot)
Tolerance (red): > 8%   |   Amber: > 6%

DATA: synthetic (generated here, fixed seed) - patterned on a retailer with
seasonal peaks, carrier capacity, stock availability and weather effects.
No real company data is used.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, roc_auc_score, precision_score, recall_score

rng = np.random.default_rng(42)
OUT = "."
AMBER, RED = 6.0, 8.0

# ---------------------------------------------------------------- 1. data
weeks = pd.date_range("2022-01-03", periods=200, freq="W-MON")
n = len(weeks)
woy = weeks.isocalendar().week.to_numpy()

# seasonality: Black Friday / Christmas peak (wk 46-52) and a smaller summer bump
peak = np.where((woy >= 46) & (woy <= 52), 1.0, 0.0) + 0.3 * ((woy >= 27) & (woy <= 32))
order_volume = 100 + 35 * peak + rng.normal(0, 4, n)                 # index, 100 = normal
carrier_capacity_util = np.clip(0.70 + 0.012 * (order_volume - 100) + rng.normal(0, 0.03, n), 0.5, 1.1)
stock_availability = np.clip(96 - 2.5 * peak + rng.normal(0, 1.2, n), 85, 99)    # %
staff_absence = np.clip(4 + 1.2 * peak + rng.normal(0, 0.8, n), 1, 12)           # %
bad_weather_days = rng.poisson(0.6 + 1.2 * ((woy <= 8) | (woy >= 49)), n)
system_incidents = rng.poisson(0.4 + 0.5 * peak, n)

late_rate = (
    2.5
    + 14.0 * np.maximum(carrier_capacity_util - 0.82, 0)    # non-linear: pain starts near capacity
    + 0.35 * (96 - stock_availability)
    + 0.25 * staff_absence
    + 0.45 * bad_weather_days
    + 0.9 * system_incidents
    + rng.normal(0, 0.45, n)
)
df = pd.DataFrame({
    "week": weeks, "order_volume_idx": order_volume.round(1),
    "carrier_util": carrier_capacity_util.round(3), "stock_avail_pct": stock_availability.round(1),
    "staff_absence_pct": staff_absence.round(1), "bad_weather_days": bad_weather_days,
    "system_incidents": system_incidents, "late_delivery_pct": late_rate.round(2),
})

# ---------------------------------------------------------------- 2. features
# Forecast the KRI 2 weeks ahead using ONLY information available today.
H = 2
feat = df.copy()
for c in ["late_delivery_pct", "carrier_util", "stock_avail_pct", "staff_absence_pct", "order_volume_idx"]:
    feat[f"{c}_lag1"] = feat[c].shift(1)
    feat[f"{c}_chg"] = feat[c] - feat[c].shift(1)
feat["late_ma4"] = feat["late_delivery_pct"].rolling(4).mean()
feat["woy"] = woy
# known-in-advance drivers (planned promotions / calendar) for t+H
feat["future_volume_idx"] = feat["order_volume_idx"].shift(-H)      # trading plan is known ahead
feat["target"] = feat["late_delivery_pct"].shift(-H)
feat = feat.dropna().reset_index(drop=True)

X_cols = [c for c in feat.columns if c not in ("week", "target")]
split = int(len(feat) * 0.75)                      # time-ordered split, no shuffling / leakage
train, test = feat.iloc[:split], feat.iloc[split:]

model = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=0)
model.fit(train[X_cols], train["target"])
pred = model.predict(test[X_cols])

# naive baseline = "next value equals today's value"
naive = test["late_delivery_pct"].to_numpy()
mae_model = mean_absolute_error(test["target"], pred)
mae_naive = mean_absolute_error(test["target"], naive)

# ---------------------------------------------------------------- 3. early-warning evaluation
y_amber = (test["target"] > AMBER).astype(int)
y_red = (test["target"] > RED).astype(int)
def alert_metrics(y, score, thr):
    flag = (score > thr).astype(int)
    return dict(precision=precision_score(y, flag, zero_division=0),
                recall=recall_score(y, flag, zero_division=0),
                auc=roc_auc_score(y, score) if y.nunique() > 1 else float("nan"))
# alert a little below the tolerance so there is lead time (recall > precision for risk use)
m_amber = alert_metrics(y_amber, pred, AMBER - 0.3)
m_red = alert_metrics(y_red, pred, RED - 0.5)
naive_red = alert_metrics(y_red, naive, RED - 0.5)

results = pd.DataFrame({
    "week_forecast_made": test["week"].dt.date, "forecast_for": (test["week"] + pd.Timedelta(weeks=H)).dt.date,
    "actual_late_pct": test["target"].round(2), "predicted_late_pct": pred.round(2),
    "status_predicted": np.where(pred > RED - 0.5, "RED-ALERT", np.where(pred > AMBER - 0.3, "AMBER-ALERT", "green")),
    "status_actual": np.where(test["target"] > RED, "RED", np.where(test["target"] > AMBER, "AMBER", "green")),
})
results.to_csv(f"{OUT}/kri_forecast_results.csv", index=False)
df.to_csv(f"{OUT}/synthetic_ops_data.csv", index=False)

# driver importance (what should owners act on?)
imp = pd.Series(model.feature_importances_, index=X_cols).sort_values(ascending=False).head(8)

# ---------------------------------------------------------------- 4. dashboard
fig, ax = plt.subplots(2, 2, figsize=(14, 8.5))
fig.suptitle("KRI early-warning dashboard - Late delivery rate (synthetic data)", fontsize=14, fontweight="bold")

a = ax[0, 0]
a.plot(test["week"] + pd.Timedelta(weeks=H), test["target"], label="Actual", color="#1f3b73", lw=2)
a.plot(test["week"] + pd.Timedelta(weeks=H), pred, label="Forecast made 2 wks earlier", color="#e07b00", lw=2, ls="--")
a.axhspan(AMBER, RED, color="#ffd54f", alpha=.35); a.axhspan(RED, 20, color="#ef5350", alpha=.25)
a.set_ylim(0, max(12, test["target"].max() + 1)); a.set_ylabel("% late"); a.set_title("Actual vs 2-week-ahead forecast (hold-out period)")
a.legend(loc="upper left"); a.tick_params(axis="x", rotation=30)

a = ax[0, 1]
imp.sort_values().plot.barh(ax=a, color="#1f3b73"); a.set_title("What drives the KRI (feature importance)")

a = ax[1, 0]
a.bar(["Naive\n(today's value)", "Model"], [mae_naive, mae_model], color=["#9e9e9e", "#1f3b73"])
a.set_ylabel("Mean absolute error (pct points)"); a.set_title("Forecast accuracy vs baseline")
for i, v in enumerate([mae_naive, mae_model]): a.text(i, v + .02, f"{v:.2f}", ha="center")

a = ax[1, 1]
a.axis("off")
txt = (f"RED alert (>{RED}%) - model\n   precision {m_red['precision']:.0%}   recall {m_red['recall']:.0%}\n"
       f"RED alert - naive baseline\n   precision {naive_red['precision']:.0%}   recall {naive_red['recall']:.0%}\n\n"
       f"AMBER alert (>{AMBER}%) - model\n   precision {m_amber['precision']:.0%}   recall {m_amber['recall']:.0%}\n\n"
       f"Thresholds: amber {AMBER}%, red {RED}%.\nAlerts trigger 0.3-0.5pt below tolerance\nto buy lead time (favour recall).")
a.text(0.02, 0.95, txt, va="top", fontsize=11, family="monospace")
a.set_title("Alert quality", loc="left")
plt.tight_layout(); plt.savefig(f"{OUT}/kri_dashboard.png", dpi=150); plt.close()

print(f"Test weeks: {len(test)} | RED weeks in test: {int(y_red.sum())} | AMBER+ weeks: {int(y_amber.sum())}")
print(f"MAE model {mae_model:.3f} vs naive {mae_naive:.3f}  ({(1-mae_model/mae_naive):.0%} better)")
print("RED  alert - model:", {k: round(v, 2) for k, v in m_red.items()})
print("RED  alert - naive:", {k: round(v, 2) for k, v in naive_red.items()})
print("AMBER alert - model:", {k: round(v, 2) for k, v in m_amber.items()})
print("Top drivers:\n", imp.round(3).head(5).to_string())
