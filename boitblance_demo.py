"""
BoitBlance - teljes eletciklus demo
====================================
Vegigjatssza a harom primitivet a SAJAT telepitett szerzodeseiddel:

  1) AgentBond   - az ugynok 5 USDC kauciot tesz le; a megbizo lekot 2 USDC-t
                   egy munka moge, majd a vegen felszabaditja.
  2) StreamPay   - a megbizo 3 USDC streamet nyit az ugynoknek 60 masodpercre;
                   par masodperc utan az ugynok kiveszi a beerett reszt.
  3) CommitStake - az ugynok 2 USDC-t tesz egy vallalasra (ellenor = megbizo);
                   az ellenor megerositi, a tet visszajar.

Futtatas (cmd, a projektmappabol):
    python boitblance_demo.py

Elofeltetel: telepitett szerzodesek (cimek.json), .env a Circle adatokkal,
es USDC mindket tarcan.
"""

import os
import json
import sys
import time

from dotenv import load_dotenv
from circle.web3 import utils, developer_controlled_wallets
from web3 import Web3

load_dotenv()

# Szereplok (Circle-tarcaid)
AGENT_ADDRESS = "0xf195bf8b147a4c5c94f3dedf147a5f283fddf50a"     # az ugynok
BUSINESS_ADDRESS = "0xfd38e25aca03e65d4b203b329733cf7e9c1a414b"  # a megbizo / ellenor

# Osszegek (USDC, 6 tizedesjegy)
BOND = 5_000_000        # 5 USDC kaucio
OBLIGATION = 2_000_000  # 2 USDC lekotes
STREAM = 3_000_000      # 3 USDC stream
STREAM_SEC = 60         # 60 masodperc
COMMIT = 2_000_000      # 2 USDC vallalas

cimek = json.load(open("cimek.json", encoding="utf-8"))
USDC = cimek["USDC"]
AGENTBOND = cimek["AgentBond"]
STREAMPAY = cimek["StreamPay"]
COMMITSTAKE = cimek["CommitStake"]

dcw = utils.init_developer_controlled_wallets_client(
    api_key=os.getenv("CIRCLE_API_KEY"), entity_secret=os.getenv("CIRCLE_ENTITY_SECRET"))
tx_api = developer_controlled_wallets.TransactionsApi(dcw)
web3 = Web3(Web3.HTTPProvider("https://rpc.testnet.arc.network"))

# Minimalis ABI-k a kiolvasashoz (view)
abi_bond = [
    {"name": "bonded", "type": "function", "stateMutability": "view", "inputs": [{"type": "address"}], "outputs": [{"type": "uint256"}]},
    {"name": "locked", "type": "function", "stateMutability": "view", "inputs": [{"type": "address"}], "outputs": [{"type": "uint256"}]},
    {"name": "freeBond", "type": "function", "stateMutability": "view", "inputs": [{"type": "address"}], "outputs": [{"type": "uint256"}]},
    {"name": "obligationCount", "type": "function", "stateMutability": "view", "inputs": [], "outputs": [{"type": "uint256"}]},
]
abi_stream = [
    {"name": "recipientBalance", "type": "function", "stateMutability": "view", "inputs": [{"type": "uint256"}], "outputs": [{"type": "uint256"}]},
    {"name": "streamCount", "type": "function", "stateMutability": "view", "inputs": [], "outputs": [{"type": "uint256"}]},
]
abi_commit = [
    {"name": "commitmentCount", "type": "function", "stateMutability": "view", "inputs": [], "outputs": [{"type": "uint256"}]},
]

c_bond = web3.eth.contract(address=Web3.to_checksum_address(AGENTBOND), abi=abi_bond)
c_stream = web3.eth.contract(address=Web3.to_checksum_address(STREAMPAY), abi=abi_stream)
c_commit = web3.eth.contract(address=Web3.to_checksum_address(COMMITSTAKE), abi=abi_commit)


def retry(fn, label="muvelet", tries=5, delay=3):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            if i < tries - 1:
                print(f"\n  [!] Halozati hiba ({label}) - ujra {i + 1}...")
                time.sleep(delay)
    raise last


def wait_for(tx_id, label):
    sys.stdout.write(f"    {label}")
    sys.stdout.flush()
    for _ in range(60):
        time.sleep(2)
        try:
            tx = tx_api.get_transaction(id=tx_id)
        except Exception:
            sys.stdout.write("x"); sys.stdout.flush(); continue
        t = tx.data.transaction
        if t.state == "COMPLETE" and t.tx_hash:
            print(" OK")
            return t.tx_hash
        if t.state == "FAILED":
            raise RuntimeError(f"{label} hibazott a lancon")
        sys.stdout.write("."); sys.stdout.flush()
    raise RuntimeError(f"{label} idotullepes")


def call(wallet, contract, sig, params, label):
    def send():
        req = developer_controlled_wallets.CreateContractExecutionTransactionForDeveloperRequest.from_dict({
            "walletAddress": wallet, "blockchain": "ARC-TESTNET",
            "contractAddress": contract, "abiFunctionSignature": sig,
            "abiParameters": params, "feeLevel": "MEDIUM"})
        return tx_api.create_developer_transaction_contract_execution(req)
    return wait_for(retry(send, label).data.id, label)


