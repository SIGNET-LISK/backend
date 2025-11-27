# EIP-2771 Gasless Transaction Integration Guide

## 📋 Overview

The SIGNET smart contracts now support **gasless transactions** (meta-transactions) using the EIP-2771 standard. This allows users to interact with the blockchain without paying gas fees - a relayer pays the gas on their behalf while maintaining the user's identity.

## 🔄 What Changed?

### Smart Contracts

#### 1. **New Contract: MinimalForwarder**
- **Location**: `src/MinimalForwarder.sol`
- **Purpose**: Acts as a trusted intermediary for meta-transactions
- **Key Features**:
  - Verifies user signatures using EIP-712
  - Manages nonces to prevent replay attacks
  - Executes transactions on behalf of users
  - Preserves the original sender's identity

#### 2. **Updated Contract: SignetRegistry**
- **Location**: `src/SignetRegistry.sol`
- **Changes**:
  - Now inherits from `ERC2771Context`
  - Constructor requires `trustedForwarder` address
  - All `msg.sender` replaced with `_msgSender()`
  - **Backward Compatible**: Direct calls still work!

### Deployment

The deployment process now deploys **two contracts**:

1. **MinimalForwarder** - The trusted forwarder
2. **SignetRegistry** - The main registry (configured with forwarder address)

---

## 🚀 For Backend Developers

### Contract Addresses

After deployment, you'll receive **two addresses**:

```
Forwarder Address: 0x... (MinimalForwarder)
Registry Address:  0x... (SignetRegistry)
```

**⚠️ IMPORTANT**: Save both addresses! You'll need them for integration.

### How Gasless Transactions Work

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   User      │         │   Backend   │         │  Blockchain │
│  (Wallet B) │         │  (Relayer)  │         │             │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │ 1. Sign transaction   │                       │
       │──────────────────────>│                       │
       │                       │                       │
       │                       │ 2. Submit to forwarder│
       │                       │──────────────────────>│
       │                       │                       │
       │                       │ 3. Forwarder verifies │
       │                       │    & executes         │
       │                       │                       │
       │                       │<──────────────────────│
       │ 4. Event emitted      │    (User = Wallet B)  │
       │    with Wallet B      │                       │
       └───────────────────────┴───────────────────────┘
```

### Implementation Steps

#### Step 1: Install Dependencies

```bash
npm install ethers@^6.0.0
```

#### Step 2: Create Signature Helper

```javascript
const { ethers } = require('ethers');

// EIP-712 Domain for MinimalForwarder
const EIP712_DOMAIN = {
  name: 'MinimalForwarder',
  version: '1.0.0',
  chainId: 1135, // Replace with your chain ID (e.g., 1135 for Lisk)
  verifyingContract: 'FORWARDER_ADDRESS_HERE' // Replace with deployed forwarder address
};

// EIP-712 Type definition
const FORWARD_REQUEST_TYPE = {
  ForwardRequest: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'gas', type: 'uint256' },
    { name: 'nonce', type: 'uint256' },
    { name: 'data', type: 'bytes' }
  ]
};

async function signMetaTransaction(signer, request) {
  const signature = await signer.signTypedData(
    EIP712_DOMAIN,
    FORWARD_REQUEST_TYPE,
    request
  );
  return signature;
}
```

#### Step 3: Get User's Nonce

```javascript
const forwarderABI = [
  "function getNonce(address from) public view returns (uint256)"
];

async function getUserNonce(userAddress) {
  const forwarder = new ethers.Contract(
    FORWARDER_ADDRESS,
    forwarderABI,
    provider
  );
  
  return await forwarder.getNonce(userAddress);
}
```

#### Step 4: Create and Sign Meta-Transaction (Frontend → Backend)

**Frontend sends to backend:**

```javascript
// Example: User wants to register content
const registryInterface = new ethers.Interface([
  "function registerContent(string _pHash, string _title, string _desc)"
]);

// Encode the function call
const data = registryInterface.encodeFunctionData('registerContent', [
  'QmHash123...',
  'My Content Title',
  'Content Description'
]);

// Create the forward request
const request = {
  from: userWalletAddress,      // User's wallet (Wallet B)
  to: REGISTRY_ADDRESS,          // SignetRegistry address
  value: 0,                      // No ETH transfer
  gas: 1000000,                  // Gas limit
  nonce: await getUserNonce(userWalletAddress),
  data: data
};

// User signs the request
const signature = await signMetaTransaction(userSigner, request);

// Send to backend
await fetch('/api/relay-transaction', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ request, signature })
});
```

#### Step 5: Backend Relays Transaction

```javascript
const forwarderABI = [
  "function execute((address from,address to,uint256 value,uint256 gas,uint256 nonce,bytes data) req, bytes signature) public payable returns (bool, bytes)"
];

