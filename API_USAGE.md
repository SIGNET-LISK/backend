# Panduan Penggunaan API SIGNET
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
    "message": "SIGNET Backend is running with gasless transaction support"
}
```

---

## 📝 Content Registration

### 2. Register Content - Endpoint Utama
**1 endpoint dengan 2 cara penggunaan berbeda:**

> **Catatan Penting:** 
> - **Kedua mode GRATIS untuk user** (user tidak bayar gas)
> - **Perbedaan utama:** Siapa yang tercatat sebagai publisher di blockchain

#### Mode 1: Backend-Signed (Cara Lama)
Upload file, backend sign transaksi. User tidak bayar gas tapi **publisher tercatat sebagai backend address**.

- **Method**: `POST`
- **Endpoint**: `/api/register-content`
- **Body Type**: `form-data`
- **Publisher di blockchain:** Backend address ⚠️

**Parameter Body:**
| Key | Type | Required | Deskripsi |
| :--- | :--- | :--- | :--- |
| `file` | File | Yes | File gambar atau video yang akan didaftarkan. |
| `title` | Text | Yes | Judul karya. |
| `description` | Text | Yes | Deskripsi singkat mengenai konten. |
| `publisher_address` | Text | No | Address publisher (untuk validasi). |

**Response Sukses (200 OK):**
```json
{
    "status": "SUCCESS",
    "pHash": "a1b2c3d4e5f67890",
    "txHash": "0x123456789abcdef...",
    "message": "Content registered successfully. Indexer will pick it up shortly."
}
```

---

#### Mode 2: User-Signed Meta-Transaction (Cara Baru) - NEW! ✨
User sign dengan wallet (EIP-712), backend relay transaksi. User tidak bayar gas dan **publisher tercatat sebagai user address** ✅

- **Method**: `POST`
- **Endpoint**: `/api/register-content` (endpoint yang sama!)
- **Body Type**: `application/json`
- **Publisher di blockchain:** User address ✅ (Identitas terjaga!)

**Parameter Body:**
```json
{
    "publisher_address": "0x123...",
    "p_hash": "QmXXX...",
    "title": "Judul Konten",
    "description": "Deskripsi konten",
    "signature": "0xabc..."
}
```

**Response Sukses (200 OK):**
```json
{
    "success": true,
    "status": "SUCCESS",
    "pHash": "QmXXX...",
    "tx_hash": "0x...",
    "txHash": "0x...",
    "block_number": 12345,
    "message": "Content registered successfully via gasless transaction."
}
```

**Error Response (401 Unauthorized):**
```json
{
    "detail": "Invalid signature. Signature verification failed."
}
```

**Error Response (403 Forbidden):**
```json
{
    "detail": "Address 0x... is not authorized as publisher."
}
```

---

## 🔐 Signature & Gasless Operations

### 4. Verify Signature (NEW! ✨)
Verifikasi signature EIP-712 sebelum submit transaksi (pre-flight check).

- **Method**: `POST`
- **Endpoint**: `/api/verify-signature`
- **Body Type**: `application/json`

**Parameter Body:**
```json
{
    "user_address": "0x123...",
    "p_hash": "QmXXX...",
    "title": "Judul",
    "description": "Deskripsi",
    "signature": "0xabc..."
}
```

**Response Sukses:**
```json
{
    "valid": true,
    "nonce": 0,
    "message": "Signature is valid and ready to be submitted"
}
```

**Response Error:**
```json
{
    "valid": false,
    "nonce": 0,
    "error": "Signature verification failed...",
    "message": "Invalid signature"
}
```

---

### 5. Get Nonce (NEW! ✨)
Ambil nonce untuk user address dari MinimalForwarder contract.

- **Method**: `GET`
- **Endpoint**: `/api/nonce/{address}`

**Contoh:**
```
GET /api/nonce/0x123456789...
```

**Response:**
```json
{
    "address": "0x123456789...",
    "nonce": 5
}
```

---

## 👤 Publisher Management

### 6. Add Publisher (Gasless - NEW! ✨)
Owner menambahkan publisher baru via gasless transaction.

- **Method**: `POST`
- **Endpoint**: `/api/add-publisher`
- **Body Type**: `application/json`

**Parameter Body:**
```json
{
    "owner_address": "0xOwner...",
    "publisher_address": "0xNewPublisher...",
    "signature": "0x..."
}
```

**Response Sukses:**
```json
{
    "success": true,
    "tx_hash": "0x...",
    "block_number": 12345,
    "message": "Publisher 0x... added successfully"
}
```

**Error Response (403 Forbidden):**
```json
{
    "detail": "Only contract owner can add publishers. Contract owner is 0x..."
}
```

---

### 7. Get Contract Owner (NEW! ✨)
Mendapatkan address owner dari smart contract.

- **Method**: `GET`
- **Endpoint**: `/api/owner`

**Response:**
```json
{
    "owner": "0xOwnerAddress..."
}
```

---

### 8. Check Publisher Status (NEW! ✨)
Cek apakah sebuah address adalah authorized publisher.

- **Method**: `GET`
- **Endpoint**: `/api/publisher/{address}`

**Contoh:**
```
GET /api/publisher/0x123456789...
```

**Response:**
```json
{
    "address": "0x123456789...",
    "is_authorized": true
}
```

---

## 🔍 Content Verification

### 9. Verify Content (Verifikasi Konten)
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
```json
{
    "status": "VERIFIED",
    "pHash_input": "a1b2c3d4e5f67890",
    "pHash_match": "a1b2c3d4e5f67890",
    "hamming_distance": 0,
    "publisher": "0xPublisherAddress...",
    "title": "Judul Karya",
    "description": "Deskripsi konten",
    "timestamp": 1700000000,
    "txHash": "0x123456789abcdef...",
    "blocknumber": 1005,
    "explorer_link": "https://sepolia-blockscout.lisk.com/tx/0x...",
    "message": "Content is authentic."
}
```

**Response: UNVERIFIED (Palsu/Belum Terdaftar)**
```json
{
    "status": "UNVERIFIED",
    "pHash_input": "f9e8d7c6b5a43210",
    "message": "No matching content found."
}
```

---

## 📚 Content Queries

### 10. Get All Contents (Enhanced - NEW! ✨)
Melihat daftar konten dengan filtering dan pagination.

- **Method**: `GET`
- **Endpoint**: `/api/contents`

**Query Parameters:**
| Parameter | Type | Required | Default | Deskripsi |
| :--- | :--- | :--- | :--- | :--- |
| `publisher` | String | No | - | Filter by publisher address |
| `limit` | Integer | No | 50 | Jumlah hasil (1-100) |
| `offset` | Integer | No | 0 | Pagination offset |

**Contoh:**
```
GET /api/contents
GET /api/contents?limit=20
GET /api/contents?publisher=0x123...&limit=10&offset=0
```

**Response Sukses (200 OK):**
```json
{
    "contents": [
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
    ],
    "total": 100,
    "limit": 50,
    "offset": 0
}
```

---

### 11. Get Content by Hash (NEW! ✨)
Mendapatkan detail content berdasarkan hash spesifik.

- **Method**: `GET`
- **Endpoint**: `/api/contents/{p_hash}`

**Contoh:**
```
GET /api/contents/QmXXX...
```

**Response Sukses (200 OK):**
```json
{
    "p_hash": "QmXXX...",
    "publisher": "0x123...",
    "title": "Judul Konten",
    "description": "Deskripsi",
    "timestamp": 1700000000
}
```

**Error Response (404 Not Found):**
```json
{
    "detail": "Content with hash QmXXX... not found"
}
```

---

## 📋 Postman Collection Examples

### Example 1: Gasless Registration Flow

**Step 1: Get Nonce**
```
GET http://localhost:8000/api/nonce/0xYourAddress
```

**Step 2: Generate Signature (di Frontend)**
```javascript
// User sign dengan wallet di frontend
// Signature dikirim ke backend
```

**Step 3: Verify Signature (Optional)**
```json
POST http://localhost:8000/api/verify-signature
Content-Type: application/json

