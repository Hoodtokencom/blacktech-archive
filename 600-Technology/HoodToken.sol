// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title HoodToken (HOOD)
 * @author Blacktech Solutions Corp
 * @notice Community-governed ERC-20 token for the Neighborhood Blockchain Hub
 * @dev Features: capped supply, community rewards, governance voting, multisig admin
 */

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";

contract HoodToken is ERC20, ERC20Burnable, ERC20Votes, AccessControl {
    bytes32 public constant COMMUNITY_ROLE = keccak256("COMMUNITY_ROLE");
    bytes32 public constant BRIDGE_ROLE = keccak256("BRIDGE_ROLE");

    // --- Tokenomics ---
    uint256 public constant MAX_SUPPLY = 100_000_000 * 10**18; // 100M HOOD
    uint256 public constant COMMUNITY_REWARD_POOL = 40_000_000 * 10**18;  // 40M
    uint256 public constant LIQUIDITY_POOL = 20_000_000 * 10**18;         // 20M
    uint256 public constant TEAM_ADVISORS = 15_000_000 * 10**18;          // 15M (2yr vest)
    uint256 public constant ECOSYSTEM_FUND = 15_000_000 * 10**18;         // 15M
    uint256 public constant AIRDROP_RESERVE = 10_000_000 * 10**18;        // 10M

    uint256 public communityRewardsDistributed;
    uint256 public airdropDistributed;

    // --- Events ---
    event CommunityReward(address indexed to, uint256 amount, string reason);
    event AirdropClaim(address indexed to, uint256 amount);
    event BridgeMint(address indexed to, uint256 amount, string chain);

    constructor(address admin, address communityManager) ERC20("HoodToken", "HOOD") EIP712("HoodToken", "1") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(COMMUNITY_ROLE, communityManager);
        _grantRole(BRIDGE_ROLE, admin);

        // Mint initial allocations
        _mint(admin, LIQUIDITY_POOL + TEAM_ADVISORS + ECOSYSTEM_FUND); // 50M to admin for allocation
        _mint(address(this), COMMUNITY_REWARD_POOL + AIRDROP_RESERVE); // 50M to contract for rewards
    }

    // --- Community Rewards ---
    function rewardCommunityMember(address to, uint256 amount, string calldata reason) external onlyRole(COMMUNITY_ROLE) {
        require(communityRewardsDistributed + amount <= COMMUNITY_REWARD_POOL, "Reward pool exhausted");
        communityRewardsDistributed += amount;
        _transfer(address(this), to, amount);
        emit CommunityReward(to, amount, reason);
    }

    // --- Airdrop ---
    function claimAirdrop(address to, uint256 amount) external onlyRole(COMMUNITY_ROLE) {
        require(airdropDistributed + amount <= AIRDROP_RESERVE, "Airdrop exhausted");
        airdropDistributed += amount;
        _transfer(address(this), to, amount);
        emit AirdropClaim(to, amount);
    }

    // --- Bridge (for multichain expansion) ---
    function bridgeMint(address to, uint256 amount, string calldata sourceChain) external onlyRole(BRIDGE_ROLE) {
        require(totalSupply() + amount <= MAX_SUPPLY, "Max supply exceeded");
        _mint(to, amount);
        emit BridgeMint(to, amount, sourceChain);
    }

    // --- Overrides for ERC20Votes ---
    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Votes) {
        // Only enforce cap on minting (from == address(0)), not on transfers
        if (from == address(0)) {
            require(totalSupply() + value <= MAX_SUPPLY, "Max supply exceeded");
        }
        super._update(from, to, value);
    }

    // _mint is NOT virtual in OZ 5.x ERC20 — the cap is enforced in _update instead

    // --- Views ---
    function remainingCommunityRewards() external view returns (uint256) {
        return COMMUNITY_REWARD_POOL - communityRewardsDistributed;
    }

    function remainingAirdrop() external view returns (uint256) {
        return AIRDROP_RESERVE - airdropDistributed;
    }
}