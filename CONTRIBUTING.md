# Panduan Kontribusi

Terima kasih atas minat Anda untuk meningkatkan Agentic Personal Finance! Dokumen ini menjelaskan cara menyiapkan proyek, mengusulkan perubahan, dan membuka pull request.

## Setup
- Kebutuhan: Python 3.10+, macOS/Linux/Windows
- Instal dependensi (pilih salah satu):
  - uv (disarankan):
    ```bash
    uv sync
    ```
  - pip:
    ```bash
    pip install -e .
    ```
- Konfigurasi environment:
  - Buat file `.env` di root proyek:
    ```env
    SPREADSHEET_URL="https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit?usp=sharing"
    SHEET_NAME="Transaksi"
    # Opsional
    # OLLAMA_MODEL="gemma3:4b"
    ```
- Backend LLM (opsional, untuk chat):
  ```bash
  brew install ollama
  ollama serve &
  ollama pull gemma3:4b
  ```
- Jalankan aplikasi:
  ```bash
  streamlit run app.py
  ```

## Branching
- Buat branch fitur dari `main`:
  - `feat/<topik-singkat>` untuk fitur baru
  - `fix/<topik-singkat>` untuk perbaikan bug
  - `docs/<topik-singkat>` untuk dokumentasi
  - `chore/<topik-singkat>` untuk pekerjaan rutin

## Pesan commit (sederhana + konvensional)
Gunakan commit kecil dan jelas. Sarankan format Conventional Commits:
- `feat: add charts for kategori and pembayaran`
- `fix: robust date parsing in preprocessing`
- `docs: update README (env, roadmap)`
- `chore: add dotenv dependency`

## Gaya kode
- Utamakan keterbacaan, penamaan variabel yang jelas, dan type hints
- Tangani edge-case di awal; hindari nesting terlalu dalam
- Tambahkan komentar singkat untuk logika yang tidak jelas (jelaskan “mengapa”)
- Jaga fungsi tetap fokus dan kecil

## Mengajukan perubahan
1. Pastikan aplikasi berjalan lokal: `streamlit run app.py`
2. Tambahkan screenshot untuk perubahan UI (charts/chat) di PR
3. Buka Pull Request berisi:
   - Ringkasan perubahan dan motivasi
   - Before/After (jika relevan)
   - Catatan pengujian (cara Anda memverifikasi)

## Isu & dukungan
- Saat membuat issue, sertakan:
  - Versi OS + Python
  - Langkah reproduksi
  - Log relevan (error/traceback) dan screenshot

## Privasi data
- JANGAN commit rahasia atau spreadsheet privat
- Gunakan template yang disediakan dan tautan share yang terbatas

---
Terima kasih telah berkontribusi! 🙌
