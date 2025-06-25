#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulk **BARCODE** → PDF generator  (Excel version)
-------------------------------------------------
Reads an .xlsx file with the columns:
    personal_id | first_name | second_name
and produces one PDF per participant:
    • Code-128 barcode in the exact size 40 mm × 15 mm, centred
    • Their ID printed underneath
"""

from pathlib import Path
import pandas as pd                      # pip install pandas openpyxl
from reportlab.pdfgen import canvas      # pip install reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Uncomment and point to a TTF if you need Hebrew/Unicode names
# pdfmetrics.registerFont(TTFont("DejaVu", "/path/to/DejaVuSans.ttf"))

# ---------- PDF builder ----------
def generate_pdf_for_participant(pid: str,
                                 first_name: str,
                                 second_name: str,
                                 out_dir: Path):
    """
    Create a single-page PDF containing a Code-128 barcode sized
    exactly 40 mm wide × 15 mm high, with the participant ID below it.
    """
    out_dir.mkdir(exist_ok=True)
    pdf_path = out_dir / f"{pid}_{first_name}_{second_name}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    page_w, page_h = A4

    # --- build the barcode (Code-128 is compact and numeric-friendly) ---
    raw_barcode = code128.Code128(pid, barHeight=15 * mm, humanReadable=False)

    # scale so that final width == 40 mm
    desired_w = 40 * mm
    scale_x = desired_w / raw_barcode.width

    # position: centred on the page
    barcode_x = (page_w - desired_w) / 2
    barcode_y = (page_h - 15 * mm) / 2

    # draw scaled barcode
    c.saveState()
    c.translate(barcode_x, barcode_y)
    c.scale(scale_x, 1.0)   # only scale horizontally
    raw_barcode.drawOn(c, 0, 0)
    c.restoreState()

    # participant ID underneath (centre-aligned)
    c.setFont("Helvetica", 10)           # change to "DejaVu" if you registered it
    c.drawCentredString(page_w / 2, barcode_y - 5 * mm, pid)

    c.showPage()
    c.save()
    print(f"✔  {pdf_path.name}")


# ---------- Excel → PDF bulk ----------
def bulk_generate_from_excel(xlsx_path: str,
                             output_dir: str = "participant_barcodes"):
    out_dir = Path(output_dir)
    df = pd.read_excel(xlsx_path, engine="openpyxl")
    required = {"personal_id", "first_name", "second_name"}
    if not required.issubset(df.columns):
        raise ValueError(f"Excel must include columns: {', '.join(required)}")

    for _, row in df.iterrows():
        generate_pdf_for_participant(
            pid=str(row["personal_id"]).strip(),
            first_name=str(row["first_name"]).strip(),
            second_name=str(row["second_name"]).strip(),
            out_dir=out_dir,
        )


if __name__ == "__main__":
    bulk_generate_from_excel(
        "./data/alon_a_participants.xlsx",
        "data/participants_barcodes"
    )