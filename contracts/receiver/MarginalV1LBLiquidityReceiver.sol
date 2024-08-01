// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import {INonfungiblePositionManager as IUniswapV3NonfungiblePositionManager} from "@uniswap/v3-core/contracts/interfaces/INonfungiblePositionManager.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";
import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

import {LiquidityAmounts} from "@marginal/v1-periphery/contracts/libraries/LiquidityAmounts.sol";
import {PoolConstants} from "@marginal/v1-periphery/contracts/libraries/PoolConstants.sol";
import {IPoolInitializer as IMarginalV1PoolInitializer} from "@marginal/v1-periphery/contracts/interfaces/IPoolInitializer.sol";
import {IRouter as IMarginalV1Router} from "@marginal/v1-periphery/contracts/interfaces/IRouter.sol";

import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";
import {PeripheryPools} from "../base/PeripheryPools.sol";
import {PeripheryPayments} from "../base/PeripheryPayments.sol";

import {IMarginalV1LBFinalizeCallback} from "../interfaces/handler/IMarginalV1LBFinalizeCallback.sol";
import {IMarginalV1LBFactory} from "../interfaces/IMarginalV1LBFactory.sol";
import {IMarginalV1LBPool} from "../interfaces/IMarginalV1LBPool.sol";

import {IMarginalV1LBLiquidityReceiverDeployer} from "../interfaces/IMarginalV1LBLiquidityReceiverDeployer.sol";
import {IMarginalV1LBLiquidityReceiver} from "../interfaces/IMarginalV1LBLiquidityReceiver.sol";

