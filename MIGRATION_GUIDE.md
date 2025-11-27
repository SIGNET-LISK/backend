# Migration Guide: Legacy ke Gasless Transaction

Panduan lengkap untuk migrasi frontend dari **Backend-Signed** (legacy) ke **User-Signed Meta-Transaction** (gasless).

---

## 📋 Checklist Migrasi

### Pre-Migration

- [ ] **Backend sudah running** dengan gasless support
- [ ] **Environment variables** backend sudah diset (FORWARDER_ADDRESS, dll)
- [ ] **Smart contracts deployed** dan address sudah benar
- [ ] **User sudah di-add** sebagai authorized publisher (untuk testing)
- [ ] **Install dependencies** di frontend (`ethers@^6.0.0`)

### Implementation

- [ ] **Config file** dibuat dengan contract addresses
- [ ] **Helper functions** untuk encode & sign
- [ ] **Update registration flow** dengan signature
- [ ] **Error handling** untuk wallet rejection
- [ ] **Loading states** untuk user feedback
- [ ] **Fallback ke legacy** (optional, untuk backward compatibility)

### Testing

- [ ] **MetaMask installed** dan connected
- [ ] **Test signature flow** end-to-end
- [ ] **Test error scenarios** (rejection, invalid signature, dll)
- [ ] **Test publisher check** sebelum register
- [ ] **Verifikasi di blockchain** publisher = user address

### Deployment

- [ ] **Update dokumentasi** untuk user
- [ ] **Training untuk tim** tentang cara kerja gasless
- [ ] **Monitoring** transaction success rate
- [ ] **User communication** tentang perubahan flow

---

## 🔄 Perbandingan Kode: Legacy vs Gasless

### Legacy Mode (Cara Lama)

```javascript
// ❌ Cara Lama - Upload file, backend sign
async function registerContent(file, title, description) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  formData.append('description', description);
  
  const response = await fetch('/api/register-content', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
  // Publisher = Backend address
}
```

### Gasless Mode (Cara Baru)

```javascript
// ✅ Cara Baru - User sign, identitas terjaga
async function registerContentGasless(pHash, title, description) {
  // 1. Connect wallet
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const userAddress = await signer.getAddress();
  
  // 2. Get nonce
  const nonceRes = await fetch(`/api/nonce/${userAddress}`);
  const { nonce } = await nonceRes.json();
  
  // 3. Encode function data
  const encodedData = encodeRegisterContent(pHash, title, description);
  
  // 4. Build ForwardRequest
  const forwardRequest = {
    from: userAddress,
    to: REGISTRY_ADDRESS,
    value: 0,
    gas: 300000,
    nonce: nonce,
    data: encodedData
  };
  
  // 5. User sign dengan wallet
  const signature = await signer.signTypedData(
    EIP712_DOMAIN,
    EIP712_TYPES,
    forwardRequest
  );
  
  // 6. Submit ke backend
  const response = await fetch('/api/register-content', {
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
  
  return await response.json();
  // Publisher = User address ✅
}
```

---

## 🚀 Step-by-Step Migration

### Step 1: Setup Dependencies

```bash
npm install ethers@^6.0.0
# atau
yarn add ethers@^6.0.0
```

### Step 2: Create Config File

Buat `src/config/blockchain.js`:

```javascript
export const BLOCKCHAIN_CONFIG = {
  FORWARDER_ADDRESS: '0xe35F4015961aB827dAc802393b4DF88083c0B00d',
  REGISTRY_ADDRESS: '0xe13c070791672Bf02e7Fc0C68FBB8b0EF7a547C0',
  CHAIN_ID: 4202,
  API_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000'
};

export const EIP712_DOMAIN = {
  name: 'MinimalForwarder',
  version: '1.0.0',
  chainId: BLOCKCHAIN_CONFIG.CHAIN_ID,
  verifyingContract: BLOCKCHAIN_CONFIG.FORWARDER_ADDRESS
};

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

### Step 3: Create Helper Functions

Buat `src/utils/blockchain.js`:

```javascript
import { ethers } from 'ethers';
import { BLOCKCHAIN_CONFIG } from '../config/blockchain';

// Encode registerContent function
export function encodeRegisterContent(pHash, title, description) {
  const iface = new ethers.Interface([
    'function registerContent(string _pHash, string _title, string _desc)'
  ]);
  return iface.encodeFunctionData('registerContent', [pHash, title, description]);
}

// Get nonce from backend
export async function getNonce(userAddress) {
  const response = await fetch(`${BLOCKCHAIN_CONFIG.API_URL}/api/nonce/${userAddress}`);
  const data = await response.json();
  return data.nonce;
}

// Check if user is authorized publisher
export async function isAuthorizedPublisher(userAddress) {
  const response = await fetch(`${BLOCKCHAIN_CONFIG.API_URL}/api/publisher/${userAddress}`);
  const data = await response.json();
  return data.is_authorized;
}
```

### Step 4: Create Gasless Service

Buat `src/services/gaslessService.js`:

```javascript
import { ethers } from 'ethers';
import { BLOCKCHAIN_CONFIG, EIP712_DOMAIN, EIP712_TYPES } from '../config/blockchain';
import { encodeRegisterContent, getNonce, isAuthorizedPublisher } from '../utils/blockchain';

