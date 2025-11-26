# Panduan Penggunaan API SIGNET (Postman)

Berikut adalah panduan lengkap untuk berinteraksi dengan SIGNET Backend API.

**Base URL**: `http://localhost:8000`

---

## Daftar Endpoint

### 1. Health Check
Mengecek status server backend.

- **Method**: `GET`
- **Endpoint**: `/`

**Response Sukses (200 OK):**
```json
{
    "message": "SIGNET Backend is running"
}
```

---

### 2. Register Content (Daftarkan Konten)
Mendaftarkan konten baru ke blockchain Lisk dan menyimpannya ke database indexer.

- **Method**: `POST`
- **Endpoint**: `/api/register-content`
- **Body Type**: `form-data`

**Parameter Body:**
| Key | Type | Required | Deskripsi |
| :--- | :--- | :--- | :--- |
| `file` | File | Yes | File gambar atau video yang akan didaftarkan. |
| `title` | Text | Yes | Judul karya. |
| `description` | Text | Yes | Deskripsi singkat mengenai konten. |

**Response Sukses (200 OK):**
```json
{
    "status": "SUCCESS",
    "pHash": "a1b2c3d4e5f67890",
    "txHash": "0x123456789abcdef...",
    "message": "Content registered successfully. Indexer will pick it up shortly."
}
```

**Error Response (500 Internal Server Error):**
Jika terjadi kesalahan saat upload atau interaksi blockchain.
```json
{
    "detail": "Error message description..."
}
```

---

### 3. Verify Content (Verifikasi Konten)
Mengecek keaslian konten dengan membandingkan perceptual hash (pHash) dengan database yang ada.

- **Method**: `POST`
- **Endpoint**: `/api/verify`
- **Body Type**: `form-data`

**Parameter Body:**
| Key | Type | Required | Deskripsi |
| :--- | :--- | :--- | :--- |
| `file` | File | Optional* | File yang ingin dicek keasliannya. |
| `link` | Text | Optional* | Link video/gambar (YouTube, TikTok, Instagram, Direct URL). |

*\*Salah satu dari `file` atau `link` harus ada.*

**Response: VERIFIED (Asli)**
Konten ditemukan dan memiliki kemiripan di bawah ambang batas (Hamming Distance <= Threshold).
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

**Response: UNVERIFIED (Palsu/Belum Terdaftar)**
Konten tidak ditemukan atau perbedaannya terlalu jauh.
```json
{
    "status": "UNVERIFIED",
    "pHash_input": "f9e8d7c6b5a43210",
    "message": "No matching content found."
}
```
*Atau jika ditemukan tapi jaraknya terlalu jauh:*
```json
{
    "status": "UNVERIFIED",
    "pHash_input": "...",
    "pHash_match": "...",
    "hamming_distance": 35,
    ...
    "message": "Content is different."
}
```

---

### 4. Get All Contents (Lihat Daftar)
Melihat daftar konten yang sudah terindex di database lokal.

- **Method**: `GET`
- **Endpoint**: `/api/contents`

**Response Sukses (200 OK):**
Mengembalikan array objek konten. Perhatikan penulisan key (huruf kecil) sesuai dengan database model.

```json
[
    {
        "id": 1,
        "phash": "a1b2c3d4e5f67890",
        "publisher": "0xPublisherAddress...",
        "title": "Judul Karya",
        "description": "Deskripsi konten...",
        "timestamp": 1700000000,
        "txhash": "0x123456789abcdef...",
        "blocknumber": 1005,
        "created_at": "2024-01-01T12:00:00"
    }
]
```

---

## Catatan Tambahan

### Telegram Bot
Selain API ini, tersedia juga **Telegram Bot** yang memiliki fitur lebih lengkap.
Bot menggunakan endpoint `/api/verify` di balik layar untuk pemrosesan file.

### Konfigurasi Environment
Beberapa perilaku API dipengaruhi oleh file `.env`:
- `HAMMING_THRESHOLD`: Ambang batas toleransi perbedaan gambar (Default: 25). Semakin kecil nilainya, semakin ketat verifikasinya.
