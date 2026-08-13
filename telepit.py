"""
BoitBlance - a 3 sajat szerzodes telepitese az Arc Testnetre.
=============================================================
A Circle Smart Contract Platformmal telepit (privat kulcs NEM kell, a Circle
tarcad + entity secret irja ala). A telepites utan elmenti a szerzodescimeket
a cimek.json fajlba (ezt hasznalja a tobbi script es a dashboard).

Futtatas (cmd, a projektmappabol):
    python telepit.py

Elofeltetel:
  - .env fajl CIRCLE_API_KEY + CIRCLE_ENTITY_SECRET ertekekkel
  - a telepito tarcan legyen egy keves Arc Testnet USDC (a gazra)
  - a build/ mappaban legyenek a leforditott szerzodesek (AgentBond/StreamPay/CommitStake .json)
"""

import os
import json
import time

from dotenv import load_dotenv
from circle.web3 import utils, smart_contract_platform, developer_controlled_wallets

load_dotenv()

# A telepito (deployer) Circle-tarcad cime - ezen legyen egy kis USDC a gazra.
DEPLOYER_ADDRESS = "0x774ECDb8b57C85aB610ED6C6bA3483F2E425c975"

USDC = "0x3600000000000000000000000000000000000000"
BLOCKCHAIN = "ARC-TESTNET"
CONTRACTS = ["AgentBond", "StreamPay", "CommitStake"]

api_key = os.getenv("CIRCLE_API_KEY")
entity_secret = os.getenv("CIRCLE_ENTITY_SECRET")

scp_client = utils.init_smart_contract_platform_client(api_key=api_key, entity_secret=entity_secret)
deploy_api = smart_contract_platform.DeployImportApi(scp_client)
view_api = smart_contract_platform.ViewUpdateApi(scp_client)

dcw_client = utils.init_developer_controlled_wallets_client(api_key=api_key, entity_secret=entity_secret)
wallets_api = developer_controlled_wallets.WalletsApi(dcw_client)


def find_wallet_id(address):
    resp = wallets_api.get_wallets()
    for w in resp.data.wallets or []:
        wallet = getattr(w, "actual_instance", w)
        if wallet.address.lower() == address.lower():
            return wallet.id
    raise RuntimeError(f"Nem talalhato tarca: {address}")


def deploy_one(name, wallet_id):
    art = json.load(open(f"build/{name}.json", encoding="utf-8"))
    print(f"\n-- {name} telepitese --")
    req = smart_contract_platform.ContractDeploymentRequest.from_dict({
        "name": f"BoitBlance {name}",
        "description": "BoitBlance agentic primitive on Arc Testnet",
        "walletId": wallet_id,
        "blockchain": BLOCKCHAIN,
        "abiJson": json.dumps(art["abi"]),
        "bytecode": art["bytecode"],
        "constructorParameters": [USDC],   # minden szerzodes constructora: address _usdc
        "feeLevel": "MEDIUM",
    })
    resp = deploy_api.deploy_contract(contract_deployment_request=req)
    contract_id = resp.data.contract_id
    print(f"   Contract ID: {contract_id}  (telepites folyamatban...)")

    # Varakozas a cimre
    for _ in range(60):
        time.sleep(3)
        c = view_api.get_contract(id=contract_id).data.contract
        if c.contract_address:
            print(f"   OK -> {c.contract_address}")
            if c.tx_hash:
                print(f"   Tx: https://testnet.arcscan.app/tx/{c.tx_hash}")
            return c.contract_address
        if getattr(c, "deployment_error_reason", None):
            raise RuntimeError(f"{name} telepites hiba: {c.deployment_error_reason}")
        print("   .", end="", flush=True)
    raise RuntimeError(f"{name} telepites idotullepes")


def main():
    print("=== BoitBlance - szerzodesek telepitese az Arc Testnetre ===")
    wallet_id = find_wallet_id(DEPLOYER_ADDRESS)
    print(f"Telepito tarca: {DEPLOYER_ADDRESS}  (ID: {wallet_id})")

    addresses = {"USDC": USDC, "chainId": 5042002}
    for name in CONTRACTS:
        addresses[name] = deploy_one(name, wallet_id)

    with open("cimek.json", "w", encoding="utf-8") as f:
        json.dump(addresses, f, indent=2)

    print("\n=== KESZ - a szerzodeseid telepitve ===")
    for name in CONTRACTS:
        print(f"  {name}: {addresses[name]}")
    print(f"\n  A cimek elmentve: cimek.json")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nHiba: {error}")
