from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

sns.set_theme(style="whitegrid")
HIGHLIGHT = "#1f77b4"
MUTED = "#c9ced6"
WARN = "#d62728"

st.set_page_config(page_title="E-Commerce Dashboard", page_icon="🛒", layout="wide")


# ------------------------------------------------------------------ DATA
@st.cache_data
def load_data() -> pd.DataFrame:
    path = Path(__file__).parent / "main_data.csv"
    df = pd.read_csv(path, parse_dates=["order_purchase_timestamp",
                                        "order_delivered_customer_date",
                                        "order_estimated_delivery_date"])
    df["bulan"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    return df


def rupiah_juta(x, pos=None):
    return f"R$ {x / 1e6:.1f} jt"


def to_orders(items: pd.DataFrame) -> pd.DataFrame:
    """Data level item -> level pesanan (satu baris per order_id)."""
    order_value = items.groupby("order_id")["price"].sum().rename("order_value")
    orders = items.drop_duplicates("order_id").merge(order_value, on="order_id")
    return orders


def build_rfm(orders: pd.DataFrame) -> pd.DataFrame:
    snapshot = orders["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    rfm = (orders.groupby("customer_unique_id")
           .agg(last_purchase=("order_purchase_timestamp", "max"),
                frequency=("order_id", "nunique"),
                monetary=("order_value", "sum"))
           .reset_index())
    rfm["recency"] = (snapshot - rfm["last_purchase"]).dt.days
    rfm["r_score"] = pd.qcut(rfm["recency"].rank(method="first", ascending=False), 4,
                             labels=[1, 2, 3, 4]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 4,
                             labels=[1, 2, 3, 4]).astype(int)

    def segment(row):
        if row["frequency"] >= 2:
            return "Repeat Customers"
        if row["r_score"] >= 3:
            return "Big Spender (Aktif)" if row["m_score"] == 4 else "New / Recent Customers"
        return "At Risk Big Spender" if row["m_score"] >= 3 else "Lost / Dormant"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


data = load_data()

# ------------------------------------------------------------------ SIDEBAR
st.sidebar.title("Filter Data")
min_date = data["order_purchase_timestamp"].min().date()
max_date = data["order_purchase_timestamp"].max().date()
date_range = st.sidebar.date_input("Rentang tanggal pembelian", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)
all_states = sorted(data["customer_state"].unique())
selected_states = st.sidebar.multiselect("State pelanggan", all_states, default=all_states)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:  # pengguna baru memilih satu tanggal
    start_date, end_date = min_date, max_date

mask = (
    (data["order_purchase_timestamp"].dt.date >= start_date)
    & (data["order_purchase_timestamp"].dt.date <= end_date)
    & (data["customer_state"].isin(selected_states))
)
items = data[mask]

st.sidebar.caption("Data: Olist Brazilian E-Commerce, pesanan *delivered* "
                   "Jan 2017 – Agu 2018. Revenue = total harga produk (tanpa ongkir).")

# ------------------------------------------------------------------ HEADER
st.title("🛒 E-Commerce Public Dataset Dashboard")
st.caption("Ringkasan hasil analisis: kategori produk, tren penjualan, pengiriman & kepuasan pelanggan, "
           "sebaran geografis, dan segmentasi pelanggan (RFM).")

if items.empty:
    st.warning("Tidak ada data pada filter yang dipilih. Ubah rentang tanggal atau state.")
    st.stop()

orders = to_orders(items)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Pesanan", f"{orders['order_id'].nunique():,}")
c2.metric("Total Revenue", f"R$ {items['price'].sum() / 1e6:.2f} jt")
c3.metric("Pelanggan Unik", f"{orders['customer_unique_id'].nunique():,}")
c4.metric("Rata-rata Review", f"{orders['review_score'].mean():.2f} / 5")
c5.metric("Pesanan Terlambat", f"{orders['is_late'].mean() * 100:.1f}%")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Kategori Produk", "📈 Tren Bulanan", "🚚 Pengiriman & Review",
    "🗺️ Geospasial", "👥 Segmentasi RFM"])

