"""
Langkah 2 - ETL: bersihkan kedua export, samakan skema, gabungkan jadi satu tabel.
"""
import numpy as np
import pandas as pd

raw_meta = pd.read_csv("data/raw/meta_ads_export.csv")
raw_tt = pd.read_csv("data/raw/tiktok_ads_export.csv")

# 1) Mapping kolom -> skema terpadu
meta = raw_meta.rename(columns={
    "Day": "date", "Campaign name": "campaign", "Ad set name": "ad_group",
    "Ad name": "ad", "Amount spent (IDR)": "spend", "Impressions": "impressions",
    "Reach": "reach", "Link clicks": "clicks", "Adds to cart": "add_to_cart",
    "Purchases": "purchases", "Purchases conversion value": "revenue",
})
meta["video_views_6s"] = np.nan          # Meta export ini tidak punya metrik tsb
meta["platform"] = "Meta"
meta["date"] = pd.to_datetime(meta["date"], format="%Y-%m-%d")

tt = raw_tt.rename(columns={
    "stat_time_day": "date", "campaign_name": "campaign", "adgroup_name": "ad_group",
    "ad_name": "ad", "complete_payment": "purchases", "complete_payment_value": "revenue",
    "video_views_p6s": "video_views_6s",
})
tt["platform"] = "TikTok"
tt["date"] = pd.to_datetime(tt["date"], format="%d/%m/%Y")

df = pd.concat([meta, tt], ignore_index=True)

# 2) Standardisasi teks
for c in ["campaign", "ad_group", "ad"]:
    df[c] = df[c].str.strip()
df["campaign"] = df["campaign"].str.upper().str.replace("PROSPECTING_FASHION_PRIA", "PROSPECTING_Fashion_Pria") \
    .str.replace("PROSPECTING_FASHION_WANITA", "PROSPECTING_Fashion_Wanita") \
    .str.replace("RETARGETING_ADDTOCART", "RETARGETING_AddToCart") \
    .str.replace("AWARENESS_BRAND_VIDEO", "AWARENESS_Brand_Video")

# 3) Hapus duplikat
before = len(df)
df = df.drop_duplicates(subset=["date", "platform", "campaign", "ad_group", "ad"])
print(f"Duplikat dibuang: {before - len(df)}")

# 4) Tangani nilai hilang (impressions) -> imputasi pakai median CPM per ad, beri flag
df["impressions_imputed"] = df["impressions"].isna()
cpm_med = (df["spend"] / df["impressions"] * 1000).groupby([df["platform"], df["ad"]]).transform("median")
df["impressions"] = df["impressions"].fillna((df["spend"] / cpm_med * 1000).round())
print(f"Impressions diimputasi: {int(df['impressions_imputed'].sum())}")

# 5) Feature engineering dari penamaan
df["objective_funnel"] = np.where(df["campaign"].str.startswith("RETARGETING"), "BOFU", "TOFU")
df["campaign_type"] = df["campaign"].str.split("_").str[0].str.title()
df["creative_format"] = df["ad"].str.rsplit("_", n=1).str[0]
df["week"] = df["date"].dt.to_period("W-SUN").dt.start_time
df["month"] = df["date"].dt.to_period("M").astype(str)

# 6) Validasi
assert (df["clicks"] <= df["impressions"]).all(), "clicks > impressions"
assert (df["purchases"] <= df["clicks"]).all(), "purchases > clicks"
assert df["spend"].ge(0).all()
assert df.duplicated(["date", "platform", "campaign", "ad_group", "ad"]).sum() == 0

cols = ["date", "week", "month", "platform", "campaign", "campaign_type", "objective_funnel",
        "ad_group", "ad", "creative_format", "spend", "impressions", "reach", "clicks",
        "video_views_6s", "add_to_cart", "purchases", "revenue", "impressions_imputed"]
df = df[cols].sort_values(["date", "platform", "campaign", "ad_group", "ad"])
df.to_csv("data/clean/ads_unified.csv", index=False)
print(f"Data bersih: {len(df):,} baris -> data/clean/ads_unified.csv")
