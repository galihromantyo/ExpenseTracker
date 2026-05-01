# 💰 FinTrack — AI-Powered Personal Finance Tracker

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Telegram-26A5E4?logo=telegram&logoColor=white)
![AI](https://img.shields.io/badge/AI-Gemini%20%7C%20OpenAI-orange?logo=google&logoColor=white)
![Storage](https://img.shields.io/badge/Storage-Google%20Sheets-34A853?logo=googlesheets&logoColor=white)
![Dashboard](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)

Telegram chatbot untuk mencatat pengeluaran dan memantau budget pribadi secara otomatis, didukung AI. Dirancang untuk pengguna Indonesia yang tinggal di **Jakarta maupun London** — mendukung metode pembayaran lokal kedua kota, multi-currency (IDR, USD, EUR, GBP), serta laporan dengan konversi kurs live.

Input cukup kirim **teks, foto struk, PDF, atau voice note** — AI agent mengekstrak, menormalisasi, lalu menyimpan ke Google Sheets. Data bisa dijelajahi lewat **Streamlit Dashboard** dengan analitik interaktif dan **AI Analysis** yang bisa menjawab pertanyaan keuangan dalam bahasa natural.

---

## Features

### v1 — Core Bot
- **Multi-input** — teks, foto struk (vision AI), PDF, voice note (speech-to-text)
- **AI extraction** — Gemini (default) atau OpenAI GPT-4o; auto-deteksi nominal, tanggal, kategori, metode bayar
- **Verifikasi sebelum simpan** — konfirmasi + edit inline sebelum data masuk ke Sheets
- **Multi-currency** — IDR, USD, EUR, GBP; konversi live via [frankfurter.app](https://www.frankfurter.app/) saat laporan
- **Budget management** — set budget total atau per kategori; tampilkan existing → pilih Tetap / Ganti / Hapus
- **Laporan bulanan** — bar chart atau pie chart opsional, on-demand
- **Edit & hapus** — koreksi atau hapus transaksi via inline keyboard
- **CSV export** — export transaksi untuk rentang bulan tertentu

### v2 — Multi-User & Dashboard
- **Multi-user** — partisi data per `chat_id`; setiap user punya data dan preferensi mata uang sendiri
- **Auto-registrasi** — `/start` daftarkan user baru secara otomatis, tanpa interupsi
- **Preferensi currency persistent** — `/setcurrency` simpan pilihan ke Sheets, tidak hilang saat bot restart
- **Password dashboard** — `/setpassword` untuk set password login dashboard (bcrypt hash disimpan ke Sheets)
- **AI Q&A `/tanya`** — tanya data transaksi dalam bahasa natural, dijawab Gemini (konteks 6 bulan terakhir)
- **Streamlit Dashboard** — analitik interaktif per-user dengan login terproteksi:
  - **Overview** — KPI cards (total keluar MoM%, sisa budget, jumlah transaksi), bar chart top kategori, treemap proporsi pengeluaran
  - **Trends** — line chart total bulanan, stacked bar per kategori, heatmap intensitas pengeluaran per hari × minggu
  - **Budget vs Aktual** — bullet chart per kategori (budget sebagai bar referensi, aktual di atasnya), cumulative spending line vs batas budget, progress bar per kategori
  - **Transaksi** — tabel filterable (tanggal, kategori, metode bayar, keyword) + export CSV
  - **Analisa AI** — Q&A ringan (seperti `/tanya`) dan analisa mendalam 5-bagian dengan rekomendasi konkret, hasil bisa di-download
  - **Admin** — agregat semua user, pengeluaran per user, daftar user terdaftar (superuser only)
- **Dua-spreadsheet model** — `MODE=prod/test` untuk switch antara data nyata dan data testing tanpa ubah kode
- **Test dataset** — `seed_test_data.py` generate data sintetis Feb–Mei 2026 untuk 3 user ke spreadsheet testing terpisah

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
     │                                     Verifikasi via Bot                   │
     │                                     (user confirm / edit / batal)        │
     │                                          ↓                               │
     │                                     Google Sheets Writer ────────────────┘
     │
     ├──── Flow B: Budget & Report ───────────────────────────────────────────┐
     │            │                                                             │
     │      Input: bulan & tahun (default: bulan berjalan)                    │
     │            │                                                             │
     │      Sheets Reader (filter per chat_id)                                 │
     │            │                                                             │
     │     [/budget] Budget sudah ada?                                         │
     │            ├── Ya  → [✅ Tetap] [✏️ Ganti] [🗑️ Hapus]                   │
     │            └── Tidak → [📦 Total] [📂 Per Kategori]                     │
     │                             ↓                                           │
     │                        Budget Writer → Google Sheets                    │
     │                                                                         │
     │     [/laporan] Ada multi-currency?                                      │
     │            ├── Ya → Currency Agent (frankfurter.app) → konversi        │
     │            └── Tidak → lanjut langsung                                  │
     │                             ↓                                           │
     │      Report Agent → kirim laporan teks + opsional chart ───────────────┘
     │
     └──── Flow C: AI Q&A (/tanya) ─────────────────────────────────────────┐
                │                                                              │
          Query Agent: fetch 6 bulan expenses + budget dari Sheets           │
                │                                                              │
          Gemini: terima context JSON + pertanyaan → jawab bahasa natural     │
                │                                                              │
          Bot reply ────────────────────────────────────────────────────────┘

Streamlit Dashboard (berjalan terpisah, baca Sheets yang sama)
     │
     ├── Auth gate (login per-user, bcrypt password)
     ├── Overview     → KPI cards, bar chart, treemap
     ├── Trends       → line chart, stacked bar, heatmap (hari × minggu)
     ├── Budget       → bullet chart, cumulative line, progress bar
     ├── Transaksi    → tabel filterable, export CSV
     ├── Analisa AI   → Q&A ringan + analisa mendalam 5-bagian
     └── Admin        → agregat semua user (superuser only)
```

---

## Agent Roster

| Agent | Tugas | Model / Tool |
|---|---|---|
| `extraction_agent` | Ekstrak tanggal, nominal, mata uang, kategori, metode bayar dari semua jenis input | Gemini / GPT-4o |
| `normalize_agent` | Normalisasi data: format ISO date, konversi `k`/`m`/`jt`, standarisasi payment method | Python |
| `sheets_agent` | Read/write/delete Google Sheets — Expenses, Budget, Users (async, partisi per `chat_id`) | gspread |
| `user_agent` | Register user baru, get/set preferensi currency & password per `chat_id` | gspread |
| `query_agent` | Fetch data Sheets sebagai JSON context + kirim ke Gemini untuk AI Q&A | Gemini + gspread |
| `currency_agent` | Ambil live exchange rate; konversi saat laporan atau saat diminta | frankfurter.app |
| `report_agent` | Kalkulasi budget vs aktual, format laporan teks | Python |
| `chart_agent` | Generate bar/pie chart sebagai gambar (Telegram, on-demand) | Matplotlib + Pillow |
| `export_agent` | Generate file CSV dengan UTF-8 BOM (Excel-compatible) | Python csv |

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
| (tidak ada simbol) | Preferensi default user (dari sheet `Users`) |

Konversi hanya terjadi **saat laporan** — data asli selalu disimpan dalam mata uang original.

---

## Google Sheets Structure

> Semua sheet dibuat otomatis oleh bot saat pertama kali dijalankan.

### Sheet: `Expenses`

| Kolom | Keterangan | Contoh |
|---|---|---|
| `chat_id` | Telegram user ID (partisi multi-user) | `123456789` |
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
| `chat_id` | Telegram user ID | `123456789` |
| `month` | Bulan (format `YYYY-MM`) | `2026-04` |
| `currency` | Kode mata uang budget | `IDR` |
| `budget_type` | `total` atau `per_category` | `per_category` |
| `category` | Nama kategori (kosong jika `total`) | `Food & Dining` |
| `amount` | Nominal budget | `1000000` |
| `notes` | Catatan opsional | `-` |

### Sheet: `Users`

| Kolom | Keterangan | Contoh |
|---|---|---|
| `chat_id` | Telegram user ID (primary key) | `123456789` |
| `username` | Username Telegram | `galihromantyo` |
| `display_name` | Nama tampilan | `Galih` |
| `default_currency` | Preferensi mata uang per-user | `GBP` |
| `joined_at` | Waktu registrasi (ISO 8601) | `2026-05-01T09:00:00+00:00` |
| `is_active` | Status aktif | `True` |
| `password_hash` | bcrypt hash untuk login dashboard (opsional) | `$2b$12$...` |

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
| `28/04/26`, `28/04/2026` | `2026-04-28` (DD/MM/YY format struk UK) |
| `28 April 2026`, `April 28, 2026` | `2026-04-28` |

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

## Telegram Bot Commands

| Command | Deskripsi |
|---|---|
| `/start` | Registrasi otomatis (jika baru), tampilkan info mata uang default |
| `/input` | Mulai input expense secara eksplisit |
| `/laporan [bulan tahun]` | Lihat laporan pengeluaran & budget bulanan |
| `/budget [bulan tahun]` | Set, ganti, atau hapus budget |
| `/tanya [pertanyaan]` | Tanya data transaksi dalam bahasa natural via AI |
| `/history [N]` | Lihat N transaksi terakhir (default: 10) |
| `/edit` | Edit transaksi via inline keyboard |
| `/hapus` | Hapus transaksi via inline keyboard |
| `/export [bulan-awal] [bulan-akhir]` | Export CSV |
| `/setcurrency` | Ubah dan simpan mata uang default (persistent ke Sheets) |
| `/setpassword [password]` | Set password untuk login Streamlit Dashboard (min. 6 karakter) |
| `/help` | Tampilkan panduan lengkap |

---

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Bot framework | `python-telegram-bot` v20.7 (async) |
| AI extraction & Q&A (default) | Google Gemini (configurable via `GEMINI_MODEL`) |
| AI extraction & Q&A (opsional) | OpenAI GPT-4o |
| Speech-to-text | Gemini multimodal / OpenAI Whisper |
| PDF parsing | `pymupdf` (fitz) |
| Google Sheets | `gspread` + Google Service Account |
| Live exchange rate | `frankfurter.app` (gratis, tanpa API key) |
| Chart (Telegram) | `matplotlib` + `pillow` |
| Dashboard | `streamlit` |
| Dashboard charts | `plotly` (bar, treemap, heatmap, cumulative line, bullet chart) |
| Data manipulation | `pandas` |
| Dashboard auth | `bcrypt` password hashing + Streamlit session state |
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
│   ├── sheets_agent.py         # Read/write/delete Google Sheets — Expenses, Budget, Users
│   ├── user_agent.py           # Register user, get/set preferensi & password per chat_id
│   ├── query_agent.py          # AI Q&A /tanya — fetch Sheets context + Gemini
│   ├── currency_agent.py       # Live exchange rate via frankfurter.app
│   ├── report_agent.py         # Kalkulasi budget & format laporan
│   ├── chart_agent.py          # Generate bar/pie chart (Telegram, on-demand)
│   └── export_agent.py         # Generate CSV export (UTF-8 BOM)
│
├── handlers/
│   ├── command_handler.py      # Handler semua slash commands
│   ├── input_handler.py        # Routing text/photo/PDF/voice + state machine
│   └── callback_handler.py     # Inline keyboard callbacks
│
├── utils/
│   ├── constants.py            # CATEGORIES, CATEGORY_EMOJI, Sheets headers
│   ├── currency.py             # Deteksi & normalisasi mata uang, format nominal
│   ├── date_parser.py          # Parse berbagai format tanggal
│   ├── formatter.py            # Format pesan Telegram (laporan, konfirmasi)
│   └── state.py                # State machine constants & helpers
│
├── dashboard/                  # Streamlit Dashboard (jalankan terpisah dari bot)
│   ├── app.py                  # Entry point, sidebar navigasi, routing antar halaman
│   ├── auth.py                 # Login per-user + session management (60 menit)
│   ├── data_loader.py          # Baca Google Sheets, cache TTL 5 menit
│   └── pages/
│       ├── overview.py         # KPI cards, bar chart, treemap
│       ├── trends.py           # Line chart bulanan, stacked bar, heatmap hari × minggu
│       ├── budget.py           # Bullet chart, cumulative line, progress bar
│       ├── transactions.py     # Tabel filterable, export CSV
│       ├── analysis.py         # AI Q&A + analisa mendalam dengan rekomendasi
│       └── admin.py            # Agregat semua user (superuser only)
│
├── .streamlit/
│   └── config.toml             # Konfigurasi Streamlit (nonaktifkan auto-nav bawaan)
│
├── seed_test_data.py           # Generate dataset testing Feb–Mei 2026 untuk 3 user
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Google account (untuk Google Cloud & Sheets)
- Telegram account (untuk membuat bot)
- Gemini API key (atau OpenAI API key)

---

### Langkah Awal (Wajib untuk Prod & Test)

#### 1. Clone & buat virtual environment

```bash
git clone <repo-url>
cd agen_exptrackerviz

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Google Cloud & Sheets setup

1. Buka [Google Cloud Console](https://console.cloud.google.com) → buat project baru
2. Aktifkan **Google Sheets API** dan **Google Drive API**
3. Pergi ke **IAM & Admin → Service Accounts → Create Service Account**
4. Download JSON key → simpan sebagai `service-account.json` di folder project
5. Buat **Google Spreadsheet** baru (biarkan kosong) — ini untuk **produksi**
6. Share spreadsheet tersebut ke email service account (format: `xxx@project.iam.gserviceaccount.com`) dengan akses **Editor**

> Sheet `Expenses`, `Budget`, dan `Users` dibuat otomatis oleh bot saat pertama kali dijalankan.

#### 4. Telegram Bot

1. Buka [@BotFather](https://t.me/BotFather) → `/newbot`
2. Ikuti instruksi → salin **Bot Token** yang diberikan

#### 5. AI API Key

- **Gemini (default):** [Google AI Studio](https://aistudio.google.com/) → Get API Key
- **OpenAI (opsional):** [platform.openai.com](https://platform.openai.com) → API Keys

---

### A. Production Setup

#### 6a. Konfigurasi `.env` untuk produksi

```bash
cp .env.example .env
```

Isi `.env` dengan nilai produksi:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# AI Provider
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash          # opsional, default: gemini-2.0-flash

# Google Sheets
GOOGLE_SHEETS_ID=your_production_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=service-account.json

# Mode — prod membaca GOOGLE_SHEETS_ID
MODE=prod

# Mata uang default fallback (per-user override disimpan di sheet Users)
DEFAULT_CURRENCY=GBP                   # sesuaikan: IDR | USD | EUR | GBP

# Telegram chat_id untuk akses halaman Admin di dashboard
# Cara cari: kirim /start ke bot → lihat log terminal, atau pakai @userinfobot
SUPERUSER_CHAT_IDS=your_telegram_chat_id
```

#### 7a. Jalankan bot

```bash
python app.py
```

#### 8a. Registrasi & set password dashboard

Buka Telegram → cari bot kamu → kirim:

```
/start
```

Bot akan mendaftarkan kamu otomatis ke sheet `Users`. Setelah itu, set password untuk login ke dashboard:

```
/setpassword passwordkamu
```

> Gunakan perintah ini **hanya di chat pribadi** dengan bot, bukan di grup.

#### 9a. Jalankan Streamlit Dashboard

Dashboard berjalan terpisah dari bot — bisa dijalankan bersamaan di terminal berbeda:

```bash
streamlit run dashboard/app.py
```

Buka browser ke `http://localhost:8501`.

**Login:**
- **Username:** Telegram username kamu (tanpa `@`)
- **Password:** password yang sudah di-set via `/setpassword`

> **Dev mode:** Jika belum set password (kolom `password_hash` kosong di sheet `Users`), dashboard menerima password apa saja dengan tampilkan peringatan kuning. Ideal untuk setup awal lokal.

---

### B. Test Environment Setup

Test environment menggunakan **spreadsheet terpisah** agar data produksi tidak terganggu.

#### 6b. Siapkan spreadsheet testing

1. Buat Google Spreadsheet baru (kosong) — ini khusus untuk testing
2. Share ke email service account yang sama dengan akses **Editor**
3. Salin Spreadsheet ID dari URL

#### 7b. Konfigurasi `.env` untuk mode test

Tambahkan atau update nilai berikut di `.env`:

```env
# Tambahkan spreadsheet testing
GOOGLE_SHEETS_ID_TEST=your_testing_spreadsheet_id

# Ubah MODE ke test
MODE=test
```

> Saat `MODE=test`, bot dan dashboard akan membaca/menulis ke `GOOGLE_SHEETS_ID_TEST`, bukan ke spreadsheet produksi.

#### 8b. Generate data sintetis

```bash
python seed_test_data.py
```

Script akan mengisi spreadsheet testing dengan data siap pakai:

| User | Username | Mata Uang | Chat ID |
|---|---|---|---|
| Alice | `alice_fin` | GBP | `1001` |
| Budi | `budi_finance` | IDR | `1002` |
| Carol | `carol_eu` | EUR | `1003` |

- **4 bulan data:** Februari – Mei 2026 (Mei parsial ±2 minggu)
- Budget per user per bulan (mix total dan per-kategori)
- ±80 transaksi per user dengan variasi kategori dan metode bayar

> Script aman dijalankan berulang — otomatis clear dan regenerate data setiap kali.

#### 9b. Jalankan dashboard dalam mode test

```bash
# Pastikan MODE=test di .env
streamlit run dashboard/app.py
```

Login dengan salah satu username test di atas (contoh: `alice_fin`) — password apa saja (dev mode aktif karena kolom `password_hash` tidak ada di data test).

#### 10b. Jalankan bot dalam mode test (opsional)

```bash
python app.py
```

Kirim `/tanya berapa total food saya bulan April?` — bot membaca data test sesuai `chat_id` Telegram kamu.

#### Kembali ke produksi

Ubah `MODE=prod` di `.env` → restart bot dan dashboard.

---

## Assumptions & Design Decisions

| Keputusan | Alasan |
|---|---|
| **Multi-user via `chat_id` column** | Satu spreadsheet untuk semua user; lebih efisien dari spreadsheet terpisah per user (API quota, manajemen) |
| **Dua spreadsheet: prod + test** | Data nyata dari bot tidak tercampur dengan data testing; bisa di-seed/reset kapan saja |
| **Verifikasi wajib sebelum simpan** | AI tidak 100% akurat; konfirmasi mencegah data salah masuk |
| **`/start` tidak tanya currency** | UX lebih simpel — langsung info currency default, arahkan ke `/setcurrency` jika ingin ganti |
| **Simplified AI Q&A (no vector DB)** | Fetch data Sheets sebagai JSON context langsung ke Gemini; cukup untuk dataset personal (max 6 bulan / 500 baris) |
| **Password via `/setpassword`** | Password di-set melalui bot Telegram (chat pribadi) → hash bcrypt disimpan ke sheet `Users`; dev mode aktif selama belum di-set |
| **Konversi currency hanya di laporan** | Tidak ada dependency live rate saat input — UX lebih cepat, data asli tetap utuh |
| **frankfurter.app untuk exchange rate** | Gratis, tanpa API key, mendukung IDR/USD/EUR/GBP |
| **Chart Telegram bersifat on-demand** | Mengurangi waktu proses; dibuat hanya saat user minta |
| **Bullet chart untuk budget vs aktual** | Budget sebagai bar lebar di belakang, aktual sebagai bar sempit di depan — selalu terlihat jelas meski budget << aktual atau tidak ada budget per kategori |
| **Deployment di v3** | Fokus v2 di fitur — pastikan semua berjalan lokal sebelum deploy ke cloud |
| **v1 data tidak terlihat di v2** | Baris lama tanpa `chat_id` difilter keluar; v2 mulai dari fresh data — tidak ada migrasi diperlukan |

---

## Future Development

FinTrack dirancang sebagai fondasi dari ekosistem manajemen keuangan personal yang lebih besar. Ke depannya, akan ada modul-modul terpisah yang terintegrasi di bawah satu platform **FinTrack Suite**.

---

### v3 — Deployment & Reliability

- **Bot deployment** — Railway atau Render: auto-deploy dari GitHub, berjalan 24/7
- **Dashboard deployment** — Streamlit Community Cloud: gratis, zero-config, domain publik
- **Budget alert otomatis** — notifikasi Telegram saat pengeluaran kategori mendekati atau melewati batas budget
- **Cached exchange rate** — simpan rate harian ke Sheets untuk mengurangi API calls

---

### FinTrack Core — Near-term Enhancements

- **Recurring expense** — catat pengeluaran rutin yang otomatis ditambahkan setiap bulan
- **Laporan komparatif** — bandingkan bulan ini vs bulan lalu atau rata-rata 3 bulan terakhir
- **Budget template** — simpan template budget dan terapkan ulang setiap bulan
- **Export ke Excel (.xlsx)** — format dengan warna dan formula via `openpyxl`
- **Currency tambahan** — SGD, AUD, JPY
- **Integrasi bank statement** — auto-parse PDF mutasi BCA, Mandiri, Barclays, Monzo

---

### Modul: FinTrack Income — Pencatatan Pemasukan

Modul khusus untuk mencatat dan menganalisis sumber pemasukan, terpisah dari pengeluaran.

- Pencatatan pemasukan: gaji, freelance, passive income, transfer keluarga
- Laporan cash flow: pemasukan vs pengeluaran per bulan
- Analisis net income dan savings rate
- Notifikasi saat savings rate turun di bawah target
- Dashboard pemasukan yang terintegrasi dengan dashboard pengeluaran

---

### Modul: FinTrack Invest — Rekomendasi Investasi

Modul untuk memantau portofolio dan mendapatkan rekomendasi investasi berbasis data keuangan personal.

- **Saham IDX** — monitoring harga, sinyal beli/jual berbasis analisis sederhana, rekomendasi saham sesuai profil risiko
- **Emas** — harga emas (Antam/LM) real-time, histori harga, rekomendasi waktu akumulasi
- **Reksa Dana** — perbandingan produk reksa dana, rekomendasi berdasarkan kapasitas menabung
- **Kalkulasi kapasitas investasi** — AI analisis pengeluaran untuk rekomendasikan berapa yang bisa diinvestasikan per bulan
- **Proyeksi pertumbuhan** — simulasi nilai investasi berdasarkan horizon waktu dan return target
- Dashboard portofolio terintegrasi dengan data pengeluaran (net worth view)

---

### Modul: FinTrack Protect — Manajemen Asuransi

Modul untuk inventarisasi, monitoring, dan rekomendasi kebutuhan asuransi.

- Catat produk asuransi yang dimiliki: jiwa, kesehatan, kendaraan, properti
- Reminder jatuh tempo premi via Telegram
- Kalkulasi kebutuhan uang pertanggungan berdasarkan profil keuangan
- Rekomendasi jenis dan besaran asuransi yang sesuai dengan kondisi keuangan
- Perbandingan produk asuransi dari berbagai penyedia
- Integrasi dengan data pengeluaran untuk optimasi premi vs budget

---

### Mid-term — AI & Intelligence

- **Spending prediction** — prediksi sisa budget akhir bulan berdasarkan tren historis
- **Anomaly detection** — notifikasi otomatis saat ada transaksi yang tidak biasa
- **Smart categorization** — model belajar dari koreksi user, akurasi kategori meningkat dari waktu ke waktu
- **Rekomendasi lintas modul** — AI melihat gambaran utuh (pengeluaran, pemasukan, investasi) untuk rekomendasi keuangan yang holistik

---

### Long-term — Platform

- **FinTrack Suite web app** — web app terpadu yang mengintegrasikan semua modul di atas
- **Shared household budget** — satu budget bersama untuk pasangan atau flatmates
- **Multi-platform** — support WhatsApp atau LINE selain Telegram
- **Open API** — endpoint untuk integrasi dengan tools keuangan lain

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
