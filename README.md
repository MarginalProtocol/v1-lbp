# v1-lbp

Marginal v1 liquidity bootstrapping pool smart contracts.

## Mechanism

Uniswap v3 range position in a single pool with fixed upper and lower ticks set by liquidity bootstrapping pool supplier.

![range position](./assets/range-position.png)

The Marginal v1 liquidity bootstrapping pool starts at one end of the tick range with supplier providing tokens
in only one type of token (e.g. all in `token0` if start at `tickLower`). Buyers bid by swapping through the pool
for supplied token in exchange for token acquiring funds in.

Once price reaches the upper tick, the pool will contain only the acquired funds token. These funds are sent
back to the original supplier who may use them coupled with more token to seed liquidity pools.

## Installation

The repo uses [ApeWorX](https://github.com/apeworx/ape) for development.

Set up a virtual environment

```sh
python -m venv .venv
source .venv/bin/activate
```

Install requirements and Ape plugins

```sh
pip install -r requirements.txt
ape plugins install .
```

## Tests

Tests without fuzzing, integration

```sh
ape test -s -m "not fuzzing and not integration"
```

Tests with fuzzing but not integration

```sh
ape test -s -m "fuzzing and not integration"
```

Tests for integrations

```sh
ape test -s -m "integration" --network ethereum:mainnet-fork:foundry
```
