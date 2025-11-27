// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "openzeppelin-contracts/contracts/utils/cryptography/ECDSA.sol";
import "openzeppelin-contracts/contracts/utils/cryptography/EIP712.sol";

/**
 * @title MinimalForwarder
 * @dev EIP-2771 compliant forwarder untuk meta-transactions
 * Allows relayers to submit transactions on behalf of users while
 * preserving the original sender's identity.
 */
contract MinimalForwarder is EIP712 {
    using ECDSA for bytes32;

    struct ForwardRequest {
        address from;
        address to;
        uint256 value;
        uint256 gas;
        uint256 nonce;
        bytes data;
    }

    bytes32 private constant TYPEHASH =
        keccak256("ForwardRequest(address from,address to,uint256 value,uint256 gas,uint256 nonce,bytes data)");

    mapping(address => uint256) private _nonces;

    event MetaTransactionExecuted(
        address indexed from,
        address indexed to,
        bool success,
        bytes returnData
    );

    constructor() EIP712("MinimalForwarder", "1.0.0") {}

    /**
     * @dev Returns the current nonce for an address
     */
    function getNonce(address from) public view returns (uint256) {
        return _nonces[from];
    }

    /**
     * @dev Verifies the signature of a forward request
     */
    function verify(ForwardRequest calldata req, bytes calldata signature)
        public
        view
        returns (bool)
    {
        address signer = _hashTypedDataV4(
            keccak256(
                abi.encode(
                    TYPEHASH,
                    req.from,
                    req.to,
                    req.value,
                    req.gas,
                    req.nonce,
                    keccak256(req.data)
                )
            )
        ).recover(signature);

        return _nonces[req.from] == req.nonce && signer == req.from;
    }

    /**
     * @dev Executes a meta-transaction
     * The relayer calls this function and pays for gas
     * The actual sender (req.from) is appended to the calldata
     * 
     * Security: Nonce is checked in verify() and incremented atomically
     * to prevent replay attacks and race conditions
     */
    function execute(ForwardRequest calldata req, bytes calldata signature)
        public
        payable
        returns (bool, bytes memory)
    {
        require(
            verify(req, signature),
            "MinimalForwarder: signature does not match request"
        );

        // Increment nonce atomically setelah verify
        // Ini prevent race condition: dua request dengan nonce sama
        unchecked {
            _nonces[req.from]++;
        }

        // Append the real sender address to calldata (EIP-2771)
        bytes memory data = abi.encodePacked(req.data, req.from);

        (bool success, bytes memory returndata) = req.to.call{
            gas: req.gas,
            value: req.value
        }(data);

        // Validate that the call was successful or revert with the error
        if (!success) {
            // If there's a revert reason, bubble it up
            if (returndata.length > 0) {
                assembly {
                    let returndata_size := mload(returndata)
                    revert(add(32, returndata), returndata_size)
                }
            } else {
                revert("MinimalForwarder: call failed without reason");
            }
        }

        emit MetaTransactionExecuted(req.from, req.to, success, returndata);

        return (success, returndata);
    }
}