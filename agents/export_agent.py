import csv
import io


def generate_csv(expenses: list[dict], label: str = "expenses") -> tuple[io.BytesIO, str]:
    """
    Generate a CSV file from a list of expense dicts.
    Returns (BytesIO, filename). Uses UTF-8 BOM for Excel compatibility.
    """
    fieldnames = ["date", "description", "amount", "currency", "category", "payment_method", "input_type", "created_at"]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(expenses)

    # UTF-8 BOM so Excel on Windows opens with correct encoding
    buf = io.BytesIO(("﻿" + output.getvalue()).encode("utf-8"))
    filename = f"{label}.csv"
    return buf, filename
