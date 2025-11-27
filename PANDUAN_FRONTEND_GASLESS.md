# Panduan Frontend - Integrasi Gasless Transaction

## 🎯 Tujuan
Panduan ini untuk frontend developer yang ingin mengintegrasikan fitur gasless transaction di aplikasi SIGNET.

---

## 📦 Instalasi

```bash
npm install ethers@^6.0.0
# atau
yarn add ethers@^6.0.0
```

---

## ⚙️ Konfigurasi

### 1. Setup Konstanta

Buat file `src/config/blockchain.js`:

```javascript
export const BLOCKCHAIN_CONFIG = {
  // Contract Addresses
  FORWARDER_ADDRESS: '0xe35F4015961aB827dAc802393b4DF88083c0B00d',
  REGISTRY_ADDRESS: '0xe13c070791672Bf02e7Fc0C68FBB8b0EF7a547C0',
  
  // Network
  CHAIN_ID: 4202, // Lisk Sepolia
  
  // Backend API
  API_URL: 'http://localhost:8000' // Sesuaikan dengan backend URL
};

// EIP-712 Domain untuk MinimalForwarder
export const EIP712_DOMAIN = {
  name: 'MinimalForwarder',
  version: '1.0.0',
  chainId: BLOCKCHAIN_CONFIG.CHAIN_ID,
  verifyingContract: BLOCKCHAIN_CONFIG.FORWARDER_ADDRESS
};

// EIP-712 Types
export const EIP712_TYPES = {
  ForwardRequest: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'gas', type: 'uint256' },
    { name: 'nonce', type: 'uint256' },
    { name: 'data', type: 'bytes' }
  ]
};
```

---

## 🔧 Helper Functions

### 1. Encode Function Call

```javascript
import { ethers } from 'ethers';
import { BLOCKCHAIN_CONFIG } from './config/blockchain';

/**
 * Encode registerContent function call
 */
export function encodeRegisterContent(pHash, title, description) {
  const iface = new ethers.Interface([
    'function registerContent(string _pHash, string _title, string _desc)'
  ]);
  
  return iface.encodeFunctionData('registerContent', [
    pHash,
    title,
    description
  ]);
}

/**
 * Encode addPublisher function call
 */
export function encodeAddPublisher(publisherAddress) {
  const iface = new ethers.Interface([
    'function addPublisher(address _clientWallet)'
  ]);
  
  return iface.encodeFunctionData('addPublisher', [publisherAddress]);
}
```

---

### 2. Get Nonce

```javascript
import { BLOCKCHAIN_CONFIG } from './config/blockchain';

/**
 * Ambil nonce dari backend
 */
export async function getNonce(userAddress) {
  const response = await fetch(
    `${BLOCKCHAIN_CONFIG.API_URL}/api/nonce/${userAddress}`
  );
  
  const data = await response.json();
  return data.nonce;
}
```

---

### 3. Build ForwardRequest

```javascript
import { BLOCKCHAIN_CONFIG } from './config/blockchain';

/**
 * Build ForwardRequest struct untuk EIP-712
 */
export function buildForwardRequest(userAddress, encodedData, nonce) {
  return {
    from: userAddress,
    to: BLOCKCHAIN_CONFIG.REGISTRY_ADDRESS,
    value: 0,
    gas: 300000,
    nonce: nonce,
    data: encodedData
  };
}
```

---

### 4. Sign dengan EIP-712

```javascript
import { ethers } from 'ethers';
import { EIP712_DOMAIN, EIP712_TYPES } from './config/blockchain';

/**
 * Sign ForwardRequest dengan EIP-712
 */
export async function signForwardRequest(signer, forwardRequest) {
  const signature = await signer.signTypedData(
    EIP712_DOMAIN,
    EIP712_TYPES,
    forwardRequest
  );
  
  return signature;
}
```

---

## 🚀 Implementasi Lengkap

