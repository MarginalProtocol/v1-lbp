import click

from ape import accounts, chain, project


def main():
    click.echo(f"Running deploy.py on chainid {chain.chain_id} ...")

    deployer_name = click.prompt("Deployer account name", default="")
    deployer = (
        accounts.load(deployer_name)
        if deployer_name != ""
        else accounts.test_accounts[0]
    )
    click.echo(f"Deployer address: {deployer.address}")
    click.echo(f"Deployer balance: {deployer.balance / 1e18} ETH")

    margv1_factory_address = click.prompt("Marginal v1 factory address", type=str)
    weth9_address = click.prompt("WETH9 address", type=str)
    publish = click.prompt("Publish to Etherscan?", default=False)

    # deploy marginal v1lb deployer if not provided
    pool_deployer_address = None
    if click.confirm("Deploy Marginal v1lb pool deployer?"):
        click.echo("Deploying Marginal v1lb pool deployer ...")
        pool_deployer = project.MarginalV1LBPoolDeployer.deploy(
            sender=deployer, publish=publish
        )
        pool_deployer_address = pool_deployer.address
        click.echo(f"Deployed Marginal v1lb pool deployer to {pool_deployer_address}")
    else:
        pool_deployer_address = click.prompt(
            "Marginal v1lb pool deployer address", type=str
        )

    # deploy marginal v1lb factory
    click.echo("Deploying Marginal v1lb factory ...")
    factory = project.MarginalV1LBFactory.deploy(
        pool_deployer_address,
        sender=deployer,
        publish=publish,
    )
    click.echo(f"Deployed Marginal v1lb factory to {factory.address}")

    # change owner if user wants
    if click.confirm("Change Marginal v1lb factory owner?"):
        owner_address = click.prompt("Marginal v1lb factory owner address", type=str)
        factory.setOwner(owner_address, sender=deployer)

    # deploy marginal v1lb router
    if click.confirm("Deploy Marginal v1lb router?"):
        click.echo("Deploying Marginal v1lb router ...")
        router = project.V1LBRouter.deploy(
            factory.address,
            margv1_factory_address,
            weth9_address,
            sender=deployer,
            publish=publish,
        )
        click.echo(f"Deployed Marginal v1lb router to {router.address}")

    # deploy marginal v1lb supplier
    supplier = None
    if click.confirm("Deploy Marginal v1lb supplier?"):
        click.echo("Deploying Marginal v1lb supplier ...")
        supplier = project.MarginalV1LBSupplier.deploy(
            factory.address,
            margv1_factory_address,
            weth9_address,
            sender=deployer,
            publish=publish,
        )
        click.echo(f"Deployed Marginal v1lb supplier to {supplier.address}")

    # deploy marginal v1lb liquidity receiver deployer
    if click.confirm("Deploy Marginal v1lb liquidity receiver deployer?"):
        click.echo("Deploying Marginal v1lb liquidity receiver deployer ...")
        supplier_address = (
            supplier.address
            if supplier is not None
            else click.prompt("Marginal v1lb supplier address", type=str)
        )
        univ3_manager_address = click.prompt("Uniswap v3 manager address", type=str)
        margv1_initializer_address = click.prompt(
            "Marginal v1 initializer address", type=str
        )
        margv1_router_address = click.prompt("Marginal v1 router address", type=str)
        liquidity_receiver_deployer = (
            project.MarginalV1LBLiquidityReceiverDeployer.deploy(
                supplier_address,
                univ3_manager_address,
                margv1_factory_address,
                margv1_initializer_address,
                margv1_router_address,
                weth9_address,
                sender=deployer,
                publish=publish,
            )
        )
        click.echo(
            f"Deployed Marginal v1lb liquidity receiver deployer to {liquidity_receiver_deployer.address}"
        )