export async function registerContentGasless(pHash, title, description) {
  // 1. Check wallet
  if (!window.ethereum) {
    throw new Error('Please install MetaMask or another Web3 wallet');
  }
  
  // 2. Connect wallet
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const userAddress = await signer.getAddress();
  
  // 3. Check authorization
  const isAuthorized = await isAuthorizedPublisher(userAddress);
  if (!isAuthorized) {
    throw new Error('You are not an authorized publisher. Please contact admin.');
  }
  
  // 4. Get nonce
  const nonce = await getNonce(userAddress);
  
  // 5. Encode function data
  const encodedData = encodeRegisterContent(pHash, title, description);
  
  // 6. Build ForwardRequest
  const forwardRequest = {
    from: userAddress,
    to: BLOCKCHAIN_CONFIG.REGISTRY_ADDRESS,
    value: 0,
    gas: 300000,
    nonce: nonce,
    data: encodedData
  };
  
  // 7. User sign
  const signature = await signer.signTypedData(
    EIP712_DOMAIN,
    EIP712_TYPES,
    forwardRequest
  );
  
  // 8. Submit to backend
  const response = await fetch(`${BLOCKCHAIN_CONFIG.API_URL}/api/register-content`, {
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
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to register content');
  }
  
  return await response.json();
}
```

### Step 5: Update React Component

```javascript
import React, { useState } from 'react';
import { registerContentGasless } from '../services/gaslessService';

function RegisterContent() {
  const [pHash, setPHash] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [txHash, setTxHash] = useState(null);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setTxHash(null);
    
    try {
      const result = await registerContentGasless(pHash, title, description);
      setTxHash(result.tx_hash);
      alert('Content registered successfully!');
      
      // Reset form
      setPHash('');
      setTitle('');
      setDescription('');
    } catch (err) {
      setError(err.message);
      console.error('Registration failed:', err);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <h2>Register Content (Gasless)</h2>
      
      <form onSubmit={handleSubmit}>
        <div>
          <label>Content Hash (IPFS):</label>
          <input
            type="text"
            value={pHash}
            onChange={(e) => setPHash(e.target.value)}
            placeholder="Qm..."
            required
            disabled={loading}
          />
        </div>
        
        <div>
          <label>Title:</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        
        <div>
          <label>Description:</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Processing...' : 'Register Content (No Gas Fee!)'}
        </button>
      </form>
      
      {error && (
        <div style={{ color: 'red', marginTop: '10px' }}>
          ❌ Error: {error}
        </div>
      )}
      
      {txHash && (
        <div style={{ color: 'green', marginTop: '10px' }}>
          ✅ Success! Transaction: {txHash}
        </div>
      )}
    </div>
  );
}

export default RegisterContent;
```

---

## ⚠️ Breaking Changes

### 1. Wallet Required
**Legacy:** Tidak perlu wallet  
**Gasless:** **WAJIB punya wallet** (MetaMask, WalletConnect, dll)

**Solusi:** Instruksikan user untuk install wallet sebelum register

### 2. User Harus Authorized
**Legacy:** Siapa saja bisa register (backend yang check)  
**Gasless:** **User harus di-add** sebagai authorized publisher

**Solusi:** Tambah UI untuk request authorization atau auto-add di backend

### 3. Network Harus Benar
**Legacy:** User tidak perlu connect ke network  
**Gasless:** **User harus connect** ke Lisk Sepolia (Chain ID: 4202)

**Solusi:** Tambah fungsi untuk auto-switch network:

```javascript
async function switchToLiskSepolia() {
  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: '0x106A' }], // 4202 in hex
    });
  } catch (error) {
    // Chain not added, add it
    if (error.code === 4902) {
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [{
          chainId: '0x106A',
          chainName: 'Lisk Sepolia',
          rpcUrls: ['https://rpc.sepolia-api.lisk.com'],
          nativeCurrency: {
            name: 'Sepolia Ether',
            symbol: 'ETH',
            decimals: 18
          },
          blockExplorerUrls: ['https://sepolia-blockscout.lisk.com']
        }]
      });
    }
  }
}
```

---

## 🔍 Error Handling

### Common Errors & Solutions

```javascript
export function handleGaslessError(error) {
  // User rejected
  if (error.code === 'ACTION_REJECTED' || error.code === 4001) {
    return 'You rejected the transaction. Please try again.';
  }
  
  // Not authorized
  if (error.message.includes('not authorized')) {
    return 'You are not an authorized publisher. Please contact support.';
  }
  
  // Invalid signature
  if (error.message.includes('Invalid signature')) {
    return 'Signature verification failed. Please try again.';
  }
  
  // Already registered
  if (error.message.includes('already registered')) {
    return 'This content has already been registered.';
  }
  
  // Wrong network
  if (error.code === -32603) {
    return 'Please connect to Lisk Sepolia network.';
  }
  
  // Generic
  return error.message || 'An error occurred. Please try again.';
}
```

---

## 📊 Testing Checklist

### Unit Tests

- [ ] `encodeRegisterContent()` returns correct encoded data
- [ ] `getNonce()` fetches nonce from backend
- [ ] `isAuthorizedPublisher()` checks authorization

### Integration Tests

- [ ] Full registration flow works end-to-end
- [ ] Error handling works for all scenarios
- [ ] Wallet connection/disconnection handled properly
- [ ] Network switching works

### E2E Tests (Manual)

1. **Happy Path:**
   - [ ] User connects wallet
   - [ ] User is authorized publisher
   - [ ] MetaMask popup appears
   - [ ] User signs
   - [ ] Transaction submitted
   - [ ] Publisher = user address di blockchain ✅

2. **Error Scenarios:**
   - [ ] User rejects signature → proper error message
   - [ ] User not authorized → proper error message
   - [ ] Wrong network → auto-switch atau error message
   - [ ] Duplicate content → proper error message
   - [ ] Backend down → proper error message

---

## 🎯 Rollout Strategy

### Phase 1: Soft Launch (Optional)
- Deploy gasless ke staging
- Test dengan internal team
- Gather feedback
- Fix bugs

### Phase 2: Beta (Optional)
- Enable gasless untuk selected users
- Monitor transaction success rate
- Check gas consumption di backend
- Optimize if needed

### Phase 3: Full Launch
- Enable gasless untuk all users
- Keep legacy as fallback (optional)
- Monitor dan support users
- Document common issues

### Phase 4: Deprecate Legacy (Optional)
- Announce legacy deprecation
- Migrate remaining users
- Remove legacy code
- Celebrate! 🎉

---

## 📚 Resources

### Dokumentasi

1. **PANDUAN_FRONTEND_GASLESS.md** - Panduan lengkap implementasi
2. **PERBEDAAN_GASLESS.md** - Perbandingan sistem lama vs baru
3. **API_USAGE.md** - Dokumentasi API endpoints
4. **walkthrough.md** - Implementation details

### External Resources

- [EIP-712 Specification](https://eips.ethereum.org/EIPS/eip-712)
- [EIP-2771 Specification](https://eips.ethereum.org/EIPS/eip-2771)
- [ethers.js Documentation](https://docs.ethers.org/)
- [MetaMask Documentation](https://docs.metamask.io/)

---

## 💡 Tips & Best Practices

### 1. User Experience
```javascript
// ✅ Berikan feedback yang jelas
const steps = [
  'Connecting wallet...',
  'Checking authorization...',
  'Preparing transaction...',
  'Waiting for signature...',
  'Submitting to blockchain...',
  'Done!'
];
```

### 2. Error Messages
```javascript
// ✅ Error message yang user-friendly
if (!isAuthorized) {
  throw new Error(
    'You are not authorized to publish content. ' +
    'Please contact support at support@signet.com to get authorized.'
  );
}
```

### 3. Loading States
```javascript
// ✅ Disable button & show progress
<button disabled={loading}>
  {loading ? (
    <>
      <Spinner /> Processing...
    </>
  ) : (
    'Register Content'
  )}
