# Social Media Ads Analyst Project (Meta Ads vs TikTok Ads) - Data Sintesis

Brand fiktif: fashion e-commerce Indonesia (IDR), periode 1 Agu - 31 Okt 2026.

## Alur pipeline
| Langkah | File | Output |
|---|---|---|
| 1. Ambil data (sintesis, meniru format export asli) | `01_generate_data.py` | `data/raw/meta_ads_export.csv`, `data/raw/tiktok_ads_export.csv` |
| 2. ETL: rename kolom, samakan tanggal, dedup, imputasi, validasi | `02_etl_clean.py` | `data/clean/ads_unified.csv` |
| 3. Analisis, uji statistik, chart | `03_analysis.py` | `reports/*.csv`, `reports/charts/*.png`, `reports/analysis_summary.txt` |

Jalankan: `pip install pandas numpy matplotlib scipy` lalu `python 01_generate_data.py && python 02_etl_clean.py && python 03_analysis.py`

## Perbedaan skema kedua platform (inti pekerjaan ETL)
| Konsep | Meta | TikTok | Skema terpadu |
|---|---|---|---|
| Tanggal | `Day` (YYYY-MM-DD) | `stat_time_day` (DD/MM/YYYY) | `date` |
| Biaya | `Amount spent (IDR)` | `spend` | `spend` |
| Klik | `Link clicks` | `clicks` | `clicks` |
| Pembelian | `Purchases` | `complete_payment` | `purchases` |
| Nilai pembelian | `Purchases conversion value` | `complete_payment_value` | `revenue` |
| Ad group | `Ad set name` | `adgroup_name` | `ad_group` |
| Video view | (tidak ada) | `video_views_p6s` | `video_views_6s` |

## Masalah data yang sengaja disisipkan (latihan cleaning)
Baris duplikat, `impressions` kosong, nama campaign beda huruf besar/kecil dan ada spasi, format tanggal beda.

## Rumus KPI
CPM = spend/impressions x 1000 | CTR = clicks/impressions | CPC = spend/clicks | CVR = purchases/clicks |
CPA = spend/purchases | ROAS = revenue/spend | AOV = revenue/purchases.
Selalu jumlahkan dulu lalu bagi; jangan merata-ratakan rasio harian.

## Langkah lanjutan
1. Ganti langkah 1 dengan data asli: Meta Marketing API (`/insights`) dan TikTok Marketing API (`/report/integrated/get/`), atau export CSV manual.
2. Dashboard (Looker Studio / Power BI / Streamlit) dari `ads_unified.csv`.
3. Simpan ke database (SQLite/PostgreSQL) dan tulis query SQL untuk KPI.
4. Model: forecasting spend/ROAS, diminishing returns per channel, simulasi realokasi budget.