# ------------------------------------------------------------------ TAB 1
with tab1:
    st.subheader("Kategori produk apa yang paling besar kontribusi revenue-nya?")
    cat = (items.groupby("product_category")
           .agg(revenue=("price", "sum"), jumlah_item=("order_id", "count"))
           .sort_values("revenue", ascending=False))
    cat["kontribusi_pct"] = cat["revenue"] / cat["revenue"].sum() * 100

    n_top = st.slider("Jumlah kategori teratas yang ditampilkan", 5, 15, 10)
    top = cat.head(n_top).sort_values("revenue")
    colors = [HIGHLIGHT if c in cat.head(5).index else MUTED for c in top.index]

    left, right = st.columns([1.7, 1])
    with left:
        fig, ax = plt.subplots(figsize=(9, 0.48 * n_top + 1.5))
        ax.barh(top.index, top["revenue"], color=colors)
        ax.xaxis.set_major_formatter(mtick.FuncFormatter(rupiah_juta))
        for i, (v, p) in enumerate(zip(top["revenue"], top["kontribusi_pct"])):
            ax.text(v + top["revenue"].max() * 0.01, i, f"{p:.1f}%", va="center", fontsize=9)
        ax.set_xlim(0, top["revenue"].max() * 1.15)
        ax.set_xlabel("Total revenue")
        ax.set_ylabel("")
        ax.set_title("Kategori dengan revenue tertinggi (biru = Top 5)", loc="left", fontweight="bold")
        sns.despine(left=True)
        st.pyplot(fig)
        plt.close(fig)
    with right:
        st.metric("Kontribusi Top 5 kategori", f"{cat['kontribusi_pct'].head(5).sum():.1f}%")
        st.metric("Kontribusi Top 10 kategori", f"{cat['kontribusi_pct'].head(10).sum():.1f}%")
        st.markdown("**5 kategori dengan revenue terendah**")
        low = cat.tail(5).sort_values("revenue")[["revenue", "jumlah_item"]]
        low.columns = ["Revenue (R$)", "Jumlah item"]
        st.dataframe(low.style.format({"Revenue (R$)": "{:,.0f}"}))

# ------------------------------------------------------------------ TAB 2
with tab2:
    st.subheader("Bagaimana tren pesanan dan revenue bulanan?")
    monthly = (items.groupby("bulan")
               .agg(jumlah_pesanan=("order_id", "nunique"), revenue=("price", "sum")))
    monthly["mom_revenue_pct"] = monthly["revenue"].pct_change() * 100

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(monthly.index, monthly["revenue"], marker="o", color=HIGHLIGHT, linewidth=2.2)
    axes[0].yaxis.set_major_formatter(mtick.FuncFormatter(rupiah_juta))
    axes[0].set_title("Total revenue bulanan", loc="left", fontweight="bold")
    axes[0].set_ylim(bottom=0)
    peak = monthly["revenue"].idxmax()
    axes[0].annotate(f"Puncak {peak}", xy=(peak, monthly.loc[peak, "revenue"]),
                     xytext=(0, 18), textcoords="offset points", ha="center",
                     arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9)
    axes[1].plot(monthly.index, monthly["jumlah_pesanan"], marker="o", color="#2ca02c", linewidth=2.2)
    axes[1].set_title("Jumlah pesanan bulanan", loc="left", fontweight="bold")
    axes[1].yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    axes[1].set_ylim(bottom=0)
    plt.setp(axes[1].get_xticklabels(), rotation=45, ha="right")
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # YoY Jan-Agu hanya bermakna jika kedua periode ada pada data terfilter
    ytd17 = monthly.loc[(monthly.index >= "2017-01") & (monthly.index <= "2017-08"), "revenue"]
    ytd18 = monthly.loc[(monthly.index >= "2018-01") & (monthly.index <= "2018-08"), "revenue"]
    if len(ytd17) == 8 and len(ytd18) == 8:
        st.metric("Pertumbuhan revenue Jan–Agu 2018 vs Jan–Agu 2017 (YoY)",
                  f"{(ytd18.sum() / ytd17.sum() - 1) * 100:.0f}%",
                  f"R$ {ytd17.sum() / 1e6:.2f} jt → R$ {ytd18.sum() / 1e6:.2f} jt")
    else:
        st.info("Metrik YoY Jan–Agu ditampilkan jika rentang tanggal mencakup Jan 2017 – Agu 2018 penuh.")