</button>
```

### 4. Validation
```javascript
// ✅ Validate sebelum submit
if (!pHash || !pHash.startsWith('Qm')) {
  throw new Error('Invalid IPFS hash format');
}

if (title.length < 3) {
  throw new Error('Title must be at least 3 characters');
}
```

---

## ✅ Final Checklist

Sebelum deploy ke production:

- [ ] ✅ Semua dependencies terinstall
- [ ] ✅ Config files sudah benar
- [ ] ✅ Helper functions tested
- [ ] ✅ Error handling lengkap
- [ ] ✅ Loading states implemented
- [ ] ✅ User feedback messages user-friendly
- [ ] ✅ Network switching works
- [ ] ✅ Publisher check implemented
- [ ] ✅ End-to-end testing passed
- [ ] ✅ Documentation updated
- [ ] ✅ Team trained
- [ ] ✅ Support prepared

---

## 🆘 Need Help?

**Backend Issues:**
- Cek logs di backend
- Verify contract addresses
- Test endpoints dengan Postman (legacy mode)

**Frontend Issues:**
- Check browser console
- Verify wallet connected
- Check network (Lisk Sepolia)
- Test with MetaMask

**Smart Contract Issues:**
- Verify contracts deployed
- Check contract addresses
- Verify user authorized as publisher

---

## 🎉 You're Ready!

Setelah mengikuti panduan ini, tim frontend siap untuk migrasi ke gasless transaction!

**Key Benefits:**
- ✅ User identity preserved on blockchain
- ✅ More transparent & decentralized
- ✅ Industry standard (EIP-712)
- ✅ Still free for users (no gas!)

**Happy Migrating! 🚀**