### 1. Register Content (Gasless)

```javascript
import { ethers } from 'ethers';
import { 
  BLOCKCHAIN_CONFIG, 
  EIP712_DOMAIN, 
  EIP712_TYPES 
} from './config/blockchain';
import {
  encodeRegisterContent,
  getNonce,
  buildForwardRequest,
  signForwardRequest
} from './helpers/blockchain';

/**
 * Register content tanpa bayar gas
 */
export async function registerContentGasless(pHash, title, description) {
  try {
    // 1. Connect ke wallet user (MetaMask, dll)
    if (!window.ethereum) {
      throw new Error('Please install MetaMask!');
    }
    
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const userAddress = await signer.getAddress();
    
    console.log('User address:', userAddress);
    
    // 2. Cek apakah user adalah authorized publisher
    const publisherCheckResponse = await fetch(
      `${BLOCKCHAIN_CONFIG.API_URL}/api/publisher/${userAddress}`
    );
    const publisherStatus = await publisherCheckResponse.json();
    
    if (!publisherStatus.is_authorized) {
      throw new Error('Anda belum terdaftar sebagai publisher. Hubungi admin!');
    }
    
    // 3. Ambil nonce dari backend
    const nonce = await getNonce(userAddress);
    console.log('Current nonce:', nonce);
    
    // 4. Encode function call
    const encodedData = encodeRegisterContent(pHash, title, description);
    console.log('Encoded data:', encodedData);
    
    // 5. Build ForwardRequest
    const forwardRequest = buildForwardRequest(userAddress, encodedData, nonce);
    console.log('Forward request:', forwardRequest);
    
    // 6. User sign dengan wallet (EIP-712)
    console.log('Meminta user untuk sign...');
    const signature = await signForwardRequest(signer, forwardRequest);
    console.log('Signature:', signature);
    
    // 7. (Optional) Verify signature dulu
    const verifyResponse = await fetch(
      `${BLOCKCHAIN_CONFIG.API_URL}/api/verify-signature`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_address: userAddress,
          p_hash: pHash,
          title: title,
          description: description,
          signature: signature
        })
      }
    );
    
    const verifyResult = await verifyResponse.json();
    if (!verifyResult.valid) {
      throw new Error('Signature tidak valid: ' + verifyResult.error);
    }
    
    console.log('Signature valid! Mengirim ke backend...');
    
    // 8. Submit ke backend untuk di-relay
    const registerResponse = await fetch(
      `${BLOCKCHAIN_CONFIG.API_URL}/api/register-content`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          publisher_address: userAddress,
          p_hash: pHash,
          title: title,
          description: description,
          signature: signature
        })
      }
    );
    
    if (!registerResponse.ok) {
      const errorData = await registerResponse.json();
      throw new Error(errorData.detail || 'Gagal register content');
    }
    
    const result = await registerResponse.json();
    console.log('Success!', result);
    
    return {
      success: true,
      txHash: result.tx_hash,
      blockNumber: result.block_number,
      message: 'Content berhasil diregister tanpa bayar gas!'
    };
    
  } catch (error) {
    console.error('Error:', error);
    
    // Handle error yang umum
    if (error.code === 'ACTION_REJECTED') {
      throw new Error('User menolak untuk sign transaksi');
    }
    
    throw error;
  }
}
```

---

### 2. React Hook untuk Gasless Transaction

```javascript
import { useState } from 'react';
import { registerContentGasless } from '../services/blockchain';

export function useGaslessRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  
  const register = async (pHash, title, description) => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const txResult = await registerContentGasless(pHash, title, description);
      setResult(txResult);
      return txResult;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };
  
  return {
    register,
    loading,
    error,
    result
  };
}
```

---

### 3. Komponen React untuk Form

