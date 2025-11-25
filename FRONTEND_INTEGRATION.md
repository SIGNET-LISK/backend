# Panduan Integrasi Frontend SIGNET

Dokumen ini berisi panduan lengkap untuk tim Frontend (Web/Mobile) untuk mengintegrasikan layanan SIGNET.

## 1. Arsitektur Sistem

Saat ini SIGNET menggunakan metode **Backend Relayer** untuk registrasi. Artinya:
1.  Frontend mengupload file ke Backend API.
2.  Backend menghitung Hash (Fingerprint).
3.  Backend mengirim transaksi ke Blockchain menggunakan wallet admin (Relayer).
4.  Frontend menerima `txHash` sebagai bukti.

*Keuntungan: User tidak perlu membayar Gas fee (Gasless untuk user).*

---

## 2. Smart Contract

Meskipun registrasi dilakukan via API, Frontend mungkin perlu membaca data langsung dari Blockchain untuk transparansi.

*   **Network**: Lisk Sepolia
*   **Contract Address**: *(Lihat file .env di backend)*
*   **ABI (Interface)**:

```json
[
  {
    "inputs": [],
    "stateMutability": "nonpayable",
    "type": "constructor"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "owner",
        "type": "address"
      }
    ],
    "name": "OwnableInvalidOwner",
    "type": "error"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "account",
        "type": "address"
      }
    ],
    "name": "OwnableUnauthorizedAccount",
    "type": "error"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "string",
        "name": "pHash",
        "type": "string"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "publisher",
        "type": "address"
      },
      {
        "indexed": false,
        "internalType": "string",
        "name": "title",
        "type": "string"
      },
      {
        "indexed": false,
        "internalType": "string",
        "name": "description",
        "type": "string"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "timestamp",
        "type": "uint256"
      }
    ],
    "name": "ContentRegisteredFull",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "address",
        "name": "previousOwner",
        "type": "address"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "newOwner",
        "type": "address"
      }
    ],
    "name": "OwnershipTransferred",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "address",
        "name": "clientAddress",
        "type": "address"
      }
    ],
    "name": "PublisherAdded",
    "type": "event"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "_clientWallet",
        "type": "address"
      }
    ],
    "name": "addPublisher",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "name": "allHashes",
    "outputs": [
      {
        "internalType": "string",
        "name": "",
        "type": "string"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "name": "authorizedPublishers",
    "outputs": [
      {
        "internalType": "bool",
        "name": "",
        "type": "bool"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "string",
        "name": "",
        "type": "string"
      }
    ],
    "name": "contentRegistry",
    "outputs": [
      {
        "internalType": "address",
        "name": "publisher",
        "type": "address"
      },
      {
        "internalType": "string",
        "name": "title",
        "type": "string"
      },
      {
        "internalType": "string",
        "name": "description",
        "type": "string"
      },
      {
        "internalType": "uint256",
        "name": "timestamp",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "getAllHashes",
    "outputs": [
      {
        "internalType": "string[]",
        "name": "",
        "type": "string[]"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "string",
        "name": "_pHash",
        "type": "string"
      }
    ],
    "name": "getContentData",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      },
      {
        "internalType": "string",
        "name": "",
        "type": "string"
      },
      {
        "internalType": "string",
        "name": "",
        "type": "string"
      },
      {
        "internalType": "uint256",
        "name": "",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "owner",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "string",
        "name": "_pHash",
        "type": "string"
      },
      {
        "internalType": "string",
        "name": "_title",
        "type": "string"
      },
      {
        "internalType": "string",
        "name": "_desc",
        "type": "string"
      }
    ],
    "name": "registerContent",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "renounceOwnership",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "newOwner",
        "type": "address"
      }
    ],
    "name": "transferOwnership",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  }
]
```

---

## 3. API Reference

**Base URL**: `http://localhost:8000` (Local) / `https://api.signet.com` (Production)

### A. Registrasi Konten
Digunakan di halaman "Upload / Register".

*   **Endpoint**: `POST /api/register-content`
*   **Headers**: `Content-Type: multipart/form-data`
*   **Body**:
    *   `file`: (Binary) File gambar/video.
    *   `title`: (String) Judul konten.
    *   `description`: (String) Deskripsi.

**Contoh Code (Javascript/React):**
```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("title", "My Art");
formData.append("description", "Original creation");

const response = await fetch("http://localhost:8000/api/register-content", {
  method: "POST",
  body: formData
});

const result = await response.json();
console.log(result);
// Output: { status: "SUCCESS", txHash: "0x...", pHash: "..." }
```

### B. Verifikasi Konten
Digunakan di halaman "Verify / Check Authenticity".

*   **Endpoint**: `POST /api/verify`
*   **Headers**: `Content-Type: multipart/form-data`
*   **Body**:
    *   `file`: (Binary) File yang akan dicek.

**Contoh Code:**
```javascript
const formData = new FormData();
formData.append("file", fileToCheck);

const response = await fetch("http://localhost:8000/api/verify", {
  method: "POST",
  body: formData
});

const result = await response.json();

if (result.status === "VERIFIED") {
  alert(`✅ Asli! Publisher: ${result.publisher}`);
} else {
  alert("⚠️ Tidak ditemukan atau palsu.");
}
```

### C. List Konten (Feed)
Digunakan di halaman "Gallery" atau "Recent Uploads".

*   **Endpoint**: `GET /api/contents`

**Contoh Response:**
```json
[
  {
    "id": 1,
    "title": "My Art",
    "pHash": "a1b2...",
    "publisher": "0x123...",
    "txHash": "0xabc...",
    "created_at": "2024-11-25T10:00:00"
  }
]
```

---

## 4. Error Handling

Backend akan mengembalikan standard HTTP Codes:
*   `200 OK`: Sukses.
*   `400 Bad Request`: File tidak ada atau format salah.
*   `500 Internal Server Error`: Masalah di server (misal koneksi blockchain putus).

Pastikan Frontend menangkap error ini:
```javascript
if (!response.ok) {
  const err = await response.json();
  console.error("Error:", err.detail);
}
```
