# Panduan Penggunaan API SIGNET (Postman)

Berikut adalah panduan lengkap untuk mengetes endpoint API menggunakan Postman.

**Base URL**: `http://localhost:8000`

---

## 1. Register Content (Daftarkan Konten)
Mendaftarkan konten baru ke blockchain Lisk dan menyimpannya ke database indexer.

- **Method**: `POST`
- **Endpoint**: `/api/register-content`
- **Body Type**: `form-data`

**Parameter Body:**
| Key | Type | Value | Deskripsi |
| :--- | :--- | :--- | :--- |
| `file` | File | (Pilih file gambar/video) | File asli yang akan didaftarkan |
| `title` | Text | "Judul Karya" | Judul konten |
| `description` | Text | "Deskripsi konten..." | Penjelasan singkat |

**Contoh Response Sukses (200 OK):**
```json
{
    "status": "SUCCESS",
    "pHash": "a1b2c3d4e5f67890",
    "txHash": "0x123456789abcdef...",
    "message": "Content registered successfully. Indexer will pick it up shortly."
}
```

---

## 2. Verify Content (Verifikasi Konten)
Mengecek apakah sebuah file sudah terdaftar dan asli.

- **Method**: `POST`
- **Endpoint**: `/api/verify`
- **Body Type**: `form-data`

**Parameter Body:**
| Key | Type | Value | Deskripsi |
| :--- | :--- | :--- | :--- |
| `file` | File | (Pilih file) | File yang ingin dicek |
| `link` | Text | (Kosongkan jika upload file) | Opsional: Link video (belum aktif penuh) |

**Contoh Response: VERIFIED (Asli)**
```json
{
    "status": "VERIFIED",
    "pHash_input": "a1b2c3d4e5f67890",
    "pHash_match": "a1b2c3d4e5f67890",
    "hamming_distance": 0,
    "publisher": "0xPublisherAddress...",
    "title": "Judul Karya",
    "txHash": "0x123456789abcdef...",
    "explorer_link": "https://sepolia-blockscout.lisk.com/tx/0x...",
    "message": "Content is authentic."
}
```

**Contoh Response: UNVERIFIED (Palsu/Belum Terdaftar)**
```json
{
    "status": "UNVERIFIED",
    "pHash_input": "f9e8d7c6b5a43210",
    "message": "No matching content found."
}
```

---

## 3. Get All Contents (Lihat Daftar)
Melihat daftar konten yang sudah terindex di database lokal.

- **Method**: `GET`
- **Endpoint**: `/api/contents`

**Contoh Response:**
```json
[
    {
        "id": 1,
        "pHash": "a1b2c3d4e5f67890",
        "publisher": "0xPublisherAddress...",
        "title": "Judul Karya",
        "description": "Deskripsi konten...",
        "timestamp": 1700000000,
        "txHash": "0x123456789abcdef...",
        "blockNumber": 1005,
        "created_at": "2024-01-01T12:00:00"
    }
]
```