def usd(x):
    return f"{x/1_000_000:.2f} USDC"


def main():
    print("=== BoitBlance - teljes eletciklus demo ===")
    print(f"  Ugynok:  {AGENT_ADDRESS}")
    print(f"  Megbizo: {BUSINESS_ADDRESS}")

    # ---------- 1) AGENTBOND ----------
    print("\n== 1) AgentBond - kaucio ==")
    print(f"  Az ugynok {usd(BOND)} kauciot tesz le...")
    call(AGENT_ADDRESS, USDC, "approve(address,uint256)", [AGENTBOND, str(BOND)], "USDC jovahagyas")
    call(AGENT_ADDRESS, AGENTBOND, "deposit(uint256)", [str(BOND)], "kaucio letetele")
    free = c_bond.functions.freeBond(Web3.to_checksum_address(AGENT_ADDRESS)).call()
    print(f"  Szabad kaucio (credit score): {usd(free)}")

    print(f"  A megbizo lekot {usd(OBLIGATION)}-t egy munka moge...")
    call(BUSINESS_ADDRESS, AGENTBOND, "lockObligation(address,uint256)", [AGENT_ADDRESS, str(OBLIGATION)], "obligation lekotes")
    oblig_id = c_bond.functions.obligationCount().call() - 1
    free2 = c_bond.functions.freeBond(Web3.to_checksum_address(AGENT_ADDRESS)).call()
    print(f"  Obligation ID: {oblig_id} | szabad kaucio most: {usd(free2)}")

    # ---------- 2) STREAMPAY ----------
    print("\n== 2) StreamPay - folyamatos fizetes ==")
    print(f"  A megbizo {usd(STREAM)} streamet nyit az ugynoknek {STREAM_SEC} mp-re...")
    call(BUSINESS_ADDRESS, USDC, "approve(address,uint256)", [STREAMPAY, str(STREAM)], "USDC jovahagyas")
    call(BUSINESS_ADDRESS, STREAMPAY, "createStream(address,uint256,uint256)",
         [AGENT_ADDRESS, str(STREAM), str(STREAM_SEC)], "stream nyitas")
    stream_id = c_stream.functions.streamCount().call() - 1
    print(f"  Stream ID: {stream_id}")

    print("  Varunk 15 masodpercet, amig folyik a penz...")
    time.sleep(15)
    vested = c_stream.functions.recipientBalance(stream_id).call()
    print(f"  Eddig beerett az ugynoknek: {usd(vested)} -> kiveszi")
    if vested > 0:
        call(AGENT_ADDRESS, STREAMPAY, "withdraw(uint256,uint256)", [str(stream_id), str(vested)], "stream kivet")

    # ---------- 3) COMMITSTAKE ----------
    print("\n== 3) CommitStake - vallalas zalogban ==")
    deadline = web3.eth.get_block("latest")["timestamp"] + 3600
    print(f"  Az ugynok {usd(COMMIT)}-t tesz egy vallalasra (ellenor = megbizo)...")
    call(AGENT_ADDRESS, USDC, "approve(address,uint256)", [COMMITSTAKE, str(COMMIT)], "USDC jovahagyas")
    call(AGENT_ADDRESS, COMMITSTAKE, "createCommitment(address,address,uint256,uint256,string)",
         [BUSINESS_ADDRESS, BUSINESS_ADDRESS, str(deadline), str(COMMIT), "Elkeszitem a riportot hatardiore"], "vallalas letrehozas")
    commit_id = c_commit.functions.commitmentCount().call() - 1
    print(f"  Commitment ID: {commit_id}")
    print("  Az ellenor megerositi a teljesitest -> a tet visszajar...")
    call(BUSINESS_ADDRESS, COMMITSTAKE, "confirm(uint256)", [str(commit_id)], "ellenor megerosites")

    # ---------- ELSZAMOLAS ----------
    print("\n== Elszamolas ==")
    print("  A munka kesz -> a megbizo felszabaditja a lekotott kauciot...")
    call(BUSINESS_ADDRESS, AGENTBOND, "release(uint256)", [str(oblig_id)], "obligation felszabaditas")
    free3 = c_bond.functions.freeBond(Web3.to_checksum_address(AGENT_ADDRESS)).call()

    print("\n=== KESZ ===")
    print(f"  Ugynok szabad kaucioja:  {usd(free3)}")
    print(f"  Obligation #{oblig_id}: felszabaditva")
    print(f"  Stream #{stream_id}: az ugynok kapott {usd(vested)}-t a munkavegzes alatt")
    print(f"  Commitment #{commit_id}: teljesitve, a tet visszajart")
    print(f"\n  Dashboard: tolts be cimek.json-t a boitblance_dashboard.html-be,")
    print(f"  es nezd meg az ugynokod ({AGENT_ADDRESS}) kaucioiat es a streameket.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nHiba: {error}")
        sys.exit(1)
