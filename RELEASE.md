# Release Process

## Versioning
- Gunakan SemVer: `MAJOR.MINOR.PATCH` (misal: `0.1.1`).
- Phase 1: `v0.1.1`
- Phase 2: `v0.2.0`
- Phase 3: `v0.3.0`

## Release Checklist

### Pre-release
- [ ] Semua fitur sudah selesai dan tested
- [ ] Dokumentasi sudah lengkap
- [ ] Versi di `pyproject.toml` sudah sesuai (contoh: `0.1.1`)
- [ ] Changelog sudah diupdate
- [ ] Branch sudah di-merge ke main

### Release Steps
1. Update versi di `pyproject.toml`
2. Set versi rilis di `pyproject.toml` (contoh Phase 1 → `0.1.1`)
3. Commit perubahan versi:
   ```bash
   git add pyproject.toml
   git commit -m "chore(release): set version 0.1.1"
   ```
4. Buat git tag:
   ```bash
   git tag -a v0.1.1 -m "Phase 1 release"
   git push origin v0.1.1
   ```
5. Buat GitHub Release dari tag `v0.1.1` dengan catatan rilis (lihat template di bawah)

### Post-release
- [ ] Update dokumentasi jika diperlukan
- [ ] Update changelog untuk versi berikutnya
- [ ] Notifikasi tim tentang rilis

## Release Template

### Phase 1 — v0.1.1

Ringkasan:
- Memuat data Google Sheet via `.env`
- Preprocessing (tanggal, Rupiah)
- Visualisasi (Pie Kategori/Pembayaran, harian, bulanan, Top Kategori)
- Chat dengan LLM (Ollama) dengan memori sementara

Perubahan Utama:
- Data loading: robust parsing + .env
- Charts: pie, line harian, bar bulanan, top kategori
- Chatbox: in-memory history (Ollama)
- Dokumentasi: README, CONTRIBUTING, LICENSE

Catatan:
- Google Sheet harus publik
- Model default Ollama: `gemma3:4b`

## Tips
- Gunakan commit kecil dan jelas (Conventional Commits)
- Hindari cabang rilis jika tidak perlu; cukup tag dari `main`
