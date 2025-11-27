# 🚀 Task: Migrasi Frontend ke Gasless Transaction System

**Priority:** High  
**Deadline:** [ISI DEADLINE]  
**Assignee:** Frontend Team

---

## 📋 Overview

Kita akan **migrasi sistem registrasi content** dari backend-signed transaction ke **user-signed meta-transaction (gasless)**.

### 🎯 Goals:
- ✅ User sign transaksi dengan wallet sendiri (MetaMask)
- ✅ **User address tercatat sebagai publisher** di blockchain (bukan backend)
- ✅ User tetap tidak bayar gas (backend yang bayar)
- ✅ Lebih transparan & terdesentralisasi
- ✅ Menggunakan standar industri (EIP-712 + EIP-2771)

---

## 📦 Files & Resources

### 1. Smart Contract Files (Attached)

File yang saya kirimkan:

```
📁 contracts/
├── abi/
│   ├── MinimalForwarder.json      # ABI untuk meta-transaction forwarder
│   └── SignetRegistry.json        # ABI untuk content registry (UPDATED)
└── solidity/
    ├── MinimalForwarder.sol       # Source code forwarder
    └── SignetRegistry.sol         # Source code registry (UPDATED)
```

**Contract Addresses (Lisk Sepolia):**
- **SignetRegistry**: `0xe13c070791672Bf02e7Fc0C68FBB8b0EF7a547C0`
- **MinimalForwarder**: `0xe35F4015961aB827dAc802393b4DF88083c0B00d`

### 2. Documentation (WAJIB BACA!)

Dokumentasi lengkap ada di folder `backend/`:

1. **MIGRATION_GUIDE.md** ⭐ **START HERE!**
   - Step-by-step migration guide
   - Code comparison (legacy vs gasless)
   - Checklist & testing guide

2. **PANDUAN_FRONTEND_GASLESS.md**
   - Implementasi detail dengan React
   - Helper functions & hooks
   - Error handling & best practices

3. **PERBEDAAN_GASLESS.md**
   - Perbandingan sistem lama vs baru
   - Konsep EIP-712, EIP-2771, Nonce
   - Diagram & penjelasan

4. **API_USAGE.md**
   - API endpoints documentation
   - Request/response examples
   - Testing guide

---

## 🔧 Environment Variables Update

### ❌ OLD (Legacy):

```env
VITE_PROJECT_ID=de217164330f177c24db00e46b038f35
VITE_CONTRACT_ADDRESS=0x92232f0Ef4bbEc80536f5591120cB3cbe8Cf6858
VITE_API_URL=http://localhost:8000/
```

### ✅ NEW (Gasless):

```env
# WalletConnect Project ID (tetap sama)
VITE_PROJECT_ID=de217164330f177c24db00e46b038f35

# Backend API URL (tetap sama)
VITE_API_URL=http://localhost:8000

# Smart Contract Addresses (BARU!)
VITE_REGISTRY_ADDRESS=0xe13c070791672Bf02e7Fc0C68FBB8b0EF7a547C0
VITE_FORWARDER_ADDRESS=0xe35F4015961aB827dAc802393b4DF88083c0B00d

# Network Configuration (BARU!)
VITE_CHAIN_ID=4202
VITE_CHAIN_NAME=Lisk Sepolia
VITE_RPC_URL=https://rpc.sepolia-api.lisk.com

# Legacy contract address (deprecated, untuk backward compatibility)
# VITE_CONTRACT_ADDRESS=0x92232f0Ef4bbEc80536f5591120cB3cbe8Cf6858
```

**Catatan:**
- `VITE_REGISTRY_ADDRESS` = Smart contract untuk register content
- `VITE_FORWARDER_ADDRESS` = Smart contract untuk meta-transaction
- Legacy `VITE_CONTRACT_ADDRESS` bisa di-comment atau dihapus

---

## 📝 Tasks Checklist

### Phase 1: Setup & Dependencies (Day 1)

- [ ] **Baca dokumentasi** (MIGRATION_GUIDE.md & PANDUAN_FRONTEND_GASLESS.md)
- [ ] **Install dependencies**
  ```bash
  npm install ethers@^6.0.0
  # atau
  yarn add ethers@^6.0.0
  ```
- [ ] **Update `.env` file** dengan environment variables baru
- [ ] **Copy ABI files** ke project (`MinimalForwarder.json` & `SignetRegistry.json`)

### Phase 2: Implementation (Day 2-3)

- [ ] **Create config file** - `src/config/blockchain.js`
  - Import contract addresses dari env
  - Define EIP-712 domain & types
  
- [ ] **Create helper functions** - `src/utils/blockchain.js`
  - `encodeRegisterContent()`
  - `getNonce()`
  - `isAuthorizedPublisher()`
  
- [ ] **Create gasless service** - `src/services/gaslessService.js`
  - `registerContentGasless()` - Main function
  - Integrate dengan ethers.js untuk signing
  
- [ ] **Update registration component**
  - Replace legacy upload flow dengan gasless flow
  - Add wallet connection
  - Add signature request
  - Update loading states
  - Update error handling

### Phase 3: Testing (Day 4)

- [ ] **Unit tests**
  - Test helper functions
  - Test error handling
  
- [ ] **Integration tests**
  - Test full registration flow
  - Test wallet connection/disconnection
  
- [ ] **Manual E2E testing**
  - Install MetaMask
  - Connect wallet
  - Add Lisk Sepolia network
  - Test registration flow
  - Verify di blockchain: publisher = user address ✅
  
- [ ] **Error scenarios testing**
  - User rejects signature
  - User not authorized
  - Wrong network
  - Duplicate content

### Phase 4: Deployment (Day 5)

