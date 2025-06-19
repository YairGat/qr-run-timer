# QR Run Timer

> **Lightweight, webcam‑based stopwatch for races that use QR‑coded bibs.**

The application lets you **register multiple runners, start the race with a single gun time, and record each finisher automatically**—all from a live camera preview.

---

## ✨ Key features

- **Multi‑QR detection** – scans every code visible in the frame.
- **One‑click gun‑start** – assigns the same start time to all registered IDs.
- **10‑second re‑scan cooldown** (configurable).
- **Big green “SCANNED” overlay** + audible beep for clear feedback.
- **CSV export** (`id,start,end,duration_seconds`).
- Pure local execution ― Python + Tkinter + OpenCV (no cloud services).

---

## 📦 Repository description (for GitHub settings)

> *"Quick, local QR‑based timer for running events. Scans multiple bibs at once and exports results to CSV."*

Copy‑paste the line above into the **Description** field of the repo to help people understand the project at a glance.

---

## 🚀 Quick start

```bash
# 1) Clone the repo
$ git clone https://github.com/your‑org/qr‑run‑timer.git
$ cd qr‑run‑timer

# 2) Create & activate a virtual env (recommended)
$ python3 -m venv .venv
$ source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) Install dependencies
$ pip install -r requirements.txt

# 4) Run
$ python qr_run_timer.py
```

> **Works on macOS, Windows, and Linux.** Tested with Python 3.9–3.13 and OpenCV ≥ 4.5.

---

## 🛠️ Requirements

| Dependency                      | Tested version | Notes                                             |
| ------------------------------- | -------------- | ------------------------------------------------- |
| Python                          | ≥ 3.9          | any 64‑bit build                                  |
| OpenCV‑Python (`opencv-python`) | 4.11.0.86      | supplies `detectAndDecodeMulti`                   |
| Pillow                          | 10.3           | Tkinter image bridge                              |
| Tkinter                         | stdlib         | comes with most Python installers                 |
| Requests                        | 2.32           | only needed for the optional QR‑generation helper |

---

## 🖥️ Usage guide

| Action               | How‑to                                                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Register runners** | Click **“Scan QR (preview)”** and hold each bib up to the camera. Accepted codes flash “SCANNED”.                            |
| **Start race**       | Press **“Start Race”** once all runners are registered. Late arrivals scanned afterwards inherit the gun time automatically. |
| **Finish**           | Scan each runner at the finish line; the app records their end time and duration. Multiple runners can finish together.      |
| **Export results**   | Click **“Export CSV”**.                                                                                                      |

### Configuration

Open `qr_run_timer.py` and tweak these constants near the top:

```python
SCAN_COOLDOWN = 10          # seconds between scans of the same ID
FRAME_W, FRAME_H = 640, 480 # camera resolution
FRAME_SKIP = 2              # decode every N‑th frame (performance)
```

---

## 🤔 Troubleshooting

- **Webcam fails to open** – ensure no other application is using it; on macOS grant Camera permissions to Terminal/Python.
- **Low FPS / high latency** – lower `FRAME_W, FRAME_H`, or increase `FRAME_SKIP`.
- **No QR detected** – check lighting; glossy bibs cause glare.

---

## 🛣️ Roadmap

- Configurable cooldown per event.
- BLE/RFID tag support as drop‑in alternative.
- Local SQLite results DB + dashboard.
- Mobile app.
- Chip-based scanning (nfc or RFID).
