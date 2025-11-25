# Backend & Indexer Sistem SIGNET

Ini adalah sistem backend lengkap untuk SIGNET, mencakup server FastAPI, Indexer Blockchain, dan Bot Telegram.

## Prasyarat

- Python 3.9+
- PostgreSQL
- FFmpeg (untuk pemrosesan video)

## Instalasi & Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Konfigurasi Environment**:
    Copy file `.env` dan isi detailnya:
    ```bash
    RPC_URL=https://rpc.sepolia-api.lisk.com
    CONTRACT_ADDRESS=<ALAMAT_KONTRAK_ANDA>
    PRIVATE_KEY=<PRIVATE_KEY_ANDA>
    DB_HOST=localhost
    DB_PORT=5432
    DB_USER=postgres
    DB_PASSWORD=<password>
    DB_NAME=signet_indexer
    TELEGRAM_BOT_TOKEN=<TOKEN_BOT_TELEGRAM_ANDA>
    ```

3.  **Setup Database**:
    Buat database dan tabel:
    ```bash
    # Pastikan PostgreSQL berjalan dan database 'signet_indexer' sudah dibuat
    psql -U postgres -d signet_indexer -f database/schema.sql
    ```
    *Catatan: Aplikasi juga akan mencoba membuat tabel secara otomatis saat dijalankan menggunakan SQLAlchemy.*

## Cara Menjalankan Sistem

Anda perlu menjalankan tiga proses terpisah (buka 3 terminal):

### 1. Menjalankan Indexer Service
Service ini mendengarkan event dari blockchain Lisk dan mengupdate database serta index ANN.
```bash
python -m indexer.listener
```
*Pastikan muncul pesan "Listening for events..."*

### 2. Menjalankan Backend API
Menyediakan endpoint REST untuk registrasi dan verifikasi.
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- Akses Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Menjalankan Bot Telegram
Bot untuk interaksi user melakukan verifikasi.
```bash
python -m telegram.bot
```

## Penggunaan API

-   **Registrasi Konten**: `POST /api/register-content`
    -   Upload file (gambar/video) beserta judul dan deskripsi.
    -   Sistem akan membuat hash dan mengirim transaksi ke blockchain.
-   **Verifikasi Konten**: `POST /api/verify`
    -   Upload file untuk dicek keasliannya.
    -   Sistem akan mencari kemiripan di database.
-   **List Konten**: `GET /api/contents`
    -   Melihat daftar konten yang sudah terdaftar.

## Struktur Proyek

-   `api/`: Handler route FastAPI.
-   `services/`: Logika inti (Hashing, Blockchain, Verifier).
-   `indexer/`: Listener event blockchain dan sinkronisasi DB.
-   `telegram/`: Logika bot Telegram.
-   `database/`: Skema SQL.
-   `models/`: Model SQLAlchemy.
