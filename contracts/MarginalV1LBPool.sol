// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";
import {TransferHelper} from "@marginal/v1-core/contracts/libraries/TransferHelper.sol";

import {IMarginalV1MintCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1SwapCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1SwapCallback.sol";

import {RangeMath} from "./libraries/RangeMath.sol";

import {IMarginalV1LBFinalizeCallback} from "./interfaces/callback/IMarginalV1LBFinalizeCallback.sol";
import {IMarginalV1LBFactory} from "./interfaces/IMarginalV1LBFactory.sol";
import {IMarginalV1LBPool} from "./interfaces/IMarginalV1LBPool.sol";

contract MarginalV1LBPool is IMarginalV1LBPool {
    /// @inheritdoc IMarginalV1LBPool
    address public immutable factory;
    /// @inheritdoc IMarginalV1LBPool
    address public immutable token0;
    /// @inheritdoc IMarginalV1LBPool
    address public immutable token1;
    /// @inheritdoc IMarginalV1LBPool
    int24 public immutable tickLower;
    /// @inheritdoc IMarginalV1LBPool
    int24 public immutable tickUpper;
    /// @inheritdoc IMarginalV1LBPool
    uint160 public immutable sqrtPriceLowerX96;
    /// @inheritdoc IMarginalV1LBPool
    uint160 public immutable sqrtPriceUpperX96;
    /// @inheritdoc IMarginalV1LBPool
    address public immutable supplier;
    /// @inheritdoc IMarginalV1LBPool
    uint256 public immutable blockTimestampInitialize;

    // minimum LBP duration before supplier can manually exit (12 hr)
    uint256 internal constant MINIMUM_DURATION = 43200;
    /// liquidity locked on initial mint always available for swaps
    uint128 internal constant MINIMUM_LIQUIDITY = 10000;

    /// @inheritdoc IMarginalV1LBPool
    uint160 public sqrtPriceInitializeX96;
    /// @inheritdoc IMarginalV1LBPool
    uint160 public sqrtPriceFinalizeX96;

    struct State {
        uint160 sqrtPriceX96;
        uint96 totalPositions; // > ~ 2e20 years at max per block to fill on mainnet
        uint128 liquidity;
        int24 tick;
        uint32 blockTimestamp;
        int56 tickCumulative;
        uint8 feeProtocol;
        bool finalized;
    }
    /// @inheritdoc IMarginalV1Pool
    State public state;

    uint256 private unlocked = 1; // uses OZ convention of 1 for false and 2 for true
    modifier lock() {
        if (unlocked == 1) revert Locked();
        unlocked = 1;
        _;
        unlocked = 2;
    }

    event Initialize(uint128 liquidity, uint160 sqrtPriceX96, int24 tick);
    event Finalize(
        uint128 liquidityDelta,
        uint160 sqrtPriceX96,
        uint256 amount0,
        uint256 amount1
    );
    event Swap(
        address indexed sender,
        address indexed recipient,
        int256 amount0,
        int256 amount1,
        uint160 sqrtPriceX96,
        uint128 liquidity,
        int24 tick
    );
    event Mint(
        address sender,
        address indexed owner,
        uint128 liquidityDelta,
        uint256 amount0,
        uint256 amount1
    );
    event Burn(
        address indexed sender,
        address recipient,
        uint128 liquidityDelta,
        uint256 amount0,
        uint256 amount1
    );

    error Locked();
    error Unauthorized();
    error Initialized();
    error Finalized();
    error NotFinalized();
    error InvalidBlockTimestamp();
    error InvalidTicks();
    error InvalidLiquidityDelta();
    error InvalidSqrtPriceLimitX96();
    error SqrtPriceX96ExceedsLimit();
    error Amount0LessThanMin();
    error Amount1LessThanMin();
    error InvalidAmountSpecified();

    constructor(
        address _factory,
        address _token0,
        address _token1,
        int24 _tickLower,
        int24 _tickUpper,
        address _supplier,
        uint256 _blockTimestampInitialize
    ) {
        factory = _factory;
        token0 = _token0;
        token1 = _token1;

        if (_tickLower >= _tickUpper) revert InvalidTicks();
        tickLower = _tickLower;
        tickUpper = _tickUpper;
        sqrtPriceLowerX96 = TickMath.getSqrtRatioAtTick(_tickLower);
        sqrtPriceUpperX96 = TickMath.getSqrtRatioAtTick(_tickUpper);

        supplier = _supplier;

        if (block.timestamp > _blockTimestampInitialize)
            revert InvalidBlockTimestamp();
        blockTimestampInitialize = _blockTimestampInitialize;
    }

    /// @inheritdoc IMarginalV1LBPool
    function initialize(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        bytes calldata data
    ) external returns (uint256 shares, uint256 amount0, uint256 amount1) {
        if (msg.sender != supplier) revert Unauthorized();
        if (
            sqrtPriceX96 != sqrtPriceLowerX96 ||
            sqrtPriceX96 != sqrtPriceUpperX96
        ) revert RangeMath.InvalidSqrtPriceX96();
        if (block.timestamp < blockTimestampInitialize)
            revert InvalidBlockTimestamp();
        if (state.sqrtPriceX96 > 0) revert Initialized();

        sqrtPriceInitializeX96 = sqrtPriceX96;
        sqrtPriceFinalizeX96 = sqrtPriceX96 == sqrtPriceLowerX96
            ? sqrtPriceUpperX96
            : sqrtPriceLowerX96;

        uint8 feeProtocol = IMarginalV1LBFactory(factory).feeProtocol();
        state = State({
            sqrtPriceX96: sqrtPriceX96,
            totalPositions: 0,
            liquidity: 0,
            tick: tick,
            blockTimestamp: _blockTimestamp(),
            tickCumulative: 0,
            feeProtocol: feeProtocol,
            finalized: false
        });
        unlocked = 2;

        (shares, amount0, amount1) = mint(address(this), liquidity, data);

        emit Initialize(liquidity, sqrtPriceX96, tick);
    }

    /// @inheritdoc IMarginalV1LBPool
    function finalize(
        bytes calldata data
    )
        external
        lock
        returns (
            uint128 liquidityDelta,
            uint160 sqrtPriceX96,
            uint256 amount0,
            uint256 amount1
        )
    {
        if (msg.sender != supplier) revert Unauthorized();
        if (!state.finalized && !_canExit()) revert NotFinalized(); // allows override if past minimum duration

        // burn liquidity to supplier
        (liquidityDelta, amount0, amount1) = burn(msg.sender, totalSupply());

        // notify supplier of funds transferred on burn
        sqrtPriceX96 = state.sqrtPriceX96;
        IMarginalV1LBFinalizeCallback(msg.sender).marginalV1LBFinalizeCallback(
            amount0,
            amount1,
            data
        );

        emit Finalize(liquidityDelta, sqrtPriceX96, amount0, amount1);
    }

    function _canExit() internal view returns (bool) {
        bool initialized = state.sqrtPriceX96 > 0;
        return (initialized &&
            (block.timestamp - blockTimestampInitialize >= MINIMUM_DURATION));
    }

    function _blockTimestamp() internal view virtual returns (uint32) {
        return uint32(block.timestamp);
    }

    function balance0() private view returns (uint256) {
        return IERC20(token0).balanceOf(address(this));
    }

    function balance1() private view returns (uint256) {
        return IERC20(token1).balanceOf(address(this));
    }

    function stateSynced() private view returns (State memory) {
        State memory _state = state;
        // oracle update
        unchecked {
            uint32 delta = _blockTimestamp() - _state.blockTimestamp;
            if (delta == 0) return _state; // early exit if nothing to update
            _state.tickCumulative += int56(_state.tick) * int56(uint56(delta)); // overflow desired
            _state.blockTimestamp = _blockTimestamp();
        }
        return _state;
    }

    /// @inheritdoc IMarginalV1Pool
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external lock returns (int256 amount0, int256 amount1) {
        State memory _state = stateSynced();
        if (amountSpecified == 0) revert InvalidAmountSpecified();
        if (
            zeroForOne
                ? !(sqrtPriceLimitX96 < _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert InvalidSqrtPriceLimitX96();
        if (_state.finalized) revert Finalized();

        bool exactInput = amountSpecified > 0;
        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            _state.liquidity,
            _state.sqrtPriceX96,
            zeroForOne,
            amountSpecified
        );
        if (
            zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert SqrtPriceX96ExceedsLimit();

        // clamp if exceeds lower or upper range limits
        // @dev no need to revert on exact input as trader pays more than necessary
        if (
            !exactInput &&
            (sqrtPriceX96Next < sqrtPriceLowerX96 ||
                sqrtPriceX96Next > sqrtPriceUpperX96)
        ) revert RangeMath.InvalidSqrtPriceX96();
        else if (sqrtPriceX96Next < sqrtPriceLowerX96)
            sqrtPriceX96Next = sqrtPriceLowerX96;
        else if (sqrtPriceX96Next > sqrtPriceUpperX96)
            sqrtPriceX96Next = sqrtPriceUpperX96;

        // amounts without fees
        // TODO: check amountSpecified >= amount{1,0} for exact input when clamp
        (amount0, amount1) = SwapMath.swapAmounts(
            _state.liquidity,
            _state.sqrtPriceX96,
            sqrtPriceX96Next
        );

        // optimistic amount out with callback for amount in
        if (!zeroForOne) {
            amount0 = !exactInput ? amountSpecified : amount0; // in case of rounding issues
            amount1 = exactInput ? amountSpecified : amount1;

            if (amount0 < 0)
                TransferHelper.safeTransfer(
                    token0,
                    recipient,
                    uint256(-amount0)
                );

            uint256 balance1Before = balance1();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            if (amount1 == 0 || balance1Before + uint256(amount1) > balance1())
                revert Amount1LessThanMin();

            _state.sqrtPriceX96 = sqrtPriceX96Next;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);
        } else {
            amount1 = !exactInput ? amountSpecified : amount1; // in case of rounding issues
            amount0 = exactInput ? amountSpecified : amount0;

            if (amount1 < 0)
                TransferHelper.safeTransfer(
                    token1,
                    recipient,
                    uint256(-amount1)
                );

            uint256 balance0Before = balance0();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            if (amount0 == 0 || balance0Before + uint256(amount0) > balance0())
                revert Amount0LessThanMin();

            _state.sqrtPriceX96 = sqrtPriceX96Next;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);
        }

        // lbp done if reaches final sqrt price
        _state.finalized = (_state.sqrtPriceX96 == sqrtPriceFinalizeX96);

        // update pool state to latest
        state = _state;

        emit Swap(
            msg.sender,
            recipient,
            amount0,
            amount1,
            _state.sqrtPriceX96,
            _state.liquidity,
            _state.tick
        );
    }

    /// @notice Adds liquidity to the pool range position with ticks (tickLower, tickUpper)
    function mint(
        address recipient,
        uint128 liquidityDelta,
        bytes calldata data
    ) private returns (uint256 shares, uint256 amount0, uint256 amount1) {
        uint256 _totalSupply = totalSupply();
        bool initializing = (_totalSupply == 0);

        State memory _state = stateSynced();
        uint128 liquidityDeltaMinimum = (initializing ? MINIMUM_LIQUIDITY : 0);
        if (liquidityDelta <= liquidityDeltaMinimum)
            revert InvalidLiquidityDelta();

        // amounts in adjusted for concentrated range position price limits
        (amount0, amount1) = RangeMath.toAmounts(
            liquidityDelta,
            _state.sqrtPriceX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );
        amount0 += 1; // rough round up on amounts in when add liquidity
        amount1 += 1;

        // total liquidity is available liquidity if all locked liquidity was returned to pool
        uint128 totalLiquidityAfter = _state.liquidity + liquidityDelta;
        shares = initializing
            ? totalLiquidityAfter
            : Math.mulDiv(
                _totalSupply,
                liquidityDelta,
                totalLiquidityAfter - liquidityDelta
            );

        _state.liquidity += liquidityDelta;

        // callback for amounts owed
        uint256 balance0Before = balance0();
        uint256 balance1Before = balance1();
        IMarginalV1MintCallback(msg.sender).marginalV1MintCallback(
            amount0,
            amount1,
            data
        );
        if (balance0Before + amount0 > balance0()) revert Amount0LessThanMin();
        if (balance1Before + amount1 > balance1()) revert Amount1LessThanMin();

        // update pool state to latest
        state = _state;

        emit Mint(msg.sender, recipient, liquidityDelta, amount0, amount1);
    }

    /// @notice Removes liquidity from the pool range position with ticks (tickLower, tickUpper)
    function burn(
        address recipient,
        uint256 shares
    )
        private
        returns (uint128 liquidityDelta, uint256 amount0, uint256 amount1)
    {
        State memory _state = stateSynced();
        uint256 _totalSupply = totalSupply();

        // total liquidity is available liquidity if all locked liquidity were returned to pool
        uint128 totalLiquidityBefore = _state.liquidity;
        liquidityDelta = uint128(
            Math.mulDiv(totalLiquidityBefore, shares, _totalSupply)
        );
        if (liquidityDelta > _state.liquidity) revert InvalidLiquidityDelta();

        // amounts out adjusted for concentrated range position price limits
        (amount0, amount1) = RangeMath.toAmounts(
            liquidityDelta,
            _state.sqrtPriceX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );

        _state.liquidity -= liquidityDelta;

        // factor in protocol fees taken on burn
        (uint256 fees0, uint256 fees1) = RangeMath.rangeFees(
            amount0,
            amount1,
            _state.feeProtocol
        );

        if (amount0 > fees0)
            TransferHelper.safeTransfer(token0, recipient, amount0 - fees0);
        if (amount1 > fees1)
            TransferHelper.safeTransfer(token1, recipient, amount1 - fees1);

        if (fees0 > 0) TransferHelper.safeTransfer(token0, factory, fees0);
        if (fees1 > 0) TransferHelper.safeTransfer(token1, factory, fees1);

        // lbp definitively done
        _state.finalized = true;

        // update pool state to latest
        state = _state;

        emit Burn(msg.sender, recipient, liquidityDelta, amount0, amount1);
    }
}