{
    "user_address": "0xYourAddress",
    "p_hash": "QmTest123",
    "title": "Test Content",
    "description": "Test Description",
    "signature": "0xSignatureHere..."
}
```

**Step 4: Submit Registration**
```json
POST http://localhost:8000/api/register-content
Content-Type: application/json

{
    "publisher_address": "0xYourAddress",
    "p_hash": "QmTest123",
    "title": "Test Content",
    "description": "Test Description",
    "signature": "0xSignatureHere..."
}
```

---

### Example 2: Query Contents

**Get first 20 contents:**
```
GET http://localhost:8000/api/contents?limit=20&offset=0
```

**Get contents from specific publisher:**
```
GET http://localhost:8000/api/contents?publisher=0x123...&limit=10
```

**Get specific content:**
```
GET http://localhost:8000/api/contents/QmXXX...
```

---

## ⚙️ Environment Variables

Beberapa perilaku API dipengaruhi oleh file `.env`:

**Blockchain**
- `RPC_URL` - URL RPC blockchain
- `CONTRACT_ADDRESS` / `REGISTRY_ADDRESS` - Address SignetRegistry
- `PRIVATE_KEY` / `RELAYER_PRIVATE_KEY` - Private key untuk transaksi
- `OWNER_ADDRESS` - Address owner contract

**Gasless Transaction**
- `FORWARDER_ADDRESS` - Address MinimalForwarder contract
- `CHAIN_ID` - Chain ID (4202 untuk Lisk Sepolia)

**Verification**
- `HAMMING_THRESHOLD` - Ambang batas toleransi perbedaan gambar (Default: 25)

---

## 🔗 Smart Contracts

**Deployed Contracts:**
- **SignetRegistry**: `0xe13c070791672Bf02e7Fc0C68FBB8b0EF7a547C0`
- **MinimalForwarder**: `0xe35F4015961aB827dAc802393b4DF88083c0B00d`
- **Network**: Lisk Sepolia (Chain ID: 4202)

---

## 📝 Catatan Tambahan

### Telegram Bot
Selain API ini, tersedia juga **Telegram Bot** yang memiliki fitur lebih lengkap.
Bot menggunakan endpoint `/api/verify` di balik layar untuk pemrosesan file.

### Gasless vs Legacy Mode
- **Gasless Mode**: User sign dengan wallet → Publisher tercatat sebagai user address
- **Legacy Mode**: Backend sign → Publisher tercatat sebagai backend address
- Kedua mode tetap didukung untuk backward compatibility

### Interactive API Documentation
Akses **Swagger UI** untuk testing interaktif:
```
http://localhost:8000/docs
```

---

## 🚀 Quick Start Testing

1. **Test Health Check**
   ```bash
   curl http://localhost:8000/
   ```

2. **Test Get Contents**
   ```bash
   curl http://localhost:8000/api/contents?limit=5
   ```

3. **Test Check Publisher**
   ```bash
   curl http://localhost:8000/api/publisher/0xYourAddress
   ```

4. **Test Get Nonce**
   ```bash
   curl http://localhost:8000/api/nonce/0xYourAddress
   ```

---

## 📚 Dokumentasi Lengkap

- **Perbedaan Gasless vs Legacy**: Lihat `PERBEDAAN_GASLESS.md`
- **Panduan Frontend**: Lihat `PANDUAN_FRONTEND_GASLESS.md`
- **Walkthrough Implementation**: Lihat `walkthrough.md`
