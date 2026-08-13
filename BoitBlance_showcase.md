# BoitBlance — 3 primitives that make an autonomous agent financially trustworthy

*Built on Arc Testnet, USDC-native. A trust + settlement stack for the agent economy.*

## The problem

Before an AI agent can act with your money, you need to **trust it**. While it works, you need to **pay it fairly**. And when it makes a promise, you need a way to **hold it to that promise** — without a middleman.

BoitBlance ships three composable on-chain primitives that solve exactly this, all settling in USDC on Arc.

## The three primitives

### 1) AgentBond — reputation-backed trust
An agent deposits a USDC **bond** as collateral. Its *free bond* is a public credit score anyone can read. A counterparty can **lock** a slice of that bond behind a job:
- Agent performs → the lock is **released**, the bond is freed.
- Agent defaults → the lock is **slashed**, and the collateral goes to the counterparty.

Trust becomes a number you can slash.

### 2) StreamPay — continuous settlement by the second
Lock USDC into a **stream** that vests to the recipient linearly, second by second. Pay-per-inference, per-API-call, per-second subscriptions — the recipient withdraws whatever has vested at any moment, and the sender can cancel and reclaim the rest. No invoices, no upfront lump sum.

### 3) CommitStake — a promise put up as collateral
An agent stakes USDC behind a goal with a deadline. A **verifier** confirms completion before the deadline (stake returned), or after the deadline **anyone** can trigger the slash and the stake goes to the beneficiary.

## How an agent uses all three

1. **Bond up** — the agent deposits USDC into AgentBond; its free bond is its credit score.
2. **Get hired** — a business reads the bond and decides the agent is trustworthy.
3. **Lock collateral** — the business locks a slice of the bond behind the job.
4. **Stream pay** — a StreamPay stream pays the agent by the second as it works.
5. **Settle** — performed → bond released and stream withdrawn; defaulted → bond slashed.

## Built on Circle & Arc

- **USDC** is the settlement rail for every bond, stream, and stake.
- **Arc** gives deterministic, sub-second finality and USDC-denominated gas — the agent budgets, pays fees, and settles in one unit.
- **Circle Developer-Controlled Wallets** sign every transaction — no private key on disk ever touches the chain.
- The contracts were **compiled and deployed via the Circle Smart Contract Platform** (no raw private key), then exercised end-to-end in real USDC on Arc Testnet.

## Live on Arc Testnet (chain 5042002)

| Contract | Address |
|---|---|
| AgentBond | [`0xb92e9e0737e585a5032ce64a43a118f6bd8e15e0`](https://testnet.arcscan.app/address/0xb92e9e0737e585a5032ce64a43a118f6bd8e15e0) |
| StreamPay | [`0xe2d81453ff4d870375566bd5e29f174661b1e5f6`](https://testnet.arcscan.app/address/0xe2d81453ff4d870375566bd5e29f174661b1e5f6) |
| CommitStake | [`0xd42f3deb8906b54c75b85c3cb9e05457fb574a0b`](https://testnet.arcscan.app/address/0xd42f3deb8906b54c75b85c3cb9e05457fb574a0b) |

A full lifecycle — deposit bond → lock obligation → open stream → withdraw vested USDC → confirm commitment → release (and a slash branch) — runs against these live contracts, plus a local web control panel that triggers every action with a button click.

## What it enables

- **Data / API agents** paid per second of use (price feeds, inference, monitoring).
- **Work agents** (research, summaries, translation) that back their quality with a slashable bond.
- **DeFi / payments agents** with real skin in the game.
- **Verifier / oracle agents** that are themselves bonded, so honesty is the rational choice.
- **SLA and deadline commitments** enforced by stake.
- **Agent-to-agent subcontracting** — escrow + bond + streaming, settled without a human.

## Notes

This is a testnet demo and the contracts are **not audited** — not for production use. The goal is to show that trust and settlement for autonomous agents can be a small set of composable, USDC-native primitives on Arc.

---

*Built during the Arc Testnet / agentic economy exploration. Contracts, deploy script, end-to-end demo, and a web control panel included.*
