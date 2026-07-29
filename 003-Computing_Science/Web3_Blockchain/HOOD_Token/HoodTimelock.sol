// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title HoodTimelock
 * @notice 2-day timelock for governance proposals — prevents rash decisions
 */

import "@openzeppelin/contracts/governance/TimelockController.sol";

contract HoodTimelock is TimelockController {
    constructor(address admin) TimelockController(172800, // 2 days
        new address[](0), // proposers — added later via governance
        new address[](0), // executors — anyone can execute once proposed
        admin
    ) {}
}