async function relayTransaction(request, signature) {
  // Backend's wallet (pays for gas)
  const relayerWallet = new ethers.Wallet(RELAYER_PRIVATE_KEY, provider);
  
  const forwarder = new ethers.Contract(
    FORWARDER_ADDRESS,
    forwarderABI,
    relayerWallet
  );

  try {
    // Execute the meta-transaction
    const tx = await forwarder.execute(request, signature, {
      gasLimit: request.gas + 50000 // Add buffer for forwarder overhead
    });
    
    const receipt = await tx.wait();
    
    return {
      success: true,
      txHash: receipt.hash,
      blockNumber: receipt.blockNumber
    };
  } catch (error) {
    console.error('Relay failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
}
```

#### Step 6: Listen for Events

```javascript
const registryABI = [
  "event ContentRegisteredFull(string indexed pHash, address indexed publisher, string title, string description, uint256 timestamp)"
];

const registry = new ethers.Contract(
  REGISTRY_ADDRESS,
  registryABI,
  provider
);

// Listen for content registration
registry.on('ContentRegisteredFull', (pHash, publisher, title, description, timestamp) => {
  console.log('Content registered by:', publisher); // This will be Wallet B (user), not relayer!
  console.log('Content hash:', pHash);
  console.log('Title:', title);
});
```

### API Endpoint Example (Express.js)

```javascript
app.post('/api/relay-transaction', async (req, res) => {
  try {
    const { request, signature } = req.body;
    
    // Optional: Validate request
    // - Check if user is authorized
    // - Verify signature matches request
    // - Rate limiting
    
    const result = await relayTransaction(request, signature);
    
    if (result.success) {
      res.json({
        success: true,
        txHash: result.txHash,
        message: 'Transaction relayed successfully'
      });
    } else {
      res.status(400).json({
        success: false,
        error: result.error
      });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});
```

### Environment Variables

Add these to your `.env`:

```env
# Smart Contract Addresses
FORWARDER_ADDRESS=0x...
REGISTRY_ADDRESS=0x...

# Relayer Configuration
RELAYER_PRIVATE_KEY=0x...
RPC_URL=https://rpc.api.lisk.com

# Chain Configuration
CHAIN_ID=1135
```

---

## 🎨 For Frontend Developers

### Installation

```bash
npm install ethers@^6.0.0
```

### Configuration

Create a config file:

```javascript
// config/contracts.js
export const CONTRACTS = {
  forwarder: {
    address: '0x...', // MinimalForwarder address
    abi: [
      "function getNonce(address from) public view returns (uint256)",
      "function verify((address,address,uint256,uint256,uint256,bytes),bytes) public view returns (bool)"
    ]
  },
  registry: {
    address: '0x...', // SignetRegistry address
    abi: [
      "function registerContent(string _pHash, string _title, string _desc) external",
      "function addPublisher(address _clientWallet) external",
      "function authorizedPublishers(address) public view returns (bool)",
      "function getContentData(string _pHash) public view returns (address, string, string, uint256)"
    ]
  }
};

export const EIP712_DOMAIN = {
  name: 'MinimalForwarder',
  version: '1.0.0',
  chainId: 1135, // Your chain ID
  verifyingContract: CONTRACTS.forwarder.address
};

export const FORWARD_REQUEST_TYPE = {
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

### Usage Example: Register Content (Gasless)

```javascript
import { ethers } from 'ethers';
import { CONTRACTS, EIP712_DOMAIN, FORWARD_REQUEST_TYPE } from './config/contracts';

async function registerContentGasless(pHash, title, description) {
  try {
    // Get user's signer (from MetaMask, WalletConnect, etc.)
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const userAddress = await signer.getAddress();

    // 1. Get user's current nonce
    const forwarder = new ethers.Contract(
      CONTRACTS.forwarder.address,
      CONTRACTS.forwarder.abi,
      provider
    );
    const nonce = await forwarder.getNonce(userAddress);

    // 2. Encode the function call
    const registryInterface = new ethers.Interface(CONTRACTS.registry.abi);
    const data = registryInterface.encodeFunctionData('registerContent', [
      pHash,
      title,
      description
    ]);

    // 3. Create the forward request
    const request = {
      from: userAddress,
      to: CONTRACTS.registry.address,
      value: 0,
      gas: 1000000,
      nonce: Number(nonce),
      data: data
    };

    // 4. Sign the request (EIP-712)
    const signature = await signer.signTypedData(
      EIP712_DOMAIN,
      FORWARD_REQUEST_TYPE,
      request
    );

    // 5. Send to backend for relay
    const response = await fetch('/api/relay-transaction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request, signature })
    });

    const result = await response.json();

    if (result.success) {
      console.log('Transaction hash:', result.txHash);
      return result;
    } else {
      throw new Error(result.error);
    }
  } catch (error) {
    console.error('Gasless transaction failed:', error);
    throw error;
  }
}
```

### React Hook Example

```javascript
import { useState } from 'react';
import { ethers } from 'ethers';

export function useGaslessTransaction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const executeGasless = async (functionName, args) => {
    setLoading(true);
    setError(null);

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const userAddress = await signer.getAddress();

      // Get nonce
      const forwarder = new ethers.Contract(
        CONTRACTS.forwarder.address,
        CONTRACTS.forwarder.abi,
        provider
      );
      const nonce = await forwarder.getNonce(userAddress);

      // Encode function call
      const registryInterface = new ethers.Interface(CONTRACTS.registry.abi);
      const data = registryInterface.encodeFunctionData(functionName, args);

      // Create request
      const request = {
        from: userAddress,
        to: CONTRACTS.registry.address,
        value: 0,
        gas: 1000000,
        nonce: Number(nonce),
        data: data
      };

      // Sign
      const signature = await signer.signTypedData(
        EIP712_DOMAIN,
        FORWARD_REQUEST_TYPE,
        request
      );

      // Relay
      const response = await fetch('/api/relay-transaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request, signature })
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error);
      }

      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { executeGasless, loading, error };
}

// Usage in component:
function RegisterContentForm() {
  const { executeGasless, loading } = useGaslessTransaction();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const result = await executeGasless('registerContent', [
        'QmHash123',
        'My Title',
        'My Description'
      ]);
      
      console.log('Success!', result.txHash);
    } catch (error) {
      console.error('Failed:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* form fields */}
      <button type="submit" disabled={loading}>
        {loading ? 'Processing...' : 'Register Content (No Gas!)'}
      </button>
    </form>
  );
}
```

### Direct Call (User Pays Gas) - Still Supported!

```javascript
async function registerContentDirect(pHash, title, description) {
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  
  const registry = new ethers.Contract(
    CONTRACTS.registry.address,
    CONTRACTS.registry.abi,
    signer
  );

  const tx = await registry.registerContent(pHash, title, description);
  const receipt = await tx.wait();
  
  return receipt;
}
```

---

## 📊 Testing

### Run All Tests

```bash
forge test -vvv
```

### Test Coverage

The test suite includes:

- ✅ Direct calls (backward compatibility)
- ✅ Meta-transaction calls through forwarder
- ✅ Correct sender identification (Wallet B, not relayer)
- ✅ Authorization checks with forwarder
- ✅ Nonce management
- ✅ Signature verification

### Example Test Output

```
[PASS] testDirectCallStillWorks() (gas: 123456)
[PASS] testMetaTxRegisterContent() (gas: 234567)
[PASS] testForwarderCorrectlySetsPublisher() (gas: 234567)
[PASS] testNonceIncrement() (gas: 123456)
```

---

## 🔐 Security Considerations

### For Backend

1. **Rate Limiting**: Implement rate limiting on relay endpoint
2. **Validation**: Verify signatures before relaying
3. **Gas Management**: Monitor relayer wallet balance
4. **Authorization**: Only relay for authorized users
5. **Nonce Tracking**: Track nonces to prevent replay attacks

### For Frontend

1. **Never expose private keys**: Only sign with user's wallet
2. **Verify contract addresses**: Always check you're interacting with correct contracts
3. **User confirmation**: Show clear UI before signing
4. **Error handling**: Handle signature rejections gracefully

---

## 🚨 Important Notes

### Breaking Changes

⚠️ **Constructor Change**: `SignetRegistry` now requires a forwarder address parameter. Old deployment scripts won't work.

**Before:**
```solidity
new SignetRegistry()
```

**After:**
```solidity
new SignetRegistry(forwarderAddress)
```

### Backward Compatibility

✅ **Direct calls still work!** Users can still call functions directly (paying gas themselves). The contract automatically detects whether the call is direct or through the forwarder.

### Gas Costs

- **Direct call**: User pays ~100k gas
- **Meta-transaction**: Relayer pays ~150k gas (includes forwarder overhead)

---

## 📞 Support

If you encounter issues:

1. Check contract addresses are correct
2. Verify chain ID matches
3. Ensure user has signed the transaction
4. Check relayer wallet has sufficient funds
5. Review transaction logs for revert reasons

---

## 📝 Quick Reference

### Contract Addresses (Update after deployment)

```
MinimalForwarder: 0x...
SignetRegistry:   0x...
```

### Key Functions

**MinimalForwarder:**
- `getNonce(address)` - Get user's current nonce
- `verify(request, signature)` - Verify a signed request
- `execute(request, signature)` - Execute a meta-transaction

**SignetRegistry:**
- `registerContent(pHash, title, desc)` - Register content
- `addPublisher(address)` - Add authorized publisher (owner only)
- `authorizedPublishers(address)` - Check if address is publisher
- `getContentData(pHash)` - Get content information

---

## 🎯 Summary

**What you need to do:**

### Backend Team
1. Save both contract addresses (forwarder + registry)
2. Implement signature verification
3. Create relay endpoint
4. Monitor relayer wallet balance
5. Add rate limiting and security measures

### Frontend Team
1. Update contract addresses in config
2. Implement EIP-712 signing
3. Create gasless transaction flow
4. Add loading states and error handling
5. Test with real transactions

**The user experience**: Users sign a message (free), backend pays gas, user's identity is preserved! 🎉