```javascript
import React, { useState } from 'react';
import { useGaslessRegister } from '../hooks/useGaslessRegister';

export function RegisterContentForm() {
  const [pHash, setPHash] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  
  const { register, loading, error, result } = useGaslessRegister();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      await register(pHash, title, description);
      alert('Content berhasil diregister!');
      
      // Reset form
      setPHash('');
      setTitle('');
      setDescription('');
    } catch (err) {
      // Error sudah di-handle di hook
      console.error('Submit failed:', err);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Content Hash (IPFS):</label>
        <input
          type="text"
          value={pHash}
          onChange={(e) => setPHash(e.target.value)}
          placeholder="Qm..."
          required
        />
      </div>
      
      <div>
        <label>Title:</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>
      
      <div>
        <label>Description:</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
      </div>
      
      <button type="submit" disabled={loading}>
        {loading ? 'Processing...' : 'Register Content (No Gas!)'}
      </button>
      
      {error && <div className="error">{error}</div>}
      {result && (
        <div className="success">
          ✅ Success! TX: {result.txHash}
        </div>
      )}
    </form>
  );
}
```

---

## 🎨 Flow Lengkap di UI

### Step-by-Step untuk User

```javascript
/**
 * Flow lengkap dengan feedback ke user
 */
export async function registerWithSteps(pHash, title, description, onProgress) {
  try {
    // Step 1: Connect wallet
    onProgress('Connecting to wallet...');
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const userAddress = await signer.getAddress();
    
    // Step 2: Check authorization
    onProgress('Checking publisher status...');
    const publisherCheck = await fetch(
      `${BLOCKCHAIN_CONFIG.API_URL}/api/publisher/${userAddress}`
    );
    const publisherStatus = await publisherCheck.json();
    
    if (!publisherStatus.is_authorized) {
      throw new Error('You are not an authorized publisher');
    }
    
    // Step 3: Get nonce
    onProgress('Getting nonce...');
    const nonce = await getNonce(userAddress);
    
    // Step 4: Build request
    onProgress('Building transaction...');
    const encodedData = encodeRegisterContent(pHash, title, description);
    const forwardRequest = buildForwardRequest(userAddress, encodedData, nonce);
    
    // Step 5: Sign
    onProgress('Waiting for signature... (Check your wallet)');
    const signature = await signForwardRequest(signer, forwardRequest);
    
    // Step 6: Verify
    onProgress('Verifying signature...');
    const verifyResponse = await fetch(
      `${BLOCKCHAIN_CONFIG.API_URL}/api/verify-signature`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_address: userAddress,
          p_hash: pHash,
          title: title,
          description: description,
          signature: signature
        })
      }
    );
    
    const verifyResult = await verifyResponse.json();
    if (!verifyResult.valid) {
      throw new Error('Invalid signature');
    }
    
    // Step 7: Submit
    onProgress('Submitting to blockchain...');
    const registerResponse = await fetch(
      `${BLOCKCHAIN_CONFIG.API_URL}/api/register-content`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          publisher_address: userAddress,
          p_hash: pHash,
          title: title,
          description: description,
          signature: signature
        })
      }
    );
    
    if (!registerResponse.ok) {
      const errorData = await registerResponse.json();
      throw new Error(errorData.detail);
    }
    
    const result = await registerResponse.json();
    
    // Step 8: Done
    onProgress('Transaction confirmed!');
    
    return result;
    
  } catch (error) {
    onProgress('Error: ' + error.message);
    throw error;
  }
}
```

---

## 🔍 Query Content

### Get All Contents

```javascript
/**
 * Ambil semua content dengan pagination
 */
export async function getAllContents(publisher = null, limit = 50, offset = 0) {
  let url = `${BLOCKCHAIN_CONFIG.API_URL}/api/contents?limit=${limit}&offset=${offset}`;
  
  if (publisher) {
    url += `&publisher=${publisher}`;
  }
  
  const response = await fetch(url);
  const data = await response.json();
  
  return data;
}
```

### Get Content by Hash

