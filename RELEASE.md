# Panduan Rilis (Release Guide)

Dokumen ini menjelaskan alur rilis versi proyek menggunakan penandaan (git tag) dan catatan rilis. Disarankan alur sederhana berbasis `main` + tag.

## Penamaan Versi
- Gunakan SemVer: `MAJOR.MINOR.PATCH` (misal: `0.1.0`).
- Contoh:
  - Phase 1: `v0.1.0`
  - Patch/hotfix: `v0.1.1`, `v0.1.2`, dst.

## Checklist Pra-Rilis
- [ ] Aplikasi berjalan: `streamlit run app.py`
- [ ] Data dapat dimuat dari Google Sheet yang publik
- [ ] Visualisasi tampil tanpa error (pie, time series, bar)
- [ ] Chat (opsional) berfungsi jika Ollama aktif
- [ ] `README.md` dan `CONTRIBUTING.md` diperbarui
- [ ] Versi di `pyproject.toml` sudah sesuai (contoh: `0.1.0`)

## Langkah Rilis
1. Pastikan `main` terbaru
   ```bash
   git checkout main
   git pull
   ```
2. Set versi rilis di `pyproject.toml` (contoh Phase 1 → `0.1.0`)
3. Commit perubahan versi (jika ada)
   ```bash
   git add pyproject.toml
   git commit -m "chore(release): set version 0.1.0"
   ```
4. Buat tag rilis dan dorong ke remote
   ```bash
   git tag -a v0.1.0 -m "Phase 1 release"
   git push origin v0.1.0
   ```
5. Buat GitHub Release dari tag `v0.1.0` dengan catatan rilis (lihat template di bawah)

## Setelah Rilis (Persiapan Pengembangan Berikutnya)
- Naikkan versi pengembangan di `pyproject.toml` (mis. `0.2.0-dev`) di `main`:
  ```bash
  git checkout main
  # ubah versi → 0.2.0-dev
  git add pyproject.toml
  git commit -m "chore: bump version to 0.2.0-dev"
  git push
  ```

## Hotfix (Opsional)
Jika perlu patch untuk versi rilis:
- Buat branch rilis (hanya jika ekspektasi ada beberapa patch)
  ```bash
  git checkout -b release/v0.1.x
  git push -u origin release/v0.1.x
  ```
- Alur hotfix:
  - `hotfix/<deskripsi>` → PR ke `release/v0.1.x`
  - Tag patch baru (mis. `v0.1.1`) dari `release/v0.1.x`
  - Merge/cherry-pick perubahan ke `main`

## Template Catatan Rilis
Judul: Phase 1 — v0.1.0

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
