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
- 🧹 **NEW**: Automatic cleaning of reasoning tags from models like DeepSeek R1:8B
- 📋 **IMPROVED**: Enhanced data context with financial summaries, category analysis, and better formatting for LLM understanding
- ⚡ **NEW**: Real-time streaming responses with loading indicators for better user experience
- 🚀 **NEW**: Smart optimization features for faster responses while maintaining accuracy

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

## Konfigurasi Lanjutan ⚙️

### Tag Cleaning untuk DeepSeek R1:8B
Jika Anda menggunakan model DeepSeek R1:8B yang memiliki fitur reasoning internal, aplikasi akan otomatis membersihkan tag `<think>...</think>` dari output. Tambahkan konfigurasi berikut ke file `.env`:

```env
# Tag Cleaning Configuration
CLEAN_REASONING_TAGS=true          # Enable/disable tag cleaning
AGGRESSIVE_CLEANING=true           # Thorough cleaning mode
LOG_LEVEL=INFO                     # Logging level
```

**Mode Pembersihan:**
- **Basic Cleaning**: Hanya menghapus tag reasoning yang lengkap
- **Aggressive Cleaning**: Juga menghapus tag yang tidak lengkap dan membersihkan formatting

**Tag yang Dibersihkan:**
- `<think>...</think>`
- `<reasoning>...</reasoning>`
- `<analysis>...</analysis>`
- `<thought>...</thought>`
- `<step>...</step>`
- `<process>...</process>`
- `<plan>...</plan>`
- `<approach>...</approach>`

### Enhanced Data Context untuk LLM
Aplikasi sekarang menyediakan context yang lebih kaya untuk LLM, termasuk:

**📊 Dataset Overview:**
- Total records dan kolom yang tersedia
- Financial summary (total spending, average, min, max)
- Category distribution (jumlah transaksi per kategori)
- Date range (periode data yang tersedia)

**📋 Complete Dataset:**
- Data lengkap dengan formatting yang optimal
- Tanggal dalam format YYYY-MM-DD yang mudah dibaca
- Nilai total dengan format currency (Rp X,XXX)
- Deskripsi yang tidak terpotong

**🧠 System Prompt:**
- Instruksi yang jelas untuk analisis keuangan
- Panduan untuk memberikan insights yang actionable
- Penekanan pada penggunaan data aktual

### ⚡ Real-time Streaming Responses
Untuk model besar seperti DeepSeek R1:8B, aplikasi mendukung streaming responses:

**🚀 Fitur Streaming:**
- Response real-time dengan loading indicator
- Updates bertahap untuk user experience yang lebih baik
- Fallback otomatis ke non-streaming jika streaming gagal
- Konfigurasi chunk size untuk kontrol update frequency

**⚙️ Konfigurasi Streaming:**
```env
# Enable/disable streaming
ENABLE_STREAMING=true

# Chunk size untuk updates (karakter)
STREAMING_CHUNK_SIZE=50
```

**💡 Keuntungan Streaming:**
- User tidak perlu menunggu response lengkap
- Feedback visual bahwa AI sedang bekerja
- Lebih responsif untuk model besar
- Mengurangi perceived latency

**🔧 Fallback Behavior:**
- Jika streaming gagal, otomatis menggunakan non-streaming
- Tidak ada interupsi user experience
- Logging untuk debugging streaming issues

### 🚀 Smart Optimization Features
Untuk meningkatkan kecepatan response sambil mempertahankan akurasi:

**🧠 Context Optimization:**
- Analisis pertanyaan untuk menentukan data yang relevan
- Pengurangan ukuran context berdasarkan kebutuhan
- Hanya menampilkan data yang diperlukan untuk pertanyaan spesifik
- Pengurangan context hingga 50-70% tanpa kehilangan akurasi

**💾 Smart Caching:**
- Cache response untuk pertanyaan yang berulang
- Hash-based caching dengan context awareness
- LRU (Least Recently Used) cache management
- Cache hit rate monitoring dan statistics

**📏 Response Length Control:**
- Batasan panjang response untuk kecepatan optimal
- Truncation otomatis dengan indikator "..."
- Konfigurasi panjang response per model
- Balance antara kecepatan dan detail

**⚙️ System Prompt Optimization:**
- Prompt yang disesuaikan berdasarkan jenis pertanyaan
- Financial advisor mode untuk pertanyaan hemat/boros
- Data analyst mode untuk trend analysis
- Calculator mode untuk perhitungan

**📊 Performance Monitoring:**
- Cache hit/miss statistics
- Context size reduction metrics
- Response time tracking
- Memory usage optimization

**⚙️ Konfigurasi Optimasi:**
```env
# Enable/disable optimization
ENABLE_OPTIMIZATION=true

# Context and response limits
MAX_CONTEXT_LENGTH=2000      # Max context characters
MAX_RESPONSE_LENGTH=1000     # Max response characters

# Caching configuration
ENABLE_CACHING=true          # Enable response caching
CACHE_SIZE=100               # Number of cached responses

# Advanced features
ENABLE_PARALLEL=false        # Parallel processing (experimental)
```

**💡 Keuntungan Optimasi:**
- **Kecepatan**: Response 2-5x lebih cepat untuk pertanyaan berulang
- **Efisiensi**: Penggunaan memory yang lebih optimal
- **Akurasi**: Tetap mempertahankan kualitas response
- **Scalability**: Performa yang konsisten dengan dataset besar
- **User Experience**: Response time yang lebih responsif

### Testing Tag Cleaning
Untuk memverifikasi fungsi pembersihan tag bekerja dengan benar:

```python
from app.llm import test_tag_cleaning
test_tag_cleaning()
```

### Testing Context Creation
Untuk memverifikasi context yang dikirim ke LLM sudah benar:

```python
python test_context.py
```

## Catatan 📝
- 🌐 Google Sheet harus bisa diakses publik (contoh: "Anyone with the link").
- 🧭 `SHEET_NAME` harus sama persis dengan nama tab di spreadsheet Anda.
- 🗓️💰 Preprocessing akan mencoba parse tanggal (US-first lalu day-first) dan mengubah "Rp 32,000" menjadi angka 32000.
- 🧠 Chat mengirim schema + preview kecil ke LLM; tidak ada data yang disimpan ke disk.
- ⚙️ Default model adalah `gemma3:4b`. Anda bisa override via env var atau shell:
  ```bash
  export OLLAMA_MODEL=llama3
  ```
- 🧹 Tag cleaning otomatis aktif untuk model yang menghasilkan reasoning tags. Gunakan `CLEAN_REASONING_TAGS=false` untuk menonaktifkan.

## Lisensi 📄
Proyek ini menggunakan lisensi MIT. Lihat file `LICENSE` untuk detail selengkapnya.