```javascript
/**
 * Ambil detail content berdasarkan hash
 */
export async function getContentByHash(pHash) {
  const response = await fetch(
    `${BLOCKCHAIN_CONFIG.API_URL}/api/contents/${pHash}`
  );
  
  if (!response.ok) {
    throw new Error('Content not found');
  }
  
  const data = await response.json();
  return data;
}
```

---

## ⚠️ Error Handling

### Common Errors

```javascript
export function handleBlockchainError(error) {
  // User rejected transaction
  if (error.code === 'ACTION_REJECTED') {
    return 'User menolak untuk sign transaksi';
  }
  
  // Not authorized publisher
  if (error.message.includes('not authorized')) {
    return 'Anda belum terdaftar sebagai publisher. Hubungi admin untuk didaftarkan.';
  }
  
  // Invalid signature
  if (error.message.includes('Invalid signature')) {
    return 'Signature tidak valid. Silakan coba lagi.';
  }
  
  // Duplicate content
  if (error.message.includes('already registered')) {
    return 'Content dengan hash ini sudah pernah diregister.';
  }
  
  // Network error
  if (error.message.includes('network')) {
    return 'Koneksi ke blockchain gagal. Cek koneksi internet Anda.';
  }
  
  // Generic error
  return error.message || 'Terjadi kesalahan. Silakan coba lagi.';
}
```

---

## ✅ Checklist Testing

### Sebelum Deploy

- [ ] MetaMask terinstall dan connected
- [ ] User sudah di-add sebagai publisher
- [ ] Backend berjalan dan accessible
- [ ] Contract addresses sudah benar di config
- [ ] Chain ID sesuai (4202 untuk Lisk Sepolia)

### Testing Flow

1. **Connect Wallet**
   ```javascript
   // Test connection
   const accounts = await window.ethereum.request({ 
     method: 'eth_requestAccounts' 
   });
   console.log('Connected:', accounts[0]);
   ```

2. **Check Publisher Status**
   ```javascript
   const status = await fetch(
     `${API_URL}/api/publisher/${userAddress}`
   ).then(r => r.json());
   console.log('Is authorized:', status.is_authorized);
   ```

3. **Get Nonce**
   ```javascript
   const nonceData = await fetch(
     `${API_URL}/api/nonce/${userAddress}`
   ).then(r => r.json());
   console.log('Nonce:', nonceData.nonce);
   ```

4. **Sign & Submit**
   ```javascript
   // Sesuai flow di atas
   ```

---

## 🎯 Best Practices

### 1. User Feedback
```javascript
// Berikan feedback yang jelas ke user
const steps = [
  'Connecting wallet...',
  'Checking authorization...',
  'Preparing transaction...',
  'Waiting for signature...',
  'Submitting to blockchain...',
  'Confirming transaction...',
  'Done!'
];
```

### 2. Error Handling
```javascript
// Selalu handle error dengan baik
try {
  await registerContentGasless(pHash, title, desc);
} catch (error) {
  const userMessage = handleBlockchainError(error);
  showErrorToUser(userMessage);
}
```

### 3. Loading States
```javascript
// Gunakan loading state untuk UX yang baik
const [isLoading, setIsLoading] = useState(false);

// Disable button saat loading
<button disabled={isLoading}>
  {isLoading ? 'Processing...' : 'Register'}
</button>
```

### 4. Validation
```javascript
// Validate input sebelum submit
if (!pHash || !pHash.startsWith('Qm')) {
  throw new Error('Invalid IPFS hash');
}

if (!title || title.length < 3) {
  throw new Error('Title too short');
}
```

---

## 🚀 Ready to Use!

Sekarang frontend siap untuk mengintegrasikan gasless transaction! User bisa:
- ✅ Register content tanpa bayar gas
- ✅ Identitas tercatat di blockchain
- ✅ UX yang smooth dengan feedback yang jelas
- ✅ Error handling yang baik

**Happy coding! 🎉**
