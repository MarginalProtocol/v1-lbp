# v1-lbp

Marginal v1 liquidity bootstrapping pool smart contracts.

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

Tests without fuzzing

```sh
ape test -s -m "not fuzzing"
```

Tests with fuzzing

```sh
ape test -s -m "fuzzing"
```
# v1-lbp