# ------------------------------------------------------------------ TAB 3
with tab3:
    st.subheader("Seberapa besar keterlambatan pengiriman menurunkan skor review?")
    rv = orders.dropna(subset=["review_score"]).copy()
    bins = [-np.inf, -8, 0, 3, 7, 14, np.inf]
    labels = ["Lebih cepat > 7 hari", "Tepat waktu / lebih cepat <= 7 hari",
              "Telat 1-3 hari", "Telat 4-7 hari", "Telat 8-14 hari", "Telat > 14 hari"]
    rv["kelompok"] = pd.cut(rv["delay_days"], bins=bins, labels=labels)
    grp = (rv.groupby("kelompok", observed=True)
           .agg(n=("order_id", "count"), skor=("review_score", "mean")).reset_index())

    ontime = rv.loc[~rv["is_late"], "review_score"].mean()
    late = rv.loc[rv["is_late"], "review_score"].mean()
    m1, m2, m3 = st.columns(3)
    m1.metric("Skor review tepat waktu", f"{ontime:.2f}")
    m2.metric("Skor review terlambat", f"{late:.2f}" if not np.isnan(late) else "-")
    m3.metric("Selisih", f"{ontime - late:.2f} poin" if not np.isnan(late) else "-")

    left, right = st.columns(2)
    with left:
        fig, ax = plt.subplots(figsize=(7, 5))
        cols = [WARN if "Telat" in k else HIGHLIGHT for k in grp["kelompok"].astype(str)]
        ax.bar(range(len(grp)), grp["skor"], color=cols)
        ax.set_xticks(range(len(grp)))
        ax.set_xticklabels([l.replace(" / ", "\n/ ") for l in grp["kelompok"].astype(str)],
                           rotation=35, ha="right", fontsize=8)
        ax.set_ylim(0, 5)
        ax.set_ylabel("Rata-rata review score (1–5)")
        ax.set_title("Skor review per kelompok pengiriman", loc="left", fontweight="bold")
        for i, (s, n) in enumerate(zip(grp["skor"], grp["n"])):
            ax.text(i, s + 0.08, f"{s:.2f}\n(n={n:,})", ha="center", fontsize=8)
        sns.despine()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    with right:
        sp = (rv.groupby("customer_state")
              .agg(n=("order_id", "count"), skor=("review_score", "mean"),
                   pct_late=("is_late", lambda s: s.mean() * 100)))
        sp = sp[sp["n"] >= 100]
        fig, ax = plt.subplots(figsize=(7, 5))
        if len(sp) >= 3:
            ax.scatter(sp["pct_late"], sp["skor"], s=40 + sp["n"] / 70, color=HIGHLIGHT,
                       alpha=0.6, edgecolor="white")
            for st_name, row in sp.iterrows():
                ax.annotate(st_name, (row["pct_late"], row["skor"]), fontsize=8,
                            xytext=(4, 4), textcoords="offset points")
            slope, intercept = np.polyfit(sp["pct_late"], sp["skor"], 1)
            xs = np.linspace(sp["pct_late"].min(), sp["pct_late"].max(), 50)
            ax.plot(xs, slope * xs + intercept, color="gray", linestyle="--", linewidth=1)
            ax.set_title(f"Per state: r = {sp['pct_late'].corr(sp['skor']):.2f}", loc="left",
                         fontweight="bold")
        ax.set_xlabel("Persentase pesanan terlambat (%)")
        ax.set_ylabel("Rata-rata review score")
        sns.despine()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
        st.caption("State dengan < 100 pesanan (pada filter ini) tidak ditampilkan. "
                   "Ukuran titik = jumlah pesanan.")

    st.markdown("**State dengan keterlambatan tertinggi**")
    worst = sp.sort_values("pct_late", ascending=False).head(8).rename(
        columns={"n": "Jumlah pesanan", "skor": "Rata-rata review", "pct_late": "% terlambat"})
    st.dataframe(worst.style.format({"Rata-rata review": "{:.2f}", "% terlambat": "{:.1f}"}))

