import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils.constants import CATEGORY_EMOJI
from utils.currency import format_amount


def generate_chart(
    by_category: dict[str, float],
    currency: str,
    month_display: str,
    chart_type: str = "bar",
) -> io.BytesIO:
    """
    Generate a bar or pie chart of expenses by category.
    by_category: {category: spent_amount}
    Returns BytesIO PNG image.
    """
    data = {k: v for k, v in by_category.items() if v > 0}
    if not data:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Tidak ada data pengeluaran", ha="center", va="center", fontsize=12)
        ax.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf

    categories = list(data.keys())
    amounts = [data[c] for c in categories]
    labels = [f"{CATEGORY_EMOJI.get(c, '')} {c}" for c in categories]
    colors = plt.cm.Set3.colors[: len(categories)]  # type: ignore[attr-defined]

    fig, ax = plt.subplots(figsize=(10, max(4, len(categories) * 0.6 + 2)))

    if chart_type == "pie":
        wedges, texts, autotexts = ax.pie(
            amounts, labels=labels, autopct="%1.1f%%",
            colors=colors, startangle=90,
        )
        for t in autotexts:
            t.set_fontsize(9)
        ax.set_title(f"Pengeluaran {month_display} ({currency})", fontsize=13, fontweight="bold", pad=15)
    else:
        bars = ax.barh(labels, amounts, color=colors)
        ax.set_xlabel(f"Jumlah ({currency})", fontsize=10)
        ax.set_title(f"Pengeluaran {month_display} per Kategori", fontsize=13, fontweight="bold")
        # Value labels
        for bar, amt in zip(bars, amounts):
            label = f"Rp {amt:,.0f}".replace(",", ".") if currency == "IDR" else f"{amt:,.2f}"
            ax.text(
                bar.get_width() * 1.005,
                bar.get_y() + bar.get_height() / 2,
                label, va="center", fontsize=8,
            )
        ax.invert_yaxis()
        ax.set_xlim(right=max(amounts) * 1.25)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf
