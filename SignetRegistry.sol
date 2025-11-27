// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "openzeppelin-contracts/contracts/metatx/ERC2771Context.sol";
import "openzeppelin-contracts/contracts/access/Ownable.sol";
import "openzeppelin-contracts/contracts/utils/Context.sol";

contract SignetRegistry is ERC2771Context, Ownable {
    
    struct Content {
        address publisher;
        string title;
        string description;
        uint256 timestamp;
    }
    
    mapping(string => Content) public contentRegistry;
    mapping(address => bool) public authorizedPublishers;
    string[] public allHashes;

    event PublisherAdded(address indexed clientAddress);
    event ContentRegisteredFull(
        string indexed pHash,
        address indexed publisher,
        string title,
        string description,
        uint256 timestamp
    );

    constructor(address _trustedForwarder) 
        ERC2771Context(_trustedForwarder)
        Ownable(_msgSender()) 
    {}

    modifier onlyPublisher() {
        require(authorizedPublishers[_msgSender()] == true, "SIGNET: Not an authorized publisher.");
        _;
    }

    function addPublisher(address _clientWallet) external onlyOwner {
        require(_clientWallet != address(0), "SIGNET: Invalid address.");
        require(!authorizedPublishers[_clientWallet], "SIGNET: Client already registered.");

        authorizedPublishers[_clientWallet] = true;
        emit PublisherAdded(_clientWallet); 
    }

    function registerContent(
        string memory _pHash, 
        string memory _title, 
        string memory _desc
    ) external onlyPublisher {
        
        require(bytes(_pHash).length > 0, "SIGNET: Hash cannot be empty.");
        require(contentRegistry[_pHash].publisher == address(0), "SIGNET: Hash already registered."); 

        contentRegistry[_pHash] = Content({
            publisher: _msgSender(),
            title: _title,
            description: _desc,
            timestamp: block.timestamp
        });

        allHashes.push(_pHash);

        emit ContentRegisteredFull(
            _pHash,
            _msgSender(),
            _title,
            _desc,
            block.timestamp
        );
    }

    function getAllHashes() public view returns (string[] memory) {
        return allHashes;
    }

    function getContentData(string memory _pHash) 
        public 
        view 
        returns (address, string memory, string memory, uint256) 
    {
        Content storage content = contentRegistry[_pHash];
        require(content.publisher != address(0), "SIGNET: Content not found.");

        return (
            content.publisher,
            content.title,
            content.description,
            content.timestamp
        );
    }

    // Override functions untuk mengatasi konflik antara ERC2771Context dan Ownable
    function _msgSender() internal view virtual override(ERC2771Context, Context) returns (address) {
        return ERC2771Context._msgSender();
    }

    function _msgData() internal view virtual override(ERC2771Context, Context) returns (bytes calldata) {
        return ERC2771Context._msgData();
    }

    function _contextSuffixLength() internal view virtual override(ERC2771Context, Context) returns (uint256) {
        return ERC2771Context._contextSuffixLength();
    }
}
