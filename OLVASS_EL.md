# BoitBlance

**3 agentic primitív, ami pénzügyileg megbízhatóvá teszi az AI-ügynököt.**
Saját okosszerződések az Arc Testneten, USDC-alapon.

## A három primitív

1. **AgentBond** — az ügynök USDC-**kauciót** tesz le. A szabad kaució egy nyilvános
   „credit score". Egy megbízó lekötheti egy munka mögé (obligation), majd
   **felszabadítja** (jó munka) vagy **slasheli** (csalás → a kaució a megbízóhoz kerül).

2. **StreamPay** — USDC **folyik másodpercenként** a fogadónak. A fogadó bármikor
   kiveheti az addig felgyűltet, a küldő bármikor leállíthatja és visszakapja a maradékot.

3. **CommitStake** — az ügynök pénzt tesz egy **vállalásra**; egy ellenőr a határidő előtt
   **megerősíti** (a tét visszajár), vagy határidő után **bárki kiváltja a slasht**
   (a tét a kedvezményezetthez kerül).

## Fájlok

| Fájl | Mire való |
|------|-----------|
| `contracts/BoitBlance.sol` | A három szerződés Solidity forráskódja |
| `build/*.json` | A lefordított szerződések (ABI + bytecode) |
| `telepit.py` | Telepíti a szerződéseket az Arc-ra (Circle SCP), elmenti a `cimek.json`-t |
| `cimek.json` | A telepített szerződéscímeid (telepítés után jön létre) |

## Telepítés (cmd)

```
cd C:\Users\Panoskir\Cowork\ARC2026\BoitBlance
copy ..\erc8004-quickstart\.env .env
pip install circle-smart-contract-platform python-dotenv
python telepit.py
```

A `telepit.py`:
- a Circle Smart Contract Platformmal telepíti a 3 szerződést (privát kulcs NEM kell),
- a telepítő tárcád a `0x774E...` (legyen rajta egy kis USDC a gázra),
- a végén elmenti a szerződéscímeket a `cimek.json`-ba.

> A `node_modules`, `package.json`, `compile.js` fájlok csak a Solidity fordításhoz
> kellettek — nyugodtan törölheted őket.

## Mi jön ezután

A telepítés után épülnek rá:
- `boitblance_demo.py` — teljes életciklus: kaució → munka → stream-fizetés → elszámolás,
- `boitblance_dashboard.html` — élő nézet a kaukciókról, streamekről, vállalásokról.

> Teszthálózati demó, nem auditált — éles használatra nem ajánlott.
