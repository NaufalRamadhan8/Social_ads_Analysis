"""
Langkah 1 - Membuat data SINTESIS yang meniru format export asli
Meta Ads Manager dan TikTok Ads Manager (brand fiktif: fashion e-commerce, mata uang IDR).
Periode: 1 Agu - 31 Okt 2026.
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
RAW = Path("data/raw")
DATES = pd.date_range("2026-08-01", "2026-10-31")

# --- Struktur akun ----------------------------------------------------------
CAMPAIGNS = {  # nama: (funnel, budget harian dasar per ad dalam IDR)
    "PROSPECTING_Fashion_Pria":   ("TOFU", 450_000),
    "PROSPECTING_Fashion_Wanita": ("TOFU", 550_000),
    "RETARGETING_AddToCart":      ("BOFU", 250_000),
    "AWARENESS_Brand_Video":      ("TOFU", 300_000),
}
ADSETS = {
    "PROSPECTING_Fashion_Pria":   ["Broad_18-34", "Interest_Streetwear"],
    "PROSPECTING_Fashion_Wanita": ["Broad_18-34", "Lookalike_1pct_Buyers"],
    "RETARGETING_AddToCart":      ["Visitors_7d", "AddToCart_14d"],
    "AWARENESS_Brand_Video":      ["Broad_18-44"],
}
CREATIVES = ["UGC_Video", "Static_Promo", "Carousel", "Influencer_Video"]

# Karakter tiap platform (CPM dalam IDR, CTR, CVR = purchase / click)
PLATFORM = {
    "Meta":   dict(cpm=42_000, ctr=0.011, cvr=0.028, atc=0.09, aov=265_000),
    "TikTok": dict(cpm=24_000, ctr=0.015, cvr=0.014, atc=0.07, aov=240_000),
}
FUNNEL_MULT = {  # pengali (ctr, cvr, cpm)
    "TOFU": (1.0, 1.0, 1.0),
    "BOFU": (1.6, 3.2, 1.35),
}
CREATIVE_MULT = {  # pengali (ctr, cvr) per format kreatif, beda per platform
    "Meta":   {"UGC_Video": (1.10, 1.05), "Static_Promo": (0.85, 1.10),
               "Carousel": (1.00, 1.15), "Influencer_Video": (1.15, 0.95)},
    "TikTok": {"UGC_Video": (1.35, 1.10), "Static_Promo": (0.60, 0.80),
               "Carousel": (0.75, 0.90), "Influencer_Video": (1.40, 1.00)},
}
EVENTS = {"2026-09-09": 1.8, "2026-10-10": 2.0}   # harbolnas 9.9 dan 10.10


def day_factors(d):
    dow = {0: 0.95, 1: 0.95, 2: 1.0, 3: 1.0, 4: 1.05, 5: 1.15, 6: 1.12}[d.dayofweek]
    payday = 1.25 if (d.day >= 25 or d.day <= 2) else 1.0
    event = EVENTS.get(d.strftime("%Y-%m-%d"), 1.0)
    # efek lanjutan 2 hari sebelum event (warming up)
    for k, v in EVENTS.items():
        gap = (pd.Timestamp(k) - d).days
        if 0 < gap <= 2:
            event = max(event, 1.0 + (v - 1) * 0.3)
    return dow, payday, event


def simulate(platform):
    p = PLATFORM[platform]
    rows = []
    for camp, (funnel, base_budget) in CAMPAIGNS.items():
        f_ctr, f_cvr, f_cpm = FUNNEL_MULT[funnel]
        for adset in ADSETS[camp]:
            for ci, creative in enumerate(CREATIVES):
                # beberapa kreatif baru launch di tengah periode
                launch = DATES[0] + pd.Timedelta(days=int(rng.integers(0, 40)))
                if creative == "Influencer_Video":
                    launch = DATES[0] + pd.Timedelta(days=int(rng.integers(10, 30)))
                c_ctr, c_cvr = CREATIVE_MULT[platform][creative]
                quality = rng.normal(1.0, 0.08)          # variasi kualitas ad
                for d in DATES[DATES >= launch]:
                    age = (d - launch).days
                    fatigue = max(0.55, 1.0 - 0.006 * age)   # creative fatigue
                    dow, payday, event = day_factors(d)

                    spend = base_budget * dow * payday * event * rng.lognormal(0, 0.15)
                    cpm = p["cpm"] * f_cpm * (1 + 0.15 * (event - 1)) * rng.lognormal(0, 0.10)
                    impressions = int(spend / cpm * 1000)
                    freq = (2.4 if funnel == "BOFU" else 1.2) + age * 0.012 + rng.random() * 0.3
                    reach = int(impressions / freq)

                    ctr = p["ctr"] * f_ctr * c_ctr * quality * fatigue * rng.lognormal(0, 0.08)
                    clicks = int(rng.binomial(impressions, min(ctr, 0.2)))

                    cvr = p["cvr"] * f_cvr * c_cvr * quality * (1 + 0.5 * (event - 1)) * (1.1 if payday > 1 else 1)
                    purchases = int(rng.binomial(clicks, min(cvr * rng.lognormal(0, 0.10), 0.5)))
                    atc = int(rng.binomial(clicks, min(p["atc"] * f_cvr ** 0.5, 0.5)))
                    atc = max(atc, purchases)
                    revenue = purchases * p["aov"] * rng.lognormal(0, 0.18) * (1 + 0.1 * (event - 1))

                    rows.append(dict(
                        date=d, campaign=camp, adset=adset,
                        ad=f"{creative}_V{ci % 2 + 1}", spend=spend,
                        impressions=impressions, reach=reach, clicks=clicks,
                        atc=atc, purchases=purchases, revenue=revenue,
                        video_6s=int(impressions * rng.uniform(0.18, 0.30) * (1.3 if "Video" in creative else 0.15)),
                    ))
    return pd.DataFrame(rows)


# --- Export format Meta Ads Manager -----------------------------------------
meta = simulate("Meta")
meta_raw = pd.DataFrame({
    "Day": meta["date"].dt.strftime("%Y-%m-%d"),
    "Campaign name": meta["campaign"],
    "Ad set name": meta["adset"],
    "Ad name": meta["ad"],
    "Amount spent (IDR)": meta["spend"].round(0),
    "Impressions": meta["impressions"],
    "Reach": meta["reach"],
    "Link clicks": meta["clicks"],
    "Adds to cart": meta["atc"],
    "Purchases": meta["purchases"],
    "Purchases conversion value": meta["revenue"].round(0),
})
# kotoran data: duplikat baris (~1%)
dups = meta_raw.sample(frac=0.01, random_state=1)
meta_raw = pd.concat([meta_raw, dups]).sample(frac=1, random_state=2).reset_index(drop=True)
meta_raw.to_csv(RAW / "meta_ads_export.csv", index=False)

# --- Export format TikTok Ads Manager ---------------------------------------
tt = simulate("TikTok")
tt_raw = pd.DataFrame({
    "stat_time_day": tt["date"].dt.strftime("%d/%m/%Y"),          # format tanggal beda
    "campaign_name": tt["campaign"].str.lower(),                  # huruf kecil
    "adgroup_name": tt["adset"],
    "ad_name": tt["ad"],
    "spend": tt["spend"].round(2),
    "impressions": tt["impressions"],
    "reach": tt["reach"],
    "clicks": tt["clicks"],
    "video_views_p6s": tt["video_6s"],
    "add_to_cart": tt["atc"],
    "complete_payment": tt["purchases"],
    "complete_payment_value": tt["revenue"].round(2),
})
# kotoran data: nilai hilang, spasi, duplikat
idx = tt_raw.sample(frac=0.005, random_state=3).index
tt_raw.loc[idx, "impressions"] = np.nan
idx2 = tt_raw.sample(frac=0.02, random_state=4).index
tt_raw.loc[idx2, "campaign_name"] = tt_raw.loc[idx2, "campaign_name"] + " "
tt_raw = pd.concat([tt_raw, tt_raw.sample(frac=0.008, random_state=5)]).sample(frac=1, random_state=6).reset_index(drop=True)
tt_raw.to_csv(RAW / "tiktok_ads_export.csv", index=False)

print(f"Meta  : {len(meta_raw):,} baris -> data/raw/meta_ads_export.csv")
print(f"TikTok: {len(tt_raw):,} baris -> data/raw/tiktok_ads_export.csv")
