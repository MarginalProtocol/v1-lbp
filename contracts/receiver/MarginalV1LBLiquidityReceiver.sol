// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import {INonfungiblePositionManager as IUniswapV3NonfungiblePositionManager} from "@uniswap/v3-periphery/contracts/interfaces/INonfungiblePositionManager.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";
import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {LiquidityAmounts} from "@marginal/v1-periphery/contracts/libraries/LiquidityAmounts.sol";
import {PoolConstants} from "@marginal/v1-periphery/contracts/libraries/PoolConstants.sol";
import {IPoolInitializer as IMarginalV1PoolInitializer} from "@marginal/v1-periphery/contracts/interfaces/IPoolInitializer.sol";
import {IRouter as IMarginalV1Router} from "@marginal/v1-periphery/contracts/interfaces/IRouter.sol";

import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";
import {PeripheryPools} from "../base/PeripheryPools.sol";
import {PeripheryPayments} from "../base/PeripheryPayments.sol";
import {RangeMath} from "../libraries/RangeMath.sol";

import {IMarginalV1LBFactory} from "../interfaces/IMarginalV1LBFactory.sol";
import {IMarginalV1LBPool} from "../interfaces/IMarginalV1LBPool.sol";

import {IMarginalV1LBReceiver} from "../interfaces/receiver/IMarginalV1LBReceiver.sol";
import {IMarginalV1LBLiquidityReceiverDeployer} from "../interfaces/receiver/liquidity/IMarginalV1LBLiquidityReceiverDeployer.sol";
import {IMarginalV1LBLiquidityReceiver} from "../interfaces/receiver/liquidity/IMarginalV1LBLiquidityReceiver.sol";

import {MarginalV1LBReceiver} from "./MarginalV1LBReceiver.sol";