/// @dev Does not support non-standard ERC20 transfer behavior
contract MarginalV1LBLiquidityReceiver is
    IMarginalV1LBLiquidityReceiver,
    IMarginalV1LBReceiver,
    PeripheryImmutableState,
    PeripheryPools,
    PeripheryPayments,
    Multicall
{
    using SafeERC20 for IERC20;

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    address public immutable deployer;

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    address public immutable pool;

    /// @dev Address of token0 fetched from pool
    address internal immutable token0;

    /// @dev Address of token1 fetched from pool
    address internal immutable token1;

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    uint256 public reserve0;

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    uint256 public reserve1;

    struct ReceiverParams {
        /// address of the treasury to send treasury ratio funds
        address treasuryAddress;
        /// fraction of lbp funds to send to treasury in units of hundredths of 1 bip
        uint24 treasuryRatio;
        /// fraction of lbp funds less supplier to add to Uniswap v3 pool in units of hundredths of 1 bip
        uint24 uniswapV3Ratio;
        /// fee tier of Uniswap v3 pool to add liquidity to
        uint24 uniswapV3Fee;
        /// minimum maintenance requirement of Marginal v1 pool to add liquidity to
        uint24 marginalV1Maintenance;
        /// address that can unlock liquidity after lock passes from this contract
        address lockOwner;
        /// seconds after which can unlock liquidity receipt tokens from this contract
        uint96 lockDuration;
    }
    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    ReceiverParams public receiverParams;

    struct PoolInfo {
        /// block timestamp at which added liquidity to pool
        uint96 blockTimestamp;
        /// address of Uniswap v3 or Marginal v1 pool added liquidity to
        address poolAddress;
        /// tokenId (if any) of pool added liquidity for nonfungible liquidity
        uint256 tokenId;
        /// shares (if any) of pool added liquidity for fungible liquidity
        uint256 shares;
    }
    /// @inheritdoc IMarginalV1LBLiquidityRecipient
    PoolInfo public uniswapV3PoolInfo;

    /// @inheritdoc IMarginalV1LBLiquidityRecipient
    PoolInfo public marginalV1PoolInfo;

    error Unauthorized();
    error Locked();
    error Notified();
    error NotFinalized();
    error InvalidRatio();
    error InvalidReserves();
    error InvalidPool();
    error InvalidUniswapV3Fee();
    error InvalidMarginalV1Maintenance();
    error LiquidityAdded();
    error LiquidityNotAdded();

    constructor(address _pool, bytes calldata data) {
        deployer = msg.sender;
        pool = _pool;
        token0 = IMarginalV1LBPool(_pool).token0();
        token1 = IMarginalV1LBPool(_pool).token1();

        ReceiverParams memory params = abi.decode(data, (ReceiverParams));
        checkParams(params);
        receiverParams = params;
    }

    // TODO: receive just in case?
    // receive() external payable virtual override {}

    /// @notice Checks whether Uniswap v3 and Marginal v1 params are valid
    /// @dev Reverts if params not valid
    function checkParams(ReceiverParams memory params) public {
        if (params.treasuryRatio > 1e6 || params.uniswapRatio > 1e6)
            revert InvalidRatio();
        fullTickRange(params.uniswapV3Fee);
        maximumLeverage(params.marginalV1Maintenance);
    }

    /// @notice Returns the full tick range for Uniswap v3 pool with given fee tier
    /// @param fee The fee tier of the Uniswap v3 pool
    /// @return tickLower The lower tick of the full range
    /// @return tickUpper The upper tick of the full range
    function fullTickRange(
        uint24 fee
    ) private view returns (int24 tickLower, int24 tickUpper) {
        int24 tickSpacing = IUniswapV3Factory(uniswapV3Factory)
            .feeAmountTickSpacing(fee);
        if (tickSpacing == 0) revert InvalidUniswapV3Fee();
        tickUpper = TickMath.MAX_TICK - (TickMath.MAX_TICK % tickSpacing);
        tickLower = -tickUpper;
    }

    /// @notice Returns the maximum leverage of the Marginal v1 pool for given maintenance requirement
    /// @param maintenance The minimum maintenance requirement of the Marginal v1 pool
    /// @return The maximum leverage for the maintenance requirement
    function maximumLeverage(
        uint24 maintenance
    ) private view returns (uint256) {
        uint256 lev = IMarginalV1Factory(marginalV1Factory).getLeverage();
        if (lev == 0) revert InvalidMarginalV1Maintenance();
        return lev;
    }

    /// @notice Returns the current block timestamp cast to uint96
    /// @dev Unsafe cast to uint96 intended for wrap around
    /// @return The current block timestamp cast to uint96
    function _blockTimestamp() internal view returns (uint96) {
        return uint96(block.timestamp);
    }

    /// @notice Checks for locked liquidity whether deadline to unlock has passed
    /// @dev Reverts if current timestamp is less than start timestamp + duration
    function checkDeadline(
        uint96 blockTimestamp,
        uint96 duration
    ) internal view {
        uint96 delta;
        unchecked {
            delta = _blockTimestamp() - blockTimestamp;
        }
        if (blockTimestamp == 0 || delta < duration) revert Locked();
    }

    /// @inheritdoc IMarginalV1LBReceiver
    function notifyRewardAmounts(uint256 amount0, uint256 amount1) external {
        address supplier = IMarginalV1LBPool(pool).supplier();
        if (msg.sender != supplier) revert Unauthorized();

        (uint160 sqrtPriceX96, , , , , , , bool finalized) = IMarginalV1LBPool(
            pool
        ).state();
        if (!finalized) revert NotFinalized();

        // only support tokens with standard ERC20 transfer
        if (reserve0 > 0 || reserve1 > 0) revert Notified();
        if (reserve0 + amount0 > balance(token0)) revert Amount0LessThanMin();
        if (reserve1 + amount1 > balance(token1)) revert Amount1LessThanMin();

        // pay treasury given ratio
        ReceiverParams memory params = receiverParams;
        uint256 amount0Treasury = (amount0 * params.treasuryRatio) / 1e6;
        uint256 amount1Treasury = (amount1 * params.treasuryRatio) / 1e6;
        amount0 -= amount0Treasury;
        amount1 -= amount1Treasury;

        // set reserves
        reserve0 = amount0;
        reserve1 = amount1;

        if (amount0Treasury > 0)
            pay(
                poolKey.token0,
                address(this),
                params.treasuryAddress,
                amount0Treasury
            );
        if (amount1Treasury > 0)
            pay(
                poolKey.token1,
                address(this),
                params.treasuryAddress,
                amount1Treasury
            );
    }

    /// @notice Returns the amounts desired for amounts{0,1} from reserves
    /// @param sqrtPriceX96 The price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @param amount0 The amount of token0 to use from reserve
    /// @param amount1 The amount of token1 to use from reserve
    function getAmountsDesired(
        uint160 sqrtPriceX96,
        uint256 amount0,
        uint256 amount1
    ) public pure returns (uint256 amount0Desired, uint256 amount1Desired) {
        // calculate additional amount{0,1} needed to provide full range liquidity
        // @dev want the *max* of these two in liquidity values
        (uint128 liquidity0, uint128 liquidity1) = (
            LiquidityAmounts.getLiquidityForAmount0(sqrtPriceX96, amount0),
            LiquidityAmounts.getLiquidityForAmount1(sqrtPriceX96, amount1)
        );
        uint128 liquidity = liquidity0 < liquidity1 ? liquidity1 : liquidity0; // max of two for amounts desired
        (amount0Desired, amount1Desired) = LiquidityMath.toAmounts(
            liquidity,
            sqrtPriceX96
        );
    }

    /// @inheritdoc IMarginalV1LBLiquidityRecipient
    function mintUniswapV3()
        external
        payable
        returns (
            address uniswapV3Pool,
            uint256 tokenId,
            uint128 liquidity,
            uint256 amount0,
            uint256 amount1
        )
    {
        ReceiverParams memory params = receiverParams;

        (uint256 _reserve0, uint256 _reserve1) = (reserve0, reserve1);
        if (_reserve0 == 0 && _reserve1 == 0) revert InvalidReserves();

        if (uniswapV3PoolInfo.poolAddress != address(0))
            revert LiquidityAdded();

        // get Uniswap v3 NFT position manager from deployer
        address uniswapV3NonfungiblePositionManager = IMarginalV1LBLiquidityReceiverDeployer(
                deployer
            ).uniswapV3NonfungiblePositionManager();

        // create uniswap v3 pool if necessary
        (uint160 sqrtPriceX96, , , , , , , bool finalized) = IMarginalV1LBPool(
            pool
        ).state();
        uniswapV3Pool = IUniswapV3NonfungiblePositionManager(
            uniswapV3NonfungiblePositionManager
        ).createAndInitializePoolIfNecessary(
                token0,
                token1,
                params.uniswapV3Fee,
                sqrtPriceX96
            );

        // reset sqrt price to Uniswap v3 pool
        (sqrtPriceX96, , , , , , ) = IUniswapV3Pool(uniswapV3Pool);

        uint256 amount0UniswapV3 = (_reserve0 * params.uniswapV3Ratio) / 1e6;
        uint256 amount1UniswapV3 = (_reserve1 * params.uniswapV3Ratio) / 1e6;

        // update reserves
        reserve0 -= amount0UniswapV3;
        reserve1 -= amount1UniswapV3;

        // transfer in diff from sender between reserves dedicated to Uniswap v3 and amounts for mint
        (uint256 amount0Desired, uint256 amount1Desired) = getAmountsDesired(
            sqrtPriceX96,
            amount0UniswapV3,
            amount1UniswapV3
        );
        if (amount0Desired > amount0UniswapV3)
            pay(
                token0,
                msg.sender,
                address(this),
                amount0Desired - amount0UniswapV3
            );
        if (amount1Desired > amount1UniswapV3)
            pay(
                token1,
                msg.sender,
                address(this),
                amount1Desired - amount1UniswapV3
            );

        // calculate tick upper/lower ticks for full tick range given uniswap v3 fee tier
        (int24 tickLower, int24 tickUpper) = fullTickRange(params.uniswapV3Fee);

        // add liquidity based on lbp price to avoid slippage issues
        // @dev should be ok if amounts changed from unexpected token transfers in between handler calls
        IERC20(token0).safeIncreaseAllowance(
            uniswapV3NonfungiblePositionManager,
            amount0Desired
        );
        IERC20(token1).safeIncreaseAllowance(
            uniswapV3NonfungiblePositionManager,
            amount1Desired
        );

        (
            tokenId,
            liquidity,
            amount0,
            amount1
        ) = IUniswapV3NonfungiblePositionManager(
            uniswapV3NonfungiblePositionManager
        ).mint(
                IUniswapV3NonfungiblePositionManager.MintParams({
                    token0: token0,
                    token1: token1,
                    fee: params.uniswapV3Fee,
                    tickLower: tickLower,
                    tickUpper: tickUpper,
                    amount0Desired: amount0Desired,
                    amount1Desired: amount1Desired,
                    amount0Min: 0,
                    amount1Min: 0, // TODO: issue for slippage?
                    recipient: address(this),
                    deadline: block.timestamp
                })
            );

        uniswapV3PoolInfo = PoolInfo({
            blockTimestamp: _blockTimestamp(),
            poolAddress: uniswapV3Pool,
            tokenId: tokenId,
            shares: 0 // nonfungible
        });
    }

    /// @inheritdoc IMarginalV1LBLiquidityRecipient
    function mintMarginalV1()
        external
        payable
        returns (
            address marginalV1Pool,
            uint256 shares,
            uint256 amount0,
            uint256 amount1
        )
    {
        /// @dev Before calling, must first initialize Uniswap v3 pool oracle above Marginal v1 factory cardinality minimum
        ReceiverParams memory params = receiverParams;

        (uint256 _reserve0, uint256 _reserve1) = (reserve0, reserve1);
        if (_reserve0 == 0 && _reserve1 == 0) revert InvalidReserves();

        address uniswapV3Pool = uniswapV3PoolInfo.poolAddress;
        if (uniswapV3Pool == address(0)) revert LiquidityNotAdded();
        if (marginalV1PoolInfo.poolAddress != address(0))
            revert LiquidityAdded();

        // set reserves to zero
        reserve0 = 0;
        reserve1 = 0;

        address marginalV1Factory = IMarginalV1LBLiquidityReceiverDeployer(
            deployer
        ).marginalV1Factory();
        marginalV1Pool = IMarginalV1Factory(marginalV1Factory).getPool(
            token0,
            token1,
            params.marginalV1Maintenance,
            uniswapV3Pool
        );

        uint160 sqrtPriceX96;
        bool initialize = (marginalV1Pool == address(0));
        if (!initialize) {
            (sqrtPriceX96, , , , , , , ) = IMarginalV1Pool(pool).state();
            if (sqrtPriceX96 == 0) {
                initialize = true;
                // use uniswap v3 sqrt price instead
                (sqrtPriceX96, , , , , , ) = IUniswapV3Pool(uniswapV3Pool)
                    .slot0();
            }
        }

        // transfer in diff from sender between reserves dedicated to Marginal v1 and amounts for mint
        (uint256 amount0Desired, uint256 amount1Desired) = getAmountsDesired(
            sqrtPriceX96,
            _reserve0,
            _reserve1
        );
        if (amount0Desired > _reserve0)
            pay(token0, msg.sender, address(this), amount0Desired - _reserve0);
        if (amount1Desired > _reserve1)
            pay(token1, msg.sender, address(this), amount1Desired - _reserve1);

        if (initialize) {
            address marginalV1PoolInitializer = IMarginalV1LBLiquidityReceiverDeployer(
                    deployer
                ).marginalV1PoolInitializer();

            // use initializer to create pool and add liquidity
            IERC20(token0).safeIncreaseAllowance(
                marginalV1PoolInitializer,
                amount0Desired
            );
            IERC20(token1).safeIncreaseAllowance(
                marginalV1PoolInitializer,
                amount1Desired
            );

            // calculate (roughly) amounts{0,1} desired accounting for liquidity burn plus swap
            uint128 liquidityDesired = LiquidityAmounts.getLiquidityForAmounts(
                sqrtPriceX96,
                amount0Desired,
                amount1Desired
            );
            uint128 liquidityBurned = PoolConstants.MINIMUM_LIQUIDITY ** 2; // TODO: validation around minimum liquidity?
            // factor of 2 for extra significant buffer given swap increases liquidity due to fee
            liquidityDesired -= 2 * liquidityBurned;
            (amount0Desired, amount1Desired) = LiquidityMath.toAmounts(
                liquidityDesired,
                sqrtPriceX96
            );

            int256 _amount0;
            int256 _amount1;
            (
                marginalV1Pool,
                shares,
                _amount0,
                _amount1
            ) = IMarginalV1PoolInitializer(marginalV1PoolInitializer)
                .createAndInitializePoolIfNecessary(
                    IMarginalV1PoolInitializer.CreateAndInitializeParams({
                        token0: token0,
                        token1: token1,
                        maintenance: params.marginalV1Maintenance,
                        oracle: uniswapV3Pool,
                        recipient: address(this),
                        sqrtPriceX96: sqrtPriceX96,
                        sqrtPriceLimitX96: 0,
                        liquidityBurned: liquidityBurned,
                        amount0BurnedMax: type(int256).max,
                        amount1BurnedMax: type(int256).max,
                        amount0Desired: amount0Desired,
                        amount1Desired: amount1Desired,
                        amount0Min: 0,
                        amount1Min: 0, // TODO: issue for slippage?
                        deadline: block.timestamp
                    })
                );

            // if rare edge case of < 0 case, have dust left over in contract
            amount0 = _amount0 > 0 ? uint256(_amount0) : 0;
            amount1 = _amount1 > 0 ? uint256(_amount1) : 0;
        } else {
            address marginalV1Router = IMarginalV1LBLiquidityReceiverDeployer(
                deployer
            ).marginalV1Router();

            // use router to add liquidity
            IERC20(token0).safeIncreaseAllowance(
                marginalV1Router,
                amount0Desired
            );
            IERC20(token1).safeIncreaseAllowance(
                marginalV1Router,
                amount1Desired
            );

            (shares, amount0, amount1) = IMarginalV1Router(marginalV1Router)
                .addLiquidity(
                    IMarginalV1Router.AddLiquidityParams({
                        token0: token0,
                        token1: token1,
                        maintenance: params.marginalV1Maintenance,
                        oracle: uniswapV3Pool,
                        recipient: address(this),
                        amount0Desired: amount0Desired,
                        amount1Desired: amount1Desired,
                        amount0Min: 0,
                        amount1Min: 0, // TODO: issue for slippage?
                        deadline: block.timestamp
                    })
                );

            marginalV1Pool = IMarginalV1Factory(marginalV1Factory).getPool(
                token0,
                token1,
                params.marginalV1Maintenance,
                uniswapV3Pool
            );
        }

        marginalV1PoolInfo = PoolInfo({
            blockTimestamp: _blockTimestamp(),
            poolAddress: marginalV1Pool,
            tokenId: 0, // fungible
            shares: shares
        });
    }

    /// @inheritdoc IMarginalV1LBLiquidityRecipient
    function freeUniswapV3(address recipient) external {
        PoolInfo memory info = uniswapV3PoolInfo;
        if (info.poolAddress == address(0)) revert LiquidityNotAdded();

        ReceiverParams memory params = receiverParams;
        if (msg.sender != params.lockOwner) revert Unauthorized();
        checkDeadline(info.blockTimestamp, params.lockDuration);

        // set tokenId and block timestamp to zero so can't free again
        info.tokenId = 0;
        info.blockTimestamp = 0;
        uniswapV3PoolInfo = info;

        // @dev not safeTransferFrom so no ERC721 received needed on recipient
        IUniswapV3NonfungiblePositionManager(
            uniswapV3NonfungiblePositionManager
        ).transferFrom(address(this), recipient, info.tokenId);
    }

    /// @inheritdoc IMarginalV1LBLiquidityRecipient
    function freeMarginalV1(address recipient) external {
        PoolInfo memory info = marginalV1PoolInfo;
        if (info.poolAddress == address(0)) revert LiquidityNotAdded();

        ReceiverParams memory params = receiverParams;
        if (msg.sender != params.lockOwner) revert Unauthorized();
        checkDeadline(info.blockTimestamp, params.lockDuration);

        // set shares and block timestamp to zero so can't free again
        info.shares = 0;
        info.blockTimestamp = 0;
        marginalV1PoolInfo = info;

        pay(info.poolAddress, address(this), recipient, info.shares);
    }
}
