#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulk QR → PDF generator  (Excel version)
---------------------------------------
קורא קובץ ‎.xlsx עם העמודות:
    personal_id | first_name | second_name
ויוצר PDF נפרד לכל משתתף:
    • QR במרכז (3-in)
    • שם קטן בתחתית (lowercase)
"""

from pathlib import Path
import requests                     # pip install requests
import pandas as pd                 # pip install pandas openpyxl
from reportlab.pdfgen import canvas # pip install reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# אם יש שמות בעברית – רשום גופן Unicode (למשל DejaVu Sans)
# pdfmetrics.registerFont(TTFont("DejaVu", "/path/to/DejaVuSans.ttf"))

# ---------- QR helper ----------
def create_qr_code(text: str,
                   filename: Path,
                   size: int = 300) -> Path:
    r = requests.get(
        "https://api.qrserver.com/v1/create-qr-code/",
        params={"data": text, "size": f"{size}x{size}"},
        timeout=10
    )
    r.raise_for_status()
    filename.write_bytes(r.content)
    return filename


# ---------- PDF builder ----------
def generate_pdf_for_participant(pid: str,
                                 first_name: str,
                                 second_name: str,
                                 out_dir: Path,
                                 qr_size_px: int = 300):
    out_dir.mkdir(exist_ok=True)
    qr_path = out_dir / f"{pid}.png"
    create_qr_code(pid, qr_path, qr_size_px)

    pdf_path = out_dir / f"{pid}_{first_name}_{second_name}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    # גודל QR ב-inch ⇒ 3-in (≈ 216 pt)
    qr_size_pt = 3 * inch
    # מיקום אמצע העמוד
    x_center = width  / 2 - qr_size_pt / 2
    y_center = height / 2 - qr_size_pt / 2
    c.drawImage(str(qr_path), x_center, y_center,
                width=qr_size_pt, height=qr_size_pt, preserveAspectRatio=True)

    # שם בכותרת תחתונה
    # name_text = f"{first_name.lower()} {second_name.lower()}"
    name_text = f"{pid}"
    c.setFont("Helvetica", 10)  # שים "DejaVu" אם רשמת גופן עברית
    c.drawCentredString(width / 2, 0.5 * inch, name_text)

    c.showPage()
    c.save()
    print(f"✔  {pdf_path.name}")


# ---------- Excel → PDF bulk ----------
def bulk_generate_from_excel(xlsx_path: str,
                             output_dir: str = "participant_pdfs",
                             qr_size: int = 300):
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
            qr_size_px=qr_size,
        )


if __name__ == "__main__":
    bulk_generate_from_excel('./data/alon_a_participants.xlsx', 'data/participants_qr_code', 300)