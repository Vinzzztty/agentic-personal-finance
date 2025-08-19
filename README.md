# Agentic Personal Finance 💸🤖

## Roadmap (Phases) 🗺️
| Phase   | Status | Goal                                                     | Highlights |
|---------|--------|----------------------------------------------------------|------------|
| Phase 1 | ✅ Done | Load Google Sheet, Preprocessing, Charts, Chat (LLM)   | Env-based sheet config, robust parsing (tanggal/Rp), multiple charts, chat with temporary memory |
| Phase 2 | ⏳ Planned | Scraping Financial Knowledge                          | Integrate curated sources; enrich insights |
| Phase 3 | 🔜 Planned | To be defined                                          | TBA |
| Phase 4 | 🔜 Planned | To be defined                                          | TBA |

## Apa yang aplikasi ini lakukan ✨
- 🔗 Memuat Google Sheet melalui link berbagi (tanpa DB) menggunakan variabel lingkungan
- 🧹 Preprocessing data dengan Pandas (normalisasi tanggal dan nilai Rupiah)
- 📊 Visualisasi:
  - 🥧 Pie berdasarkan `Kategori`
  - 💳 Pie berdasarkan `Pembayaran`
  - 📈 Time series harian (line)
  - 📅 Time series bulanan (bar)
  - 🏆 Bar Top Kategori
- 💬🤖 Chat dengan LLM lokal (Ollama) tentang data yang dimuat, menggunakan memori sementara (in-memory)

## Quickstart 🚀

1. Install dependencies (uv atau pip):
   - Dengan `uv` (disarankan):
     ```bash
     uv sync
     ```
   - Atau dengan `pip`:
     ```bash
     pip install -e .
     ```

2. Buat file `.env` di root proyek untuk mengatur sumber data Google Sheet:
   ```env
   SPREADSHEET_URL="https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit?usp=sharing"
   SHEET_NAME="Transaksi"
   # Opsional: model LLM
   # OLLAMA_MODEL="gemma3:4b"
   ```

3. (Opsional) Install dan jalankan Ollama, lalu tarik model:
   ```bash
   brew install ollama
   ollama serve &
   ollama pull gemma3:4b
   ```

4. Jalankan aplikasi:
   ```bash
   streamlit run app.py
   ```

## Template Google Sheet 📄
- 🔗 Gunakan template berikut agar struktur kolom kompatibel:
  - [Template Google Sheet](https://lynk.id/deeplate)
- 📑 Buat salinan (File → Make a copy), lalu set di `.env`:
  - 🔗 `SPREADSHEET_URL` ke link salinan Anda
  - 🏷️ `SHEET_NAME` ke nama tab (contoh: `Transaksi`)

## Catatan 📝
- 🌐 Google Sheet harus bisa diakses publik (contoh: "Anyone with the link").
- 🧭 `SHEET_NAME` harus sama persis dengan nama tab di spreadsheet Anda.
- 🗓️💰 Preprocessing akan mencoba parse tanggal (US-first lalu day-first) dan mengubah "Rp 32,000" menjadi angka 32000.
- 🧠 Chat mengirim schema + preview kecil ke LLM; tidak ada data yang disimpan ke disk.
- ⚙️ Default model adalah `gemma3:4b`. Anda bisa override via env var atau shell:
  ```bash
  export OLLAMA_MODEL=llama3
  ```

## Lisensi 📄
Proyek ini menggunakan lisensi MIT. Lihat file `LICENSE` untuk detail selengkapnya.