# ------------------------------------------------------------------ TAB 4
with tab4:
    st.subheader("Di mana pelanggan berada dan di mana pengiriman bermasalah?")
    geo = orders.dropna(subset=["customer_lat", "customer_lng"])
    state_geo = (geo.groupby("customer_state")
                 .agg(jumlah_pesanan=("order_id", "count"), lat=("customer_lat", "mean"),
                      lng=("customer_lng", "mean"), pct_late=("is_late", lambda s: s.mean() * 100)))
    metric = st.radio("Warnai peta berdasarkan", ["Jumlah pesanan", "% pesanan terlambat"], horizontal=True)

    fig, ax = plt.subplots(figsize=(8, 8))
    pts = geo.drop_duplicates(subset=["customer_lat", "customer_lng"])
    ax.scatter(pts["customer_lng"], pts["customer_lat"], s=2, color=MUTED, alpha=0.5)
    if metric == "Jumlah pesanan":
        ax.scatter(state_geo["lng"], state_geo["lat"], s=state_geo["jumlah_pesanan"] / 25,
                   color=HIGHLIGHT, alpha=0.6, edgecolor="white")
        for st_name, row in state_geo.iterrows():
            if row["jumlah_pesanan"] > state_geo["jumlah_pesanan"].quantile(0.75):
                ax.annotate(st_name, (row["lng"], row["lat"]), ha="center", va="center",
                            fontsize=9, fontweight="bold")
        ax.set_title("Ukuran lingkaran = jumlah pesanan", loc="left", fontweight="bold")
    else:
        valid = state_geo[state_geo["jumlah_pesanan"] >= 100]
        sc = ax.scatter(valid["lng"], valid["lat"], s=200 + valid["jumlah_pesanan"] / 60,
                        c=valid["pct_late"], cmap="YlOrRd", edgecolor="gray", alpha=0.9)
        for st_name, row in valid.iterrows():
            ax.annotate(st_name, (row["lng"], row["lat"]), ha="center", va="center", fontsize=8)
        fig.colorbar(sc, ax=ax, shrink=0.6, label="% pesanan terlambat")
        ax.set_title("State < 100 pesanan tidak ditampilkan", loc="left", fontweight="bold")
    ax.set_xlim(-75, -33)
    ax.set_ylim(-34, 6)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.markdown("**Top 5 state berdasarkan jumlah pesanan**")
    top_states = state_geo.sort_values("jumlah_pesanan", ascending=False).head(5)
    top_states = top_states.assign(persen_pesanan=top_states["jumlah_pesanan"] / state_geo["jumlah_pesanan"].sum() * 100)
    st.dataframe(top_states[["jumlah_pesanan", "persen_pesanan", "pct_late"]]
                 .rename(columns={"jumlah_pesanan": "Jumlah pesanan", "persen_pesanan": "% pesanan",
                                  "pct_late": "% terlambat"})
                 .style.format({"% pesanan": "{:.1f}", "% terlambat": "{:.1f}"}))

# ------------------------------------------------------------------ TAB 5
with tab5:
    st.subheader("Segmentasi pelanggan dengan RFM")
    st.caption("Recency = hari sejak pembelian terakhir, Frequency = jumlah pesanan, "
               "Monetary = total belanja. Segmentasi dihitung ulang sesuai filter.")
    if orders["customer_unique_id"].nunique() < 8:
        st.info("Data terlalu sedikit untuk segmentasi RFM pada filter ini.")
    else:
        rfm = build_rfm(orders)
        seg = (rfm.groupby("segment")
               .agg(pelanggan=("customer_unique_id", "count"), avg_recency=("recency", "mean"),
                    avg_monetary=("monetary", "mean"), total=("monetary", "sum")))
        seg["% pelanggan"] = seg["pelanggan"] / seg["pelanggan"].sum() * 100
        seg["% revenue"] = seg["total"] / seg["total"].sum() * 100
        seg = seg.sort_values("% revenue")

        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
        axes[0].barh(seg.index, seg["% pelanggan"], color=MUTED)
        axes[0].set_title("% dari total pelanggan", loc="left", fontweight="bold")
        axes[1].barh(seg.index, seg["% revenue"], color=HIGHLIGHT)
        axes[1].set_title("% dari total revenue", loc="left", fontweight="bold")
        for ax, col in zip(axes, ["% pelanggan", "% revenue"]):
            for i, v in enumerate(seg[col]):
                ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
            ax.set_xlim(0, seg[["% pelanggan", "% revenue"]].max().max() * 1.2)
        sns.despine(left=True)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        table = seg.sort_values("% revenue", ascending=False)[
            ["pelanggan", "avg_recency", "avg_monetary", "% pelanggan", "% revenue"]]
        table.columns = ["Pelanggan", "Rata-rata recency (hari)", "Rata-rata monetary (R$)",
                         "% pelanggan", "% revenue"]
        st.dataframe(table.style.format({"Pelanggan": "{:,.0f}", "Rata-rata recency (hari)": "{:.0f}",
                                         "Rata-rata monetary (R$)": "{:,.2f}",
                                         "% pelanggan": "{:.1f}", "% revenue": "{:.1f}"}))

st.caption("Proyek Analisis Data — E-Commerce Public Dataset (Olist).")
