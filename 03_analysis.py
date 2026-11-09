"""
Langkah 3 - Analisis performa lintas platform: KPI, tren, funnel, kreatif, uji statistik, rekomendasi.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

df = pd.read_csv("data/clean/ads_unified.csv", parse_dates=["date", "week"])
CH = "reports/charts/"
COLORS = {"Meta": "#1877F2", "TikTok": "#111111"}


def kpis(g):
    """Hitung KPI standar dari kolom mentah (jumlahkan dulu, baru bagi - bukan rata-rata rasio)."""
    s = g[["spend", "impressions", "reach", "clicks", "add_to_cart", "purchases", "revenue"]].sum()
    return pd.Series({
        "spend": s.spend, "revenue": s.revenue, "purchases": s.purchases,
        "impressions": s.impressions, "clicks": s.clicks,
        "CPM": s.spend / s.impressions * 1000,
        "CTR_%": s.clicks / s.impressions * 100,
        "CPC": s.spend / s.clicks,
        "ATC_rate_%": s.add_to_cart / s.clicks * 100,
        "CVR_%": s.purchases / s.clicks * 100,
        "CPA": s.spend / s.purchases if s.purchases else np.nan,
        "ROAS": s.revenue / s.spend,
        "AOV": s.revenue / s.purchases if s.purchases else np.nan,
    })

out = []

# 1) Ringkasan per platform
by_platform = df.groupby("platform").apply(kpis, include_groups=False).round(2)
by_platform.to_csv("reports/kpi_by_platform.csv")
out.append("## 1. KPI per platform\n" + by_platform[["spend", "revenue", "CPM", "CTR_%", "CPC", "CVR_%", "CPA", "ROAS"]].to_string())

# 2) Platform x tipe campaign
by_pc = df.groupby(["platform", "campaign_type"]).apply(kpis, include_groups=False).round(2)
by_pc.to_csv("reports/kpi_by_platform_campaign_type.csv")
out.append("\n## 2. Platform x tipe campaign\n" + by_pc[["spend", "CTR_%", "CVR_%", "CPA", "ROAS"]].to_string())

# 3) Platform x format kreatif
by_cr = df.groupby(["platform", "creative_format"]).apply(kpis, include_groups=False).round(2)
by_cr.to_csv("reports/kpi_by_platform_creative.csv")
out.append("\n## 3. Platform x format kreatif\n" + by_cr[["spend", "CTR_%", "CVR_%", "CPA", "ROAS"]].to_string())

# 4) Tren mingguan
weekly = df.groupby(["week", "platform"]).apply(kpis, include_groups=False).reset_index()
weekly.to_csv("reports/kpi_weekly.csv", index=False)

# 5) Uji statistik: ROAS harian Meta vs TikTok (Welch t-test)
daily = df.groupby(["date", "platform"]).apply(kpis, include_groups=False).reset_index()
m = daily.loc[daily.platform == "Meta", "ROAS"]
t = daily.loc[daily.platform == "TikTok", "ROAS"]
tstat, p = stats.ttest_ind(m, t, equal_var=False)
out.append(f"\n## 4. Uji Welch t-test ROAS harian\nMeta rata-rata {m.mean():.2f} vs TikTok {t.mean():.2f} | t={tstat:.2f}, p={p:.4g} "
           f"-> {'berbeda signifikan' if p < 0.05 else 'tidak berbeda signifikan'} (alpha 0.05)")

# 6) Dampak event (9.9 dan 10.10) vs hari biasa
df["is_event"] = df["date"].isin(pd.to_datetime(["2026-09-09", "2026-10-10"]))
ev = df.groupby(["platform", "is_event"]).apply(kpis, include_groups=False).round(2)[["CPM", "CVR_%", "CPA", "ROAS"]]
out.append("\n## 5. Hari event (9.9 & 10.10) vs hari biasa\n" + ev.to_string())

# 7) Creative fatigue: CTR berdasarkan umur ad
first = df.groupby(["platform", "ad_group", "campaign", "ad"])["date"].transform("min")
df["ad_age_days"] = (df["date"] - first).dt.days
df["age_bucket"] = pd.cut(df["ad_age_days"], [-1, 13, 27, 41, 90], labels=["0-13", "14-27", "28-41", "42+"])
fat = df.groupby(["platform", "age_bucket"], observed=True).apply(kpis, include_groups=False).round(3)[["CTR_%", "CPA", "ROAS"]]
out.append("\n## 6. Creative fatigue (umur ad)\n" + fat.to_string())

# 8) Rekomendasi realokasi budget: ROAS per (platform, campaign_type, creative)
combo = df.groupby(["platform", "campaign_type", "creative_format"]).apply(kpis, include_groups=False).reset_index()
combo = combo[combo.spend > combo.spend.quantile(0.1)]
top = combo.sort_values("ROAS", ascending=False).head(5)[["platform", "campaign_type", "creative_format", "spend", "ROAS", "CPA"]].round(2)
bot = combo.sort_values("ROAS").head(5)[["platform", "campaign_type", "creative_format", "spend", "ROAS", "CPA"]].round(2)
out.append("\n## 7. Top 5 kombinasi (scale up)\n" + top.to_string(index=False))
out.append("\n## 8. Bottom 5 kombinasi (kurangi / optimasi)\n" + bot.to_string(index=False))

# ---------------- Chart ----------------
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

# a) ROAS & spend mingguan
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
for pl, g in weekly.groupby("platform"):
    ax[0].plot(g["week"], g["ROAS"], marker="o", label=pl, color=COLORS[pl])
    ax[1].plot(g["week"], g["spend"] / 1e6, marker="o", label=pl, color=COLORS[pl])
ax[0].set_title("ROAS mingguan"); ax[1].set_title("Spend mingguan (juta IDR)")
for a in ax: a.legend(); a.tick_params(axis="x", rotation=30)
plt.tight_layout(); plt.savefig(CH + "01_weekly_roas_spend.png", dpi=140); plt.close()

# b) CPA & ROAS per tipe campaign
pc = by_pc.reset_index()
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
for i, metric in enumerate(["CPA", "ROAS"]):
    pv = pc.pivot(index="campaign_type", columns="platform", values=metric)
    pv.plot.bar(ax=ax[i], color=[COLORS[c] for c in pv.columns], rot=0)
    ax[i].set_title(f"{metric} per tipe campaign"); ax[i].set_xlabel("")
plt.tight_layout(); plt.savefig(CH + "02_campaign_type.png", dpi=140); plt.close()

# c) Heatmap ROAS: format kreatif x platform
pv = by_cr.reset_index().pivot(index="creative_format", columns="platform", values="ROAS")
fig, ax = plt.subplots(figsize=(5.5, 4))
im = ax.imshow(pv.values, cmap="YlGn", aspect="auto")
ax.set_xticks(range(len(pv.columns)), pv.columns); ax.set_yticks(range(len(pv.index)), pv.index)
for i in range(pv.shape[0]):
    for j in range(pv.shape[1]):
        ax.text(j, i, f"{pv.values[i, j]:.2f}", ha="center", va="center")
ax.set_title("ROAS: format kreatif x platform"); plt.colorbar(im)
plt.tight_layout(); plt.savefig(CH + "03_creative_heatmap.png", dpi=140); plt.close()

# d) Creative fatigue
fig, ax = plt.subplots(figsize=(6.5, 4))
for pl, g in fat.reset_index().groupby("platform"):
    ax.plot(g["age_bucket"].astype(str), g["CTR_%"], marker="o", label=pl, color=COLORS[pl])
ax.set_title("CTR menurun seiring umur ad (creative fatigue)"); ax.set_ylabel("CTR %"); ax.legend()
plt.tight_layout(); plt.savefig(CH + "04_creative_fatigue.png", dpi=140); plt.close()

# e) Funnel
fun = df.groupby("platform")[["impressions", "clicks", "add_to_cart", "purchases"]].sum()
fig, ax = plt.subplots(figsize=(7, 4))
(fun.div(fun["impressions"], axis=0) * 100).T.plot.bar(ax=ax, logy=True, color=[COLORS[c] for c in fun.index], rot=0)
ax.set_title("Funnel (% dari impressions, skala log)")
plt.tight_layout(); plt.savefig(CH + "05_funnel.png", dpi=140); plt.close()

report = "\n".join(out)
open("reports/analysis_summary.txt", "w").write(report)
print(report)
