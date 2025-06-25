#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QR / BAR Run-Timer
• Multi-code preview (QR + 1-D barcodes)
• 10-s cooldown per runner ID
• Big green “SCANNED” drawn on each accepted code
• Preview scaled ל-640×480 עם Letter-boxing (לא חותך את הפריים)
"""

# ---------- 0. IMPORTS & CONSTANTS -----------------------------------------
import csv, platform, time
from datetime import datetime
from pathlib import Path

import cv2, numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode          # supports EAN-13/8, CODE-128/39, QR, etc.

SCAN_COOLDOWN = 10                        # seconds before same code allowed again
TARGET_W, TARGET_H = 640, 480             # preview window size

last_scan_ts: dict[str, float] = {}       # id → last accepted time
race_started = False
race_start_ts: datetime | None = None
runs: dict[str, dict[str, datetime | None]] = {}   # id → {"start": …, "end": …}

# ---------- 1. GUI ---------------------------------------------------------
root = tk.Tk()
root.title("QR / BAR Run-Timer")
root.geometry("740x470")

style = ttk.Style(root)
style.configure("Treeview", rowheight=28)

cols = ("id", "start", "end", "duration")
view = ttk.Treeview(root, columns=cols, show="headings")
for c, head in zip(cols, ("ID", "Start", "End", "Duration (hh:mm:ss)")):
    view.heading(c, text=head)
    view.column(c, anchor=tk.CENTER)
view.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

iso = lambda dt: dt.isoformat(timespec="seconds") if dt else ""

def refresh_table() -> None:
    view.delete(*view.get_children())
    for pid, rec in runs.items():
        dur = (
            str(rec["end"] - rec["start"]).split(".")[0]
            if rec["start"] and rec["end"] else ""
        )
        view.insert(
            "", tk.END,
            values=(pid, iso(rec["start"]), iso(rec["end"]), dur)
        )
    root.title(f"QR / BAR Run-Timer – {len(runs)} runners")

# ---------- 2. LOGIC -------------------------------------------------------
def record_scan(pid: str) -> None:
    rec = runs.setdefault(pid, {"start": None, "end": None})
    if not race_started:
        return
    if rec["start"] is None:
        rec["start"] = race_start_ts
        return
    if rec["end"] is None:
        rec["end"] = datetime.now()
        return

    # Extra laps after first finish
    lap = 1
    while f"{pid}_lap{lap}" in runs:
        lap += 1
    runs[f"{pid}_lap{lap}"] = {
        "start": race_start_ts,
        "end":   datetime.now(),
    }

def start_race() -> None:
    global race_started, race_start_ts
    if race_started or not runs:
        if not runs:
            messagebox.showwarning("No runners", "Register at least one runner before starting.")
        return
    race_start_ts = datetime.now()
    race_started  = True
    for rec in runs.values():
        rec["start"] = race_start_ts
    refresh_table()
    start_btn.config(state=tk.DISABLED)
    root.bell()
    messagebox.showinfo("Race started!", f"Gun time: {iso(race_start_ts)}")

# ---------- 3. SCANNER -----------------------------------------------------
def handle_scan_preview(camera_index: int = 0) -> None:
    backend = cv2.CAP_AVFOUNDATION if platform.system() == "Darwin" else cv2.CAP_ANY
    cap = cv2.VideoCapture(camera_index, backend)

    # Try to request 640×480 from the camera (ignored if unsupported)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  TARGET_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_H)

    if not cap.isOpened():
        messagebox.showerror("Camera error", "Cannot open webcam.")
        return

    win = tk.Toplevel(root)
    win.title("Scanner – Esc to close")
    win.geometry(f"{TARGET_W}x{TARGET_H}")
    lbl = tk.Label(win)
    lbl.pack(expand=True)
    win.bind("<Escape>", lambda *_: (cap.release(), win.destroy()))

    def update() -> None:
        ok, frame = cap.read()
        if not ok:
            win.after(15, update)
            return

        # ---------- Decode ALL codes in current frame ----------------
        for obj in decode(frame):
            data = obj.data.decode("utf-8")
            pts  = np.array([(p.x, p.y) for p in obj.polygon], dtype=np.int32)

            # Draw outline
            if len(pts) >= 4:
                cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
                cx, cy = pts[:, 0].mean().astype(int), pts[:, 1].mean().astype(int)
            else:  # Fallback to bounding box
                x, y, w, h = obj.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                cx, cy = x + w // 2, y + h // 2

            # Cool-down check
            now = time.time()
            if now - last_scan_ts.get(data, 0) >= SCAN_COOLDOWN:
                last_scan_ts[data] = now
                record_scan(data)
                refresh_table()
                root.bell()

                cv2.putText(
                    frame, "SCANNED", (cx - 60, cy + 15),
                    cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 255, 0), 3
                )

        # ---------- Scale & letter-box preview to TARGET_W×TARGET_H ----------
        h, w = frame.shape[:2]
        scale  = min(TARGET_W / w, TARGET_H / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h))

        canvas = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8)
        y_off  = (TARGET_H - new_h) // 2
        x_off  = (TARGET_W - new_w) // 2
        canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized

        # ---------- Display in Tkinter --------------------------------------
        img_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        lbl.imgtk = ImageTk.PhotoImage(Image.fromarray(img_rgb))
        lbl.configure(image=lbl.imgtk)
        win.after(15, update)

    update()

# ---------- 4. EXPORT ------------------------------------------------------
def export_csv() -> None:
    if not runs:
        messagebox.showwarning("Nothing to export", "No data has been recorded.")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile="run_results.csv",
    )
    if not path:
        return
    with open(path, "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(["id", "start", "end", "duration_seconds"])
        for pid, rec in runs.items():
            sec = (
                int((rec["end"] - rec["start"]).total_seconds())
                if rec["start"] and rec["end"] else ""
            )
            w.writerow([pid, iso(rec["start"]), iso(rec["end"]), sec])
    messagebox.showinfo("Export complete", f"Saved to:\n{path}")

# ---------- 5. BUTTONS -----------------------------------------------------
btns = tk.Frame(root)
btns.pack(fill=tk.X, padx=6, pady=(0, 6))

tk.Button(
    btns, text="Scan (preview)", height=2, width=18,
    command=handle_scan_preview
).pack(side=tk.LEFT, padx=4)

start_btn = tk.Button(
    btns, text="Start Race", height=2, width=12, bg="#e5ffe5",
    command=start_race
)
start_btn.pack(side=tk.LEFT, padx=4)

tk.Button(
    btns, text="Export CSV", height=2, width=12,
    command=export_csv
).pack(side=tk.LEFT, padx=4)

tk.Button(
    btns, text="Quit", height=2, width=8,
    command=root.destroy
).pack(side=tk.RIGHT, padx=4)

refresh_table()
root.mainloop()