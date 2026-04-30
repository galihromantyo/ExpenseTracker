# 💰 FinTrack Bot — AI-Powered Personal Expense Tracker & Budget Manager

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Telegram-26A5E4?logo=telegram&logoColor=white)
![AI](https://img.shields.io/badge/AI-Gemini%20%7C%20OpenAI-orange?logo=google&logoColor=white)
![Storage](https://img.shields.io/badge/Storage-Google%20Sheets-34A853?logo=googlesheets&logoColor=white)

Telegram chatbot untuk mencatat pengeluaran dan memantau budget pribadi secara otomatis, didukung AI. Dirancang untuk pengguna Indonesia yang tinggal di **Jakarta maupun London** — mendukung metode pembayaran lokal kedua kota, multi-currency (IDR, USD, EUR, GBP), serta visualisasi laporan dengan konversi kurs live.

Input cukup kirim **teks, foto struk, PDF, atau voice note** — AI agent mengekstrak, menormalisasi, lalu menyimpan ke Google Sheets.

---

## Features

- **Multi-input** — text, foto struk (vision AI), PDF, voice note (speech-to-text)
- **AI extraction** — Gemini (default) atau OpenAI GPT-4o; auto-deteksi nominal, tanggal, kategori, metode bayar
- **Multi-currency** — IDR, USD, EUR, GBP; konversi live via [frankfurter.app](https://www.frankfurter.app/) saat laporan
- **Budget management** — set budget total atau per kategori, untuk bulan apa saja (historis, berjalan, mendatang)
- **Budget review** — tampilkan budget yang sudah ada sebelum mengubah; pilih Tetap / Ganti / Hapus
- **Laporan visual** — bar chart atau pie chart opsional, on-demand
- **CSV export** — export transaksi untuk rentang bulan tertentu
- **Edit & hapus** — koreksi atau hapus transaksi via inline keyboard

---

## Architecture

```
Telegram Bot
     │
     ▼
 Command Router
     │
     ├──── Flow A: Input Expense ──────────────────────────────────────────────┐
     │          │                                                                │
     │    Input Handler                                                          │
     │    ├── Text     → (raw text)       ─┐                                    │
     │    ├── Photo    → Vision AI OCR    ─┤→ Extraction Agent                 │
     │    ├── PDF      → PDF-to-text      ─┤   (Gemini/OpenAI)                 │
     │    └── Voice    → Speech-to-text   ─┘   ↓                               │
     │                                     Normalize Agent                      │
     │                                     (tanggal, nominal, mata uang,        │
     │                                      kategori, metode bayar)             │
     │                                          ↓                               │
     │                                     Verification via Bot                 │
     │                                     (user confirm / edit / batal)        │
     │                                          ↓                               │
     │                                     Google Sheets Writer Agent ──────────┘
     │                                     (append row ke sheet Expenses)
     │
     └──── Flow B: Budget & Report ────────────────────────────────────────────┐
                │                                                                │
          Input: bulan & tahun (default: bulan berjalan)                       │
                │                                                                │
          Sheets Reader Agent                                                    │
          (cek budget & expenses bulan tsb)                                    │
                │                                                                │
         [/budget] Budget sudah ada?                                            │
                ├── Ya  → Tampilkan budget + pilihan:                          │
                │         [✅ Tetap] [✏️ Ganti] [🗑️ Hapus]                      │
                └── Tidak → Tanya jenis budget:                                │
                            [📦 Total] [📂 Per Kategori]                        │
                                 ↓                                              │
                            Budget Writer Agent → Google Sheets                 │
                                                                                │
         [/laporan] Ada multi-currency?                                        │
                ├── Ya → "Konversi ke [IDR]?" atau "Pisah per mata uang?"     │
                │              ↓                                                │
                │         Currency Agent (frankfurter.app)                     │
                └── Tidak → lanjut langsung                                    │
                                 ↓                                              │
          Report Agent → kirim laporan teks                                    │
                │                                                                │
          Tanya: "Mau lihat chart? 📊"                                         │
          ┌─────┴─────┐                                                         │
         Ya          Tidak                                                       │
          │            └─ Selesai                                                │
     Chart Agent                                                                 │
     (bar/pie PNG) ──────────────────────────────────────────────────────────┘
```

---

## Agent Roster

| Agent | Tugas | Model / Tool |
|---|---|---|
| `command_router` | Parse perintah Telegram, routing ke flow yang tepat | Python logic |
| `input_handler` | Terima & preprocess input (text/photo/PDF/voice) | Telegram Bot API |
| `extraction_agent` | Ekstrak tanggal, nominal, mata uang, kategori, metode bayar | Gemini (configurable) / GPT-4o |
| `normalize_agent` | Normalisasi data: format tanggal ISO, konversi `k`/`m`/`rb`/`jt`, standarisasi mata uang & metode bayar | Python |
| `verification_agent` | Kirim ringkasan hasil ekstraksi ke user, minta konfirmasi sebelum disimpan | Telegram inline keyboard |
| `sheets_writer_agent` | Append / update / delete baris di sheet `Expenses` | Google Sheets API |
| `sheets_reader_agent` | Baca data budget dan pengeluaran bulan tertentu | Google Sheets API |
| `budget_writer_agent` | Insert, replace, atau hapus budget di sheet `Budget` | Google Sheets API |
| `currency_agent` | Ambil live exchange rate dari frankfurter.app; konversi saat laporan | httpx + frankfurter.app |
| `report_agent` | Kalkulasi sisa budget total dan per kategori, format pesan laporan | Python |
| `chart_agent` | Generate bar/pie chart dari data pengeluaran (opsional, on-demand) | Matplotlib + Pillow |
| `export_agent` | Generate dan kirim file CSV ringkasan transaksi | Python csv module |

---

## Multi-Currency Support

Mata uang yang didukung: **IDR**, **USD**, **EUR**, **GBP**

### Auto-detection dari input

| Input contoh | Terdeteksi |
|---|---|
| `Rp 25.000`, `25rb`, `25k`, `IDR 25000` | IDR |
| `$25`, `25 USD`, `25 dollar` | USD |
| `€25`, `25 EUR`, `25 euro` | EUR |
| `£25`, `25 GBP`, `25 pound` | GBP |
| (tidak ada simbol) | Default currency user |

Konversi hanya terjadi **saat laporan** — data asli selalu disimpan dalam mata uang original.

### Konversi di level laporan

Saat laporan berisi transaksi multi-currency, bot menawarkan:

1. **Konversi ke default currency** — live rate dari frankfurter.app, ditampilkan di footer laporan
2. **Tampilkan terpisah per mata uang** — tanpa konversi, dikelompokkan per currency

Data asli di Google Sheets **tidak pernah diubah**.

---

## Google Sheets Structure

### Sheet: `Expenses`

| Kolom | Keterangan | Contoh |
|---|---|---|
| `date` | Tanggal transaksi (ISO 8601) | `2026-04-28` |
| `description` | Deskripsi singkat | `Makan siang di warteg` |
| `amount` | Nominal asli (desimal, tanpa simbol) | `25000` |
| `currency` | Kode mata uang asli | `IDR` |
| `category` | Kategori pengeluaran | `Food & Dining` |
| `payment_method` | Metode pembayaran | `GoPay` |
| `input_type` | Jenis input asal | `photo` |
| `created_at` | Timestamp dicatat (ISO 8601) | `2026-04-28T13:00:00+00:00` |

### Sheet: `Budget`

| Kolom | Keterangan | Contoh |
|---|---|---|
| `month` | Bulan (format `YYYY-MM`) | `2026-04` |
| `currency` | Kode mata uang budget | `IDR` |
| `budget_type` | `total` atau `per_category` | `per_category` |
| `category` | Nama kategori (kosong jika `total`) | `Food & Dining` |
| `amount` | Nominal budget | `1000000` |
| `notes` | Catatan opsional | `-` |

> Kedua sheet dibuat otomatis oleh bot saat pertama kali dijalankan.

---

## Expense Categories

| Kategori | Relevansi |
|---|---|
| `Rent & Housing` | Sewa apartemen/kos — prioritas di Jakarta & London |
| `Groceries` | Belanja bahan makanan |
| `Food & Dining` | Restoran, kafe, takeaway |
| `Transport` | Ojek, KRL, TfL/Oyster, Grab, Gojek, Uber |
| `Travel` | Tiket pesawat, hotel — relevan untuk rute Jakarta–London |
| `Shopping` | Pakaian, elektronik, barang rumah tangga |
| `Health & Medical` | Dokter, obat, gym |
| `Utilities & Bills` | Listrik, air, internet, council tax (UK) |
| `Subscriptions` | Netflix, Spotify, iCloud, aplikasi bulanan |
| `Education` | Kursus, buku |
| `Insurance` | Asuransi jiwa, kesehatan, kendaraan |
| `Remittance` | Transfer antarnegara (Wise, Revolut, dll) |
| `Entertainment` | Bioskop, konser, hobi |
| `Personal Care` | Salon, kosmetik, perawatan diri |
| `Other` | Pengeluaran di luar kategori lain |

---

## Data Normalization Rules

### Normalisasi nominal

| Input | Hasil |
|---|---|
| `25k`, `25rb`, `25K` | `25000` |
| `1.5jt`, `1.5m`, `1.5juta` | `1500000` |
| `£1,200.50` | `1200.50` (GBP) |
| `1.000,50` | `1000.50` (format Eropa/IDR) |

### Normalisasi tanggal

| Input | Hasil |
|---|---|
| `kemarin`, `yesterday` | tanggal hari sebelumnya |
| `tadi`, `today`, `hari ini` | tanggal hari ini |
| `28 April`, `April 28`, `28 Apr` | `2026-04-28` |

### Normalisasi metode pembayaran

#### Indonesia
| Input | Hasil |
|---|---|
| `gopay`, `ovo`, `dana`, `shopeepay`, `linkaja`, `qris`, `jenius`, `flip` | nama asli (case-normalized) |
| `bca`, `mandiri`, `bri`, `bni`, `cimb`, `tf`, `transfer` | `Bank Transfer` |
| `tunai`, `cash` | `Cash` |

#### UK & Internasional
| Input | Hasil |
|---|---|
| `revolut`, `monzo`, `starling` | nama asli |
| `apple pay`, `applepay` | `Apple Pay` |
| `google pay`, `gpay` | `Google Pay` |
| `wise`, `transferwise` | `Wise` |
| `paypal` | `PayPal` |
| `contactless` | `Contactless` |
| `barclays`, `hsbc`, `lloyds`, `natwest`, `santander` | `Bank Transfer` |
| `cc`, `credit card`, `kartu kredit` | `Credit Card` |
| `amex`, `american express` | `American Express` |

---

## User Flow Detail

### Flow A — Input Expense

```
User kirim pesan / foto / PDF / voice note
        ↓
Bot: "⏳ Sedang memproses input kamu..."
        ↓
AI ekstrak & normalisasi data
        ↓
Bot kirim konfirmasi:
  ┌────────────────────────────────┐
  │  📋 Konfirmasi Transaksi        │
  │  📅 Tanggal   : 28 April 2026  │
  │  💰 Nominal   : £ 12.50        │
  │  💱 Mata Uang : GBP            │
  │  🏷️  Kategori  : Food & Dining  │
  │  💳 Bayar via : Monzo           │
  │  📝 Deskripsi : Lunch Pret      │
  │  [✅ Simpan] [✏️ Edit] [❌ Batal] │
  └────────────────────────────────┘
        ↓
[✅ Simpan] → Data masuk Google Sheets
[✏️ Edit]   → Pilih field (tanggal/nominal/kategori/dll) → edit → kembali ke konfirmasi
[❌ Batal]  → Flow dibatalkan
```

### Flow B — Budget Management (`/budget`)

```
/budget [bulan]
        ↓
Jika tanpa parameter → pilih bulan via inline keyboard
        ↓
Bot cek budget bulan tsb di Google Sheets

  Sudah ada budget?
  ├── Ya  → Tampilkan budget yang ada:
  │         💰 Budget April 2026 sudah ada:
  │         📦 Total: £ 3,000.00
  │         Mau diapakan?
  │         [✅ Tetap] [✏️ Ganti] [🗑️ Hapus] [❌ Batal]
  │
  └── Tidak → Pilih jenis budget:
              [📦 Total saja] [📂 Per kategori]
              ↓
              Input nominal → Tersimpan ke Google Sheets
```

### Flow C — Budget Report (`/laporan`)

```
/laporan [bulan]
        ↓
Agent ambil expenses + budget bulan tsb
        ↓
Ada multi-currency?
├── Ya  → "Konversi ke IDR?" atau "Pisah per mata uang?"
│         → Currency Agent ambil live rate dari frankfurter.app
└── Tidak → lanjut langsung
        ↓
Bot kirim laporan teks
  - Budget belum diset: catatan "gunakan /budget untuk mengatur"
  - Budget sudah ada: perbandingan budget vs pengeluaran per kategori
        ↓
"Mau lihat chart? [📊 Bar] [🥧 Pie] [⏭️ Tidak perlu]"
```

Contoh output laporan:
```
📊 Laporan April 2026
──────────────────────────────────
💰 Budget Total  : £ 3,000.00
📤 Total Keluar  : £ 2,340.00  (78%)
💵 Sisa Budget   : £   660.00  (22%)

📂 Per Kategori:
🏠 Rent          : £ 1,800.00
🍽️ Food & Dining : £   280.00  (sisa £ 20.00)
🚇 Transport     : £    95.00
🛍️ Shopping      : £   165.00  ⚠️ lewat budget
──────────────────────────────────
💱 Rate: 1 GBP = Rp 20.250
📌 Rate diambil: 30 Apr 2026 via frankfurter.app
```

---

## Telegram Bot Commands

| Command | Deskripsi |
|---|---|
| `/start` | Mulai bot, tampilkan menu utama |
| `/input` | Mulai input expense secara eksplisit |
| `/laporan [bulan tahun]` | Lihat laporan pengeluaran & budget |
| `/budget [bulan tahun]` | Set, ganti, atau hapus budget |
| `/history [N]` | Lihat N transaksi terakhir (default: 10) |
| `/edit` | Edit transaksi via inline keyboard |
| `/hapus` | Hapus transaksi via inline keyboard |
| `/export [bulan-awal] [bulan-akhir]` | Export CSV |
| `/setcurrency` | Ubah mata uang default (IDR / USD / EUR / GBP) |
| `/help` | Tampilkan panduan |

Untuk input expense, tidak perlu command — langsung kirim teks, foto, PDF, atau voice note.

**Contoh command dengan parameter:**
```
/laporan April 2026
/laporan 2026-03
/budget Maret 2026
/export Jan 2026 Apr 2026
/history 20
```

---

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Bot framework | `python-telegram-bot` v20.7 (async) |
| AI extraction (default) | Google Gemini (configurable via `GEMINI_MODEL`) |
| AI extraction (opsional) | OpenAI GPT-4o |
| Speech-to-text | Gemini multimodal / OpenAI Whisper |
| PDF parsing | `pymupdf` (fitz) |
| Google Sheets | `gspread` + Google Service Account |
| Live exchange rate | `frankfurter.app` (gratis, tanpa API key) |
| Chart generation | `matplotlib` + `pillow` |
| CSV export | Python built-in `csv` module |
| Runtime | Python 3.11+ |
| Config | `.env` via `python-dotenv` |

---

## Project Structure

```
agen_exptrackerviz/
├── app.py                      # Entry point — Telegram bot setup & polling
├── config.py                   # Load & validasi env vars
│
├── agents/
│   ├── extraction_agent.py     # AI extraction (Gemini/OpenAI), text/image/audio
│   ├── normalize_agent.py      # Normalisasi nominal, tanggal, metode bayar, kategori
│   ├── sheets_agent.py         # Read/write/delete Google Sheets (async wrapper)
│   ├── currency_agent.py       # Live exchange rate via frankfurter.app
│   ├── report_agent.py         # Kalkulasi budget & format laporan
│   ├── chart_agent.py          # Generate bar/pie chart (opsional, on-demand)
│   └── export_agent.py         # Generate CSV export (UTF-8 BOM untuk Excel)
│
├── handlers/
│   ├── command_handler.py      # Handler semua slash commands
│   ├── input_handler.py        # Routing text/photo/PDF/voice + state machine
│   └── callback_handler.py     # Inline keyboard callbacks (confirm, edit, budget, dll)
│
├── utils/
│   ├── constants.py            # CATEGORIES, CATEGORY_EMOJI, Sheets headers
│   ├── currency.py             # Deteksi & normalisasi mata uang, format nominal
│   ├── date_parser.py          # Parse ekspresi tanggal relatif & berbagai format
│   ├── formatter.py            # Format pesan Telegram (laporan, konfirmasi)
│   └── state.py                # State machine constants & helpers (flow/step/data)
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup & Installation

### 1. Clone & buat virtual environment

```bash
git clone <repo-url>
cd agen_exptrackerviz

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Google Cloud & Sheets setup

1. Buat Google Spreadsheet baru (biarkan kosong)
2. Buka [Google Cloud Console](https://console.cloud.google.com)
3. Buat project → aktifkan **Google Sheets API** dan **Google Drive API**
4. **IAM & Admin → Service Accounts → Create Service Account**
5. Download JSON key dari service account yang dibuat
6. Share spreadsheet ke email service account (`xxx@project.iam.gserviceaccount.com`) dengan akses **Editor**

> Sheet `Expenses` dan `Budget` beserta header-nya dibuat otomatis oleh bot saat pertama dijalankan.

### 4. Telegram Bot

1. Buka [@BotFather](https://t.me/BotFather) → `/newbot`
2. Salin **Bot Token** yang diberikan

### 5. AI API Key

- **Gemini (default):** [Google AI Studio](https://aistudio.google.com/) → Get API Key → pastikan billing aktif di project Google Cloud untuk menghindari quota limit
- **OpenAI (opsional):** [platform.openai.com](https://platform.openai.com) → API Keys

### 6. Konfigurasi `.env`

Salin template dan isi nilainya:

```bash
cp .env.example .env
```

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# AI Provider: "gemini" atau "openai"
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash          # opsional, default: gemini-2.0-flash
OPENAI_API_KEY=                        # isi jika AI_PROVIDER=openai

# Google Sheets
GOOGLE_SHEETS_ID=your_spreadsheet_id

# Opsi A — path ke file JSON (untuk lokal):
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/service-account.json
# Opsi B — paste isi JSON sebagai satu baris (untuk cloud deploy):
# GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}

# Default currency: IDR | USD | EUR | GBP
DEFAULT_CURRENCY=IDR
```

### 7. Jalankan bot

```bash
python app.py
```

---

## Assumptions & Design Decisions

| Keputusan | Alasan |
|---|---|
| Single user | Satu bot instance untuk satu pengguna; tidak perlu isolasi data per `chat_id` |
| Gemini sebagai default AI | Multimodal (vision + audio dalam satu model); model dapat dikonfigurasi via `GEMINI_MODEL` |
| Konversi currency hanya di level laporan | Tidak ada dependency live rate saat input — UX lebih cepat, data asli tetap utuh |
| Data asli disimpan dalam currency original | Nilai historis tidak rusak akibat fluktuasi kurs |
| frankfurter.app untuk exchange rate | Gratis, tanpa API key, mendukung IDR/USD/EUR/GBP |
| Budget review sebelum overwrite | User bisa melihat budget yang ada lalu memilih tetap/ganti/hapus alih-alih langsung ditimpa |
| Budget & laporan untuk bulan apa saja | Pengguna bisa input telat atau cek historis — tidak terbatas bulan berjalan |
| Chart bersifat on-demand | Mengurangi waktu proses; dibuat hanya saat user minta |
| Verifikasi wajib sebelum simpan | AI tidak 100% akurat; konfirmasi mencegah data salah masuk |
| Kategori mencakup Jakarta + London | Rent, Remittance, Council Tax relevan untuk kedua konteks |
| `/setcurrency` bersifat in-memory | Perubahan aktif selama sesi bot; untuk permanen, edit `DEFAULT_CURRENCY` di `.env` lalu restart |
| Virtual environment direkomendasikan | Menghindari konflik dependency dengan package global (misal `httpx` yang dibutuhkan PTB ~0.25) |

---

## Future Development

### Near-term
- **Multi-user support** — partisi data per `chat_id`, deploy sebagai shared bot
- **Recurring expense** — catat pengeluaran rutin bulanan yang otomatis ditambahkan
- **Budget alert** — notifikasi jika pengeluaran kategori mendekati atau melewati budget
- **Export ke Excel (.xlsx)** — format dengan warna dan formula via `openpyxl`

### Mid-term
- **Laporan komparatif** — bandingkan bulan ini vs bulan lalu atau rata-rata 3 bulan
- **Web dashboard** — visualisasi interaktif via Streamlit menggunakan data Sheets yang sama
- **Budget template** — simpan template dan terapkan ulang tiap bulan
- **Cached exchange rate** — simpan rate harian di Sheets untuk menghindari hit API berulang

### Long-term
- **Integrasi bank statement** — auto-parse PDF mutasi BCA, Mandiri, Barclays, Monzo
- **AI insight** — analisis pola pengeluaran dan rekomendasi efisiensi
- **Multi-platform** — support WhatsApp atau LINE
- **Currency tambahan** — SGD, AUD, JPY

---

## License

MIT License — Copyright (c) 2026 Galih Romantyo

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Developer

**Galih Romantyo** · [galihromantyo@gmail.com](mailto:galihromantyo@gmail.com)

> Dibuat sebagai bagian dari eksplorasi AI Agent untuk personal finance management.
