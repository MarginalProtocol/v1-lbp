// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.4.0;

/// @title PoolConstants
/// @notice A library for pool internal constants relevant for periphery contracts
library PoolConstants {
    uint256 internal constant MINIMUM_DURATION = 43200; // minimum LBP duration before supplier can manually exit
    uint128 internal constant MINIMUM_LIQUIDITY = 10000; // minimum liquidity on initial mint
}