- [ ] **Deploy to staging**
- [ ] **QA testing di staging**
- [ ] **Fix bugs (if any)**
- [ ] **Deploy to production**
- [ ] **Monitor & support**

---

## 🎓 Quick Start Guide

### 1. Read Documentation First!

```
📖 Urutan baca:
1. MIGRATION_GUIDE.md       → Overview & checklist
2. PANDUAN_FRONTEND_GASLESS.md  → Implementation details
3. PERBEDAAN_GASLESS.md     → Understand the concept
4. API_USAGE.md             → API reference
```

### 2. Key Code Changes

**Before (Legacy):**
```javascript
// Upload file, backend sign
const formData = new FormData();
formData.append('file', file);
formData.append('title', title);
formData.append('description', description);

await fetch('/api/register-content', {
  method: 'POST',
  body: formData
});
```

**After (Gasless):**
```javascript
// User sign dengan wallet
const provider = new ethers.BrowserProvider(window.ethereum);
const signer = await provider.getSigner();
const userAddress = await signer.getAddress();

// Get nonce
const nonce = await getNonce(userAddress);

// Encode function
const encodedData = encodeRegisterContent(pHash, title, description);

// Build request
const forwardRequest = {
  from: userAddress,
  to: REGISTRY_ADDRESS,
  value: 0,
  gas: 300000,
  nonce: nonce,
  data: encodedData
};

// User sign (MetaMask popup)
const signature = await signer.signTypedData(
  EIP712_DOMAIN,
  EIP712_TYPES,
  forwardRequest
);

// Submit ke backend
await fetch('/api/register-content', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    publisher_address: userAddress,
    p_hash: pHash,
    title: title,
    description: description,
    signature: signature
  })
});
```

### 3. Testing Checklist

✅ **Manual Testing Steps:**

1. Open aplikasi
2. Click "Register Content"
3. MetaMask popup muncul
4. User review data yang akan di-sign
5. User click "Sign"
6. Transaksi submitted
7. Content registered
8. **Verify**: Cek di blockchain → publisher = user address ✅

---

## 📞 Support & Questions

### Backend Developer Contact:
- **Name:** [NAMA KAMU]
- **Contact:** [CONTACT KAMU]

### Backend API:
- **Local:** http://localhost:8000
- **Staging:** [ISI STAGING URL]
- **Production:** [ISI PRODUCTION URL]

### Smart Contracts:
- **Explorer:** https://sepolia-blockscout.lisk.com
- **Registry Contract:** [Link ke contract]
- **Forwarder Contract:** [Link ke contract]

### Dokumentasi:
- **Backend Repo:** [ISI REPO URL]
- **Docs Folder:** `/backend/` (MIGRATION_GUIDE.md, dll)

---

## ⚠️ Important Notes

### Breaking Changes:

1. **User WAJIB punya wallet** (MetaMask/WalletConnect)
   - Sebelumnya: tidak perlu wallet
   - Sekarang: WAJIB
   
2. **User HARUS di-add sebagai authorized publisher**
   - Hubungi backend untuk add user
   - Atau implement auto-request authorization
   
3. **Network harus Lisk Sepolia (Chain ID: 4202)**
   - Implement auto-switch network
   - Atau instruksikan user untuk manual switch

### Error Handling:

**Common errors yang perlu di-handle:**
- User rejects signature → "You rejected the transaction"
- User not authorized → "Please contact support to get authorized"
- Wrong network → "Please connect to Lisk Sepolia network"
- Duplicate content → "Content already registered"
- Backend error → "Failed to register, please try again"

### User Education:

User perlu tahu:
- Mereka harus install wallet (MetaMask)
- Mereka harus connect ke Lisk Sepolia
- Mereka harus authorized sebagai publisher
- Signing itu aman & gratis (no gas fee)
- Publisher akan tercatat sebagai address mereka

---

## 🎯 Success Criteria

Migrasi dianggap sukses jika:

- [x] User bisa register content dengan wallet
- [x] MetaMask popup muncul untuk signing
- [x] Transaction berhasil submitted
- [x] **Publisher di blockchain = user address** (bukan backend)
- [x] User tidak bayar gas (tetap gratis)
- [x] Error handling lengkap & user-friendly
- [x] Loading states jelas
- [x] E2E testing passed

---

## 📅 Timeline

**Estimasi:** 5 hari kerja

| Day | Tasks | Deliverable |
|-----|-------|-------------|
| 1 | Setup & read docs | Dependencies installed, env updated |
| 2-3 | Implementation | Code complete |
| 4 | Testing | All tests passed |
| 5 | Deployment | Deployed to production |

**Target Launch:** [ISI TARGET DATE]

---

## 🚀 Let's Ship It!

Fitur gasless ini akan meningkatkan:
- ✅ **Decentralization** - User punya kontrol penuh
- ✅ **Transparency** - User tahu apa yang di-sign
- ✅ **Trust** - Publisher = user address di blockchain
- ✅ **UX** - Tetap gratis untuk user

**Kalau ada pertanyaan, langsung tanya ke saya atau baca dokumentasi lengkap di folder backend!**

Good luck & happy coding! 🎉

---

**Attachments:**
1. ✅ MinimalForwarder.json (ABI)
2. ✅ SignetRegistry.json (ABI)
3. ✅ MinimalForwarder.sol (Source)
4. ✅ SignetRegistry.sol (Source)
5. ✅ MIGRATION_GUIDE.md (Documentation)
6. ✅ PANDUAN_FRONTEND_GASLESS.md (Documentation)
7. ✅ PERBEDAAN_GASLESS.md (Documentation)
8. ✅ API_USAGE.md (Documentation)