/// @dev Does not support non-standard ERC20 transfer behavior
contract MarginalV1LBLiquidityReceiver is
    IMarginalV1LBLiquidityReceiver,
    MarginalV1LBReceiver,
    PeripheryImmutableState,
    PeripheryPools,
    PeripheryPayments
{
    using SafeERC20 for IERC20;

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    address public immutable deployer;

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    bool public zeroForOne;

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
    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    PoolInfo public uniswapV3PoolInfo;

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    PoolInfo public marginalV1PoolInfo;

    uint256 private unlocked = 1; // uses OZ convention of 1 for false and 2 for true
    modifier lock() {
        if (unlocked == 1) revert Locked();
        unlocked = 1;
        _;
        unlocked = 2;
    }

    event Initialize(uint256 reserve0, uint256 reserve1);
    event RewardsAdded(
        uint256 amount0,
        uint256 amount1,
        uint256 reserve0After,
        uint256 reserve1After
    );
    event MintUniswapV3(
        address uniswapV3Pool,
        uint256 tokenId,
        uint128 liquidity,
        uint256 amount0,
        uint256 amount1,
        uint256 reserve0After,
        uint256 reserve1After
    );
    event MintMarginalV1(
        address marginalV1Pool,
        uint256 shares,
        uint256 amount0,
        uint256 amount1,
        uint256 reserve0After,
        uint256 reserve1After
    );
    event FreeUniswapV3(
        address uniswapV3Pool,
        uint256 tokenId,
        address recipient
    );
    event FreeMarginalV1(
        address marginalV1Pool,
        uint256 shares,
        address recipient
    );

    error Unauthorized();
    error Initialized();
    error Locked();
    error Notified();
    error PoolNotInitialized();
    error PoolNotFinalized();
    error InvalidRatio();
    error InvalidReserves();
    error InvalidPool();
    error InvalidUniswapV3Fee();
    error InvalidMarginalV1Maintenance();
    error Amount0LessThanMin();
    error Amount1LessThanMin();
    error LiquidityAdded();
    error LiquidityNotAdded();
    error DeadlineNotPassed();

    constructor(
        address _factory,
        address _marginalV1Factory,
        address _WETH9,
        address _pool,
        bytes memory data // receiver parameters encoded
    )
        PeripheryImmutableState(_factory, _marginalV1Factory, _WETH9)
        MarginalV1LBReceiver(_pool)
    {
        deployer = msg.sender;
        ReceiverParams memory params = abi.decode(data, (ReceiverParams));
        checkParams(params);
        receiverParams = params;
    }

    /// @notice Checks whether Uniswap v3 and Marginal v1 params are valid
    /// @dev Reverts if params not valid
    function checkParams(ReceiverParams memory params) public {
        if (params.treasuryRatio > 1e6 || params.uniswapV3Ratio > 1e6)
            revert InvalidRatio();
        fullTickRange(params.uniswapV3Fee);
        maximumLeverage(params.marginalV1Maintenance);
    }

    /// @inheritdoc IMarginalV1LBReceiver
    function seeds(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceLowerX96,
        uint160 sqrtPriceUpperX96
    )
        public
        view
        virtual
        override(MarginalV1LBReceiver, IMarginalV1LBReceiver)
        returns (uint256 amount0, uint256 amount1)
    {
        bool _zeroForOne = (sqrtPriceX96 == sqrtPriceLowerX96);
        uint160 sqrtPriceFinalizeX96 = _zeroForOne
            ? sqrtPriceUpperX96
            : sqrtPriceLowerX96;

        (uint256 amount0Pool, uint256 amount1Pool) = RangeMath.toAmounts(
            liquidity,
            sqrtPriceFinalizeX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );
        (uint256 amount0Desired, uint256 amount1Desired) = getAmountsDesired(
            sqrtPriceFinalizeX96,
            amount0Pool,
            amount1Pool,
            _zeroForOne
        );
        // @dev extra tokens to add to reserves of receiver is in the offered token as
        // notifyRewardAmounts provides acquired token side of full range liquidity mint
        amount0 = _zeroForOne ? amount0Desired : 0;
        amount1 = _zeroForOne ? 0 : amount1Desired;
    }

    /// @inheritdoc IMarginalV1LBReceiver
    function initialize()
        external
        virtual
        override(MarginalV1LBReceiver, IMarginalV1LBReceiver)
    {
        (uint160 sqrtPriceInitializeX96, uint160 sqrtPriceFinalizeX96) = (
            IMarginalV1LBPool(pool).sqrtPriceInitializeX96(),
            IMarginalV1LBPool(pool).sqrtPriceFinalizeX96()
        );
        if (sqrtPriceInitializeX96 == 0) revert PoolNotInitialized();

        (uint160 sqrtPriceLowerX96, uint160 sqrtPriceUpperX96) = (
            sqrtPriceInitializeX96 < sqrtPriceFinalizeX96
                ? (sqrtPriceInitializeX96, sqrtPriceFinalizeX96)
                : (sqrtPriceFinalizeX96, sqrtPriceInitializeX96)
        );
        bool _zeroForOne = (sqrtPriceInitializeX96 == sqrtPriceLowerX96);
        zeroForOne = _zeroForOne;

        (uint256 _reserve0, uint256 _reserve1) = (reserve0, reserve1);
        if (_reserve0 > 0 || _reserve1 > 0) revert Initialized();

        // calculate amount{0,1}Owed for reserves in case where need most tokens of hitting finalize price
        (, , uint128 liquidity, , , , , ) = IMarginalV1LBPool(pool).state();
        (uint256 amount0, uint256 amount1) = seeds(
            liquidity,
            sqrtPriceInitializeX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );

        if (_reserve0 + amount0 > balance(token0)) revert Amount0LessThanMin();
        if (_reserve1 + amount1 > balance(token1)) revert Amount1LessThanMin();
        _reserve0 += amount0;
        _reserve1 += amount1;

        reserve0 = _reserve0;
        reserve1 = _reserve1;
        unlocked = 2;

        emit Initialize(_reserve0, _reserve1);
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
        uint256 lev = IMarginalV1Factory(marginalV1Factory).getLeverage(
            maintenance
        );
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
        if (blockTimestamp == 0 || delta < duration) revert DeadlineNotPassed();
    }

    /// @inheritdoc IMarginalV1LBReceiver
    function notifyRewardAmounts(
        uint256 amount0,
        uint256 amount1
    )
        external
        virtual
        override(MarginalV1LBReceiver, IMarginalV1LBReceiver)
        lock
    {
        address supplier = IMarginalV1LBPool(pool).supplier();
        if (msg.sender != supplier) revert Unauthorized();

        (, , , , , , , bool finalized) = IMarginalV1LBPool(pool).state();
        if (!finalized) revert PoolNotFinalized();

        // only support tokens with standard ERC20 transfer
        (uint256 _reserve0, uint256 _reserve1) = (reserve0, reserve1);
        if (_reserve0 + amount0 > balance(token0)) revert Amount0LessThanMin();
        if (_reserve1 + amount1 > balance(token1)) revert Amount1LessThanMin();

        // pay treasury given ratio
        ReceiverParams memory params = receiverParams;
        uint256 amount0Treasury = (amount0 * params.treasuryRatio) / 1e6;
        uint256 amount1Treasury = (amount1 * params.treasuryRatio) / 1e6;

        _reserve0 += amount0 - amount0Treasury;
        _reserve1 += amount1 - amount1Treasury;

        // update reserves
        reserve0 = _reserve0;
        reserve1 = _reserve1;

        if (amount0Treasury > 0)
            pay(token0, address(this), params.treasuryAddress, amount0Treasury);
        if (amount1Treasury > 0)
            pay(token1, address(this), params.treasuryAddress, amount1Treasury);

        emit RewardsAdded(amount0, amount1, _reserve0, _reserve1);
    }

    /// @notice Returns the amounts desired to mint full range liquidity given reserves from lbp
    /// @dev Uses liquidity value calculated from reserve amount in token acquired
    /// @param sqrtPriceX96 The price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @param amount0 The amount of token0 to use from reserve
    /// @param amount1 The amount of token1 to use from reserve
    /// @param _zeroForOne Whether lbp offered up token0 for token1
    /// @return amount0Desired The maximum amount of token0 needed to mint full range liquidity
    /// @return amount1Desired The maximum amount of token1 needed to mint full range liquidity
    function getAmountsDesired(
        uint160 sqrtPriceX96,
        uint256 amount0,
        uint256 amount1,
        bool _zeroForOne
    ) public pure returns (uint256 amount0Desired, uint256 amount1Desired) {
        // calculate additional amount{0,1} needed to provide full range liquidity
        (uint128 liquidity0, uint128 liquidity1) = (
            LiquidityAmounts.getLiquidityForAmount0(sqrtPriceX96, amount0),
            LiquidityAmounts.getLiquidityForAmount1(sqrtPriceX96, amount1)
        );
        uint128 liquidity = _zeroForOne ? liquidity1 : liquidity0; // liquidity determined by lbp acquired token
        (amount0Desired, amount1Desired) = LiquidityMath.toAmounts(
            liquidity,
            sqrtPriceX96
        );
    }

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    function mintUniswapV3()
        external
        lock
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

        if (uniswapV3PoolInfo.blockTimestamp > 0) revert LiquidityAdded();
        uniswapV3PoolInfo.blockTimestamp = _blockTimestamp(); // store here first to avoid re-entrancy issues

        // get Uniswap v3 NFT position manager from deployer
        address uniswapV3NonfungiblePositionManager = IMarginalV1LBLiquidityReceiverDeployer(
                deployer
            ).uniswapV3NonfungiblePositionManager();

        // create uniswap v3 pool if necessary
        (uint160 sqrtPriceX96, , , , , , , ) = IMarginalV1LBPool(pool).state();
        uniswapV3Pool = IUniswapV3NonfungiblePositionManager(
            uniswapV3NonfungiblePositionManager
        ).createAndInitializePoolIfNecessary(
                token0,
                token1,
                params.uniswapV3Fee,
                sqrtPriceX96
            );

        uint256 amount0UniswapV3 = (_reserve0 * params.uniswapV3Ratio) / 1e6;
        uint256 amount1UniswapV3 = (_reserve1 * params.uniswapV3Ratio) / 1e6;

        _reserve0 -= amount0UniswapV3;
        _reserve1 -= amount1UniswapV3;

        // update reserves
        reserve0 = _reserve0;
        reserve1 = _reserve1;

        // @dev lbp price used for amounts desired, capped by token acquired from lbp
        // initialize should transfer in worst case excess of amounts{0,1}Desired vs reserves{0,1} prior to minting
        (uint256 amount0Desired, uint256 amount1Desired) = getAmountsDesired(
            sqrtPriceX96,
            amount0UniswapV3,
            amount1UniswapV3,
            zeroForOne
        );

        // calculate tick upper/lower ticks for full tick range given uniswap v3 fee tier
        // @dev finite full tick range implies *less* physical reserves required to mint than calculated at initialize
        // TODO: check finite full tick range math
        (int24 tickLower, int24 tickUpper) = fullTickRange(params.uniswapV3Fee);

        // add liquidity based on lbp price to avoid slippage issues
        IERC20(token0).safeIncreaseAllowance(
            uniswapV3NonfungiblePositionManager,
            amount0UniswapV3
        );
        IERC20(token1).safeIncreaseAllowance(
            uniswapV3NonfungiblePositionManager,
            amount1UniswapV3
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

        emit MintUniswapV3(
            uniswapV3Pool,
            tokenId,
            liquidity,
            amount0,
            amount1,
            _reserve0,
            _reserve1
        );
    }

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    function mintMarginalV1()
        external
        lock
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

        if (marginalV1PoolInfo.blockTimestamp > 0) revert LiquidityAdded();
        marginalV1PoolInfo.blockTimestamp = _blockTimestamp(); // store here first to avoid re-entrancy issues

        // set reserves to zero
        reserve0 = 0;
        reserve1 = 0;

        marginalV1Pool = getMarginalV1Pool(
            token0,
            token1,
            params.marginalV1Maintenance,
            uniswapV3Pool
        );

        bool initialize = (marginalV1Pool == address(0));
        if (!initialize) {
            (, , , , , , , bool initialized) = IMarginalV1Pool(marginalV1Pool)
                .state();
            initialize = !initialized;
        }

        // @dev lbp price used for amounts desired, capped by token acquired from lbp
        (uint160 sqrtPriceX96, , , , , , , ) = IMarginalV1LBPool(pool).state();
        // initialize should transfer in worst case excess of amounts{0,1}Desired vs reserves{0,1} prior to minting
        (uint256 amount0Desired, uint256 amount1Desired) = getAmountsDesired(
            sqrtPriceX96,
            _reserve0,
            _reserve1,
            zeroForOne
        );

        if (initialize) {
            address marginalV1PoolInitializer = IMarginalV1LBLiquidityReceiverDeployer(
                    deployer
                ).marginalV1PoolInitializer();

            // use initializer to create pool and add liquidity
            IERC20(token0).safeIncreaseAllowance(
                marginalV1PoolInitializer,
                _reserve0
            );
            IERC20(token1).safeIncreaseAllowance(
                marginalV1PoolInitializer,
                _reserve1
            );

            // initialize to uniswap v3 sqrt price
            // @dev use uniswap v3 sqrt price to adjust desired amounts for burn via liquidity calculations
            (sqrtPriceX96, , , , , , ) = IUniswapV3Pool(uniswapV3Pool).slot0();

            // TODO: fix logic for liquidity burned? use quoter?
            // liquidity (roughly) contributed to marginal v1 pool ignoring burn
            uint128 liquidityDesired = LiquidityAmounts.getLiquidityForAmounts(
                sqrtPriceX96,
                amount0Desired,
                amount1Desired
            );
            uint128 liquidityBurned = PoolConstants.MINIMUM_LIQUIDITY ** 2; // TODO: validation around minimum liquidity?
            // factor of 2 for extra significant buffer given swap increases liquidity due to fee
            liquidityDesired -= 2 * liquidityBurned;
            // back to amounts{0,1} with uniswap v3 sqrt price so near exact contribution (< original desired)
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
                        uniswapV3Fee: params.uniswapV3Fee,
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

            // if rare edge case of < 0 case, have extra dust left over in contract
            amount0 = _amount0 > 0 ? uint256(_amount0) : 0;
            amount1 = _amount1 > 0 ? uint256(_amount1) : 0;
        } else {
            address marginalV1Router = IMarginalV1LBLiquidityReceiverDeployer(
                deployer
            ).marginalV1Router();

            // use router to add liquidity
            IERC20(token0).safeIncreaseAllowance(marginalV1Router, _reserve0);
            IERC20(token1).safeIncreaseAllowance(marginalV1Router, _reserve1);

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

            marginalV1Pool = getMarginalV1Pool(
                token0,
                token1,
                params.marginalV1Maintenance,
                uniswapV3Pool
            );
        }

        // refund any left over unused amounts from uniswap v3 and marginal v1 mints
        uint256 balance0 = balance(token0);
        uint256 balance1 = balance(token1);
        if (balance0 > 0)
            pay(token0, address(this), params.treasuryAddress, balance0);
        if (balance1 > 0)
            pay(token1, address(this), params.treasuryAddress, balance1);

        marginalV1PoolInfo = PoolInfo({
            blockTimestamp: _blockTimestamp(),
            poolAddress: marginalV1Pool,
            tokenId: 0, // fungible
            shares: shares
        });

        emit MintMarginalV1(marginalV1Pool, shares, amount0, amount1, 0, 0);
    }

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    function freeUniswapV3(address recipient) external lock {
        PoolInfo memory info = uniswapV3PoolInfo;
        if (info.poolAddress == address(0)) revert LiquidityNotAdded();

        ReceiverParams memory params = receiverParams;
        if (msg.sender != params.lockOwner) revert Unauthorized();
        checkDeadline(info.blockTimestamp, params.lockDuration);

        // set tokenId and block timestamp to zero so can't free again
        uint256 tokenId = info.tokenId;
        info.tokenId = 0;
        info.blockTimestamp = 0;
        uniswapV3PoolInfo = info;

        // get Uniswap v3 NFT position manager from deployer
        address uniswapV3NonfungiblePositionManager = IMarginalV1LBLiquidityReceiverDeployer(
                deployer
            ).uniswapV3NonfungiblePositionManager();

        // @dev not safeTransferFrom so no ERC721 received needed on recipient
        IUniswapV3NonfungiblePositionManager(
            uniswapV3NonfungiblePositionManager
        ).transferFrom(address(this), recipient, tokenId);

        emit FreeUniswapV3(info.poolAddress, tokenId, recipient);
    }

    /// @inheritdoc IMarginalV1LBLiquidityReceiver
    function freeMarginalV1(address recipient) external lock {
        PoolInfo memory info = marginalV1PoolInfo;
        if (info.poolAddress == address(0)) revert LiquidityNotAdded();

        ReceiverParams memory params = receiverParams;
        if (msg.sender != params.lockOwner) revert Unauthorized();
        checkDeadline(info.blockTimestamp, params.lockDuration);

        // set shares and block timestamp to zero so can't free again
        uint256 shares = info.shares;
        info.shares = 0;
        info.blockTimestamp = 0;
        marginalV1PoolInfo = info;

        pay(info.poolAddress, address(this), recipient, shares);

        emit FreeMarginalV1(info.poolAddress, shares, recipient);
    }
}
