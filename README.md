# PANASEA — versi browser

Project Pygame ini disiapkan untuk dijalankan di browser dengan Pygbag.

## Tes di laptop (Windows)
1. Buka CMD di folder yang berisi folder `PANASEA-web`.
2. Jalankan:
   ```bash
   python -m pip install --upgrade pygbag
   python -m pygbag PANASEA-web
   ```
3. Buka `http://localhost:8000` di browser laptop.

## Hosting gratis dengan GitHub Pages
1. Buat repository GitHub baru.
2. Upload seluruh isi folder `PANASEA-web` ke root repository, termasuk folder `.github`.
3. Buka **Settings → Pages** dan pilih **GitHub Actions** sebagai sumber deployment.
4. Buka tab **Actions**. Workflow `Build and publish PANASEA` akan membangun dan menerbitkan project setelah push ke branch `main`.
5. Setelah workflow sukses, buka alamat Pages yang ditampilkan GitHub, biasanya:
   `https://USERNAME.github.io/NAMA-REPOSITORY/`

## Catatan
- Tes lokal dulu sebelum dipublikasikan.
- Pygbag menjalankan Pygame melalui WebAssembly; pemuatan pertama bisa lebih lama.
- Di HP, gunakan browser modern. Performa bergantung pada perangkat.
