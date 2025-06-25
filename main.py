#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QR / BAR Run-Timer  –  Threaded, Adaptive Frame-Skip, Gray-scale
"""

# ---------- 0. IMPORTS & CONSTANTS -----------------------------------------
import csv, platform, time, threading, queue, re, logging
from datetime import datetime
from pathlib import Path

import cv2, numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SCAN_COOLDOWN  = 10                # s between identical IDs
TARGET_W, TARGET_H = 640, 480      # preview window
MAX_FRAME_SKIP = 6                 # upper bound for adaptive skip

ID_RE = re.compile(r'^[0-9]{6,12}$')  # דוגמה: 6-12 ספרות; שנה כראות עיניך

# ---------- 1. CAMERA THREAD ----------------------------------------------
class CameraThread(threading.Thread):
    """Pushes frames into a queue as fast as possible (dropping old ones)."""
    def __init__(self, q: queue.Queue, camera_idx: int = 0):
        super().__init__(daemon=True)
        self.q = q
        backend = cv2.CAP_AVFOUNDATION if platform.system() == "Darwin" else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(camera_idx, backend)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  TARGET_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_H)
        if not self.cap.isOpened():
            raise RuntimeError("Cannot open webcam")

    def run(self):
        while True:
            ok, frame = self.cap.read()
            if not ok:
                continue
            try:
                self.q.put_nowait(frame)
            except queue.Full:
                # queue full → throw away the oldest
                try: self.q.get_nowait()
                except queue.Empty: pass
                self.q.put_nowait(frame)

# ---------- 2. SCANNER LOGIC ----------------------------------------------
class Scanner:
    """Stateless helper that decodes bar/QR-codes from gray frames."""
    def __init__(self):
        self.last_scan_ts: dict[str, float] = {}
        self.frame_skip = 2  # starts low ⇒ snappy first detection

    def process(self, frame: np.ndarray, on_code_cb):
        """Possibly decode this frame; call `on_code_cb(data, polygon_pts, center)`."""
        # decide whether to skip this frame
        if self.frame_skip > 1:
            self.frame_skip -= 1
            return  # skip → just down-count

        self.frame_skip = 2  # reset; may rise again later
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found_any = False

        for obj in decode(gray):
            data = obj.data.decode("utf-8")
            if not ID_RE.fullmatch(data):
                continue          # ignore garbage
            now = time.time()
            if now - self.last_scan_ts.get(data, 0) < SCAN_COOLDOWN:
                continue          # cooldown
            self.last_scan_ts[data] = now
            found_any = True

            pts = np.array([(p.x, p.y) for p in obj.polygon], dtype=np.int32)
            if len(pts) < 4:      # fallback rectangle
                x, y, w, h = obj.rect
                pts = np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]])

            cx, cy = pts[:, 0].mean().astype(int), pts[:, 1].mean().astype(int)
            on_code_cb(data, pts, (cx, cy))

        # no code? ⇒ increase skip (max 6)
        if not found_any:
            self.frame_skip = min(self.frame_skip + 1, MAX_FRAME_SKIP)

# ---------- 3. MAIN APPLICATION (Tk) ---------------------------------------
class App:
    def __init__(self):
        # --- state --------------------------------------------------------
        self.runs: dict[str, dict[str, datetime | None]] = {}
        self.race_started   = False
        self.race_start_ts: datetime | None = None

        # --- Tk roots & widgets ------------------------------------------
        self.root = tk.Tk(); self.root.title("QR / BAR Run-Timer")
        self.root.geometry("760x500")
        ttk.Style(self.root).configure("Treeview", rowheight=26)

        cols = ("id", "start", "end", "duration")
        self.view = ttk.Treeview(self.root, columns=cols, show="headings")
        for c, head in zip(cols, ("ID", "Start", "End", "Duration (hh:mm:ss)")):
            self.view.heading(c, text=head); self.view.column(c, anchor=tk.CENTER)
        self.view.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # buttons
        btns = tk.Frame(self.root); btns.pack(fill=tk.X, padx=6, pady=(0, 6))
        tk.Button(btns, text="Scan (preview)", height=2, width=18,
                  command=self.start_preview).pack(side=tk.LEFT, padx=4)
        self.start_btn = tk.Button(btns, text="Start Race", height=2, width=12,
                                   bg="#e5ffe5", command=self.start_race)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Export CSV", height=2, width=12,
                  command=self.export_csv).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Quit", height=2, width=8,
                  command=self.root.destroy).pack(side=tk.RIGHT, padx=4)

        self.refresh_table()

    # ---------- table helpers -------------------------------------------
    iso = staticmethod(lambda dt: dt.isoformat(timespec="seconds") if dt else "")

    def refresh_table(self):
        self.view.delete(*self.view.get_children())
        for pid, rec in self.runs.items():
            dur = (str(rec["end"] - rec["start"]).split(".")[0]
                   if rec["start"] and rec["end"] else "")
            self.view.insert("", tk.END, values=(pid, self.iso(rec["start"]),
                                                 self.iso(rec["end"]), dur))
        self.root.title(f"Run-Timer – {len(self.runs)} runners")

    # ---------- race logic ---------------------------------------------
    def record_scan(self, pid: str):
        rec = self.runs.setdefault(pid, {"start": None, "end": None})
        if not self.race_started:
            return
        if rec["start"] is None:
            rec["start"] = self.race_start_ts; return
        if rec["end"] is None:
            rec["end"] = datetime.now();       return
        # laps
        lap = 1
        while f"{pid}_lap{lap}" in self.runs: lap += 1
        self.runs[f"{pid}_lap{lap}"] = {"start": self.race_start_ts, "end": datetime.now()}

    def start_race(self):
        if self.race_started or not self.runs:
            if not self.runs:
                messagebox.showwarning("No runners", "Register at least one runner before starting.")
            return
        self.race_start_ts = datetime.now()
        self.race_started  = True
        for rec in self.runs.values(): rec["start"] = self.race_start_ts
        self.refresh_table()
        self.start_btn.config(state=tk.DISABLED)
        self.root.bell()
        messagebox.showinfo("Race started!", f"Gun time: {self.iso(self.race_start_ts)}")

    # ---------- CSV export ---------------------------------------------
    def export_csv(self):
        if not self.runs:
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
            # ★ כותרת חדשה – בפורמט mm:ss:ms
            w = csv.writer(fp)
            w.writerow(["id", "start", "end", "duration_mm:ss:ms"])

            for pid, rec in self.runs.items():
                if rec["start"] and rec["end"]:
                    td = rec["end"] - rec["start"]  # timedelta
                    minutes, seconds = divmod(td.seconds, 60)
                    millis = td.microseconds // 1_000
                    duration_str = f"{minutes:02d}:{seconds:02d}:{millis:03d}"
                else:
                    duration_str = ""

                w.writerow([pid, self.iso(rec["start"]),
                            self.iso(rec["end"]), duration_str])

        messagebox.showinfo("Export complete", f"Saved to:\n{path}")

    # ---------- preview window ----------------------------------------
    def start_preview(self):
        # create camera thread & queue once
        q = queue.Queue(maxsize=4)
        try:
            cam_thread = CameraThread(q)
        except RuntimeError as e:
            messagebox.showerror("Camera error", str(e)); return
        cam_thread.start()

        scanner = Scanner()

        win = tk.Toplevel(self.root); win.title("Scanner – Esc to close")
        win.geometry(f"{TARGET_W}x{TARGET_H}")
        lbl = tk.Label(win); lbl.pack(expand=True)
        win.bind("<Escape>", lambda *_: win.destroy())

        def on_code(data, pts, center):
            self.record_scan(data); self.refresh_table(); self.root.bell()
            # draw feedback
            cv2.polylines(frame, [pts], True, (0,255,0), 3)
            cx, cy = center
            cv2.putText(frame, "SCANNED", (cx-60, cy+15),
                        cv2.FONT_HERSHEY_DUPLEX, 1.4, (0,255,0), 3)

        def update():
            try:
                global frame
                frame = q.get_nowait()
            except queue.Empty:
                win.after(10, update); return

            scanner.process(frame, on_code)

            # letter-box & display
            h, w = frame.shape[:2]; scale = min(TARGET_W/w, TARGET_H/h)
            resized = cv2.resize(frame, (int(w*scale), int(h*scale)))
            canvas  = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8)
            yoff    = (TARGET_H - resized.shape[0])//2
            xoff    = (TARGET_W - resized.shape[1])//2
            canvas[yoff:yoff+resized.shape[0], xoff:xoff+resized.shape[1]] = resized
            img = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
            lbl.imgtk = ImageTk.PhotoImage(Image.fromarray(img))
            lbl.configure(image=lbl.imgtk)
            win.after(10, update)

        update()

# ---------- 4. ENTRY-POINT -----------------------------------------------
if __name__ == "__main__":
    App().root.mainloop()