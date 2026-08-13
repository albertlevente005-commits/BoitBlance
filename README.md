# BoitBlance

**Three on-chain primitives that make an autonomous AI agent financially trustworthy — USDC-native on Arc.**

Trust + settlement for the agent economy, deployed and exercised end-to-end on **Arc Testnet** via Circle Developer-Controlled Wallets and the Circle Smart Contract Platform.

> Testnet demo, not audited — not for production use.

## The three primitives

1. **AgentBond** — an agent deposits a USDC **bond** as collateral. Its free bond is a public on-chain credit score. A counterparty can **lock** a slice behind a job, then **release** it (agent performs) or **slash** it to the counterparty (agent defaults).

2. **StreamPay** — lock USDC into a **stream** that vests to the recipient **per second**. Pay-per-inference, per-API-call, per-second subscriptions. The recipient withdraws what has vested anytime; the sender can cancel and reclaim the rest.

3. **CommitStake** — an agent **stakes** USDC behind a goal with a deadline. A **verifier** confirms completion before the deadline (stake returned), or after the deadline anyone can trigger the **slash** (stake goes to the beneficiary).

## Deployed contracts (Arc Testnet, chain 5042002)

| Contract | Address |
|---|---|
| AgentBond | [`0xb92e9e0737e585a5032ce64a43a118f6bd8e15e0`](https://testnet.arcscan.app/address/0xb92e9e0737e585a5032ce64a43a118f6bd8e15e0) |
| StreamPay | [`0xe2d81453ff4d870375566bd5e29f174661b1e5f6`](https://testnet.arcscan.app/address/0xe2d81453ff4d870375566bd5e29f174661b1e5f6) |
| CommitStake | [`0xd42f3deb8906b54c75b85c3cb9e05457fb574a0b`](https://testnet.arcscan.app/address/0xd42f3deb8906b54c75b85c3cb9e05457fb574a0b) |

## Repo contents

| File | What it is |
|---|---|
| `contracts/BoitBlance.sol` | The three Solidity contracts |
| `build/*.json` | Compiled ABI + bytecode |
| `telepit.py` | Deploys the contracts via Circle Smart Contract Platform |
| `boitblance_demo.py` | Full lifecycle demo (bond → lock → stream → withdraw → settle) |
| `webapp.py` | Local web control panel (Flask) to trigger every action |
| `.env.minta` | Environment template (copy to `.env`, fill your Circle keys) |

## Tech stack

Solidity, Python, web3.py, Flask, Circle Developer-Controlled Wallets, Circle Smart Contract Platform, ethers.js, USDC, Arc Testnet.

## Run

```bash
pip install circle-developer-controlled-wallets circle-smart-contract-platform web3 python-dotenv flask
copy .env.minta .env   # then fill CIRCLE_API_KEY + CIRCLE_ENTITY_SECRET
python telepit.py       # deploy your own contracts
python boitblance_demo.py
python webapp.py        # open http://127.0.0.1:5000
```

## Security

Never commit your `.env`, `recovery/` folder, API keys, or entity secret. They control your Circle wallets.
