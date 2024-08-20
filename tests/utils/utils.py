from math import log, sqrt

from eth_abi.packed import encode_packed
from eth_utils import keccak

from utils.constants import FEE_UNIT


def get_position_key(address: str, id: int) -> bytes:
    return keccak(encode_packed(["address", "uint96"], [address, id]))


def calc_tick_from_sqrt_price_x96(sqrt_price_x96: int) -> int:
    price = (sqrt_price_x96**2) / (1 << 192)
    return int(log(price) // log(1.0001))


def calc_sqrt_price_x96_from_tick(tick: int) -> int:
    return int(sqrt(1.0001**tick)) * (1 << 96)


def calc_sqrt_price_x96_next_swap_exact_input(
    liquidity: int, sqrt_price_x96: int, zero_for_one: bool, amount_specified: int
) -> int:
    assert amount_specified > 0
    if zero_for_one:
        # sqrtP' = L / (del x + x)
        (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
            liquidity, sqrt_price_x96
        )
        return (liquidity << 96) // (reserve0 + amount_specified)
    else:
        # sqrtP' = del y / L + sqrtP
        return (amount_specified << 96) // liquidity + sqrt_price_x96


def calc_sqrt_price_x96_next_swap_exact_output(
    liquidity: int, sqrt_price_x96: int, zero_for_one: bool, amount_specified: int
) -> int:
    assert amount_specified <= 0
    if zero_for_one:
        # sqrtP' = del y / L + sqrtP
        return (amount_specified << 96) // liquidity + sqrt_price_x96
    else:
        # sqrtP' = L / (del x + x)
        (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
            liquidity, sqrt_price_x96
        )
        return (liquidity << 96) // (reserve0 + amount_specified)


def calc_sqrt_price_x96_next_swap(
    liquidity: int, sqrt_price_x96: int, zero_for_one: bool, amount_specified: int
) -> int:
    exact_input = amount_specified > 0
    return (
        calc_sqrt_price_x96_next_swap_exact_input(
            liquidity, sqrt_price_x96, zero_for_one, amount_specified
        )
        if exact_input
        else calc_sqrt_price_x96_next_swap_exact_output(
            liquidity, sqrt_price_x96, zero_for_one, amount_specified
        )
    )


def calc_amounts_from_liquidity_sqrt_price_x96(
    liquidity: int, sqrt_price_x96: int
) -> (int, int):
    amount0 = (liquidity << 96) // sqrt_price_x96
    amount1 = (liquidity * sqrt_price_x96) // (1 << 96)
    return (amount0, amount1)


# @dev sqrt in OZ solidity results in slight diff with python math.sqrt
def calc_liquidity_sqrt_price_x96_from_reserves(
    reserve0: int, reserve1: int
) -> (int, int):
    liquidity = int(sqrt(reserve0 * reserve1))
    sqrt_price_x96 = (liquidity << 96) // reserve0
    return (liquidity, sqrt_price_x96)


def calc_swap_amounts(
    liquidity: int, sqrt_price_x96: int, sqrt_price_x96_next: int
) -> (int, int):
    amount0 = (liquidity << 96) // sqrt_price_x96_next - (
        liquidity << 96
    ) // sqrt_price_x96
    amount1 = (liquidity * (sqrt_price_x96_next - sqrt_price_x96)) // (1 << 96)
    return (amount0, amount1)


def calc_swap_fees(amount_in: int, fee: int) -> int:
    return (amount_in * fee) // FEE_UNIT
