// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

/// @title Immutable state
/// @notice Functions that return immutable state of periphery for Marginal v1 liquidity bootstrapping pool
interface IPeripheryImmutableState {
    /// @return Returns the address of the Marginal V1 liquidity bootstrapping factory
    function factory() external view returns (address);

    /// @return Returns the address of the Marginal V1 factory
    function marginalV1Factory() external view returns (address);

    /// @return Returns the address of the Uniswap V3 factory
    function uniswapV3Factory() external view returns (address);

    /// @return Returns the address of WETH9
    function WETH9() external view returns (address);
}
