# USB-Writer

**Usb Writer** adalah tool sederhana berbasis Python untuk menulis file ISO ke USB drive sekaligus mengatur partisi (GPT/MBR) dan memformatnya. Tool ini ditujukan untuk pengguna tingkat lanjut yang ingin memiliki kontrol penuh terhadap proses pembuatan bootable drive tanpa menggunakan aplikasi GUI seperti Rufus atau BalenaEtcher.

## ⚙️ Fitur
- Menampilkan daftar disk dan partisinya.
- Memilih device target untuk penulisan ISO.
- Pilihan tipe partisi: **GPT** atau **MBR**.
- Format partisi ke **FAT32**, **NTFS**, atau **EXT4**.
- Menulis ISO ke drive menggunakan `dd` (Linux/macOS).
- Kompatibel dengan Windows (terbatas, via `diskpart`).

## ⚠️ Peringatan Penting
> Tool ini **akan menghapus seluruh data** di drive target. Pastikan kamu memilih drive yang benar sebelum melanjutkan!

## 🧰 Kebutuhan Sistem
### Linux / macOS
- Python 3.8+
- `parted`, `dd`, `mkfs.*`, `sgdisk` (opsional)

### Windows
- Python 3.8+
- Jalankan sebagai Administrator
- `diskpart` sudah tersedia secara default

## 📦 Instalasi
```bash
# Clone repository
$ git clone https://github.com/username/usb-writer.git
$ cd usb-writer

# Jalankan langsung
$ sudo python3 usb_writer.py
```

## 💡 Contoh Penggunaan
```bash
# Lihat daftar drive
$ sudo python3 usb_writer.py --list

# Pilih device dan tulis ISO
$ sudo python3 usb_writer.py --device /dev/sdb --iso ubuntu.iso --partition gpt --format fat32
```

## 🚀 Rencana Fitur Selanjutnya
- Antarmuka GUI menggunakan PySimpleGUI.
- Dukungan auto-detect ISO boot sector.
- Log dan verifikasi checksum ISO.

## 🧑‍💻 Kontribusi
Kontribusi sangat diterima! Silakan buat *pull request* atau *issue* jika menemukan bug atau ingin menambahkan fitur.
