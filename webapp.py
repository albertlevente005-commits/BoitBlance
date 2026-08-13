"""
BoitBlance - helyi webes vezerlofelulet (Flask)
================================================
Egy bongeszobol gombnyomassal indithato felulet a 3 primitivhez. A gombok egy
helyi Python szervert hivnak, ami a Circle-tarcaiddal alairja a tranzakciokat
(a titkos kulcsok a gepen maradnak, nem a bongeszoben).

Inditas (cmd, a projektmappabol):
    pip install flask
    python webapp.py

Aztan nyisd meg a bongeszoben:  http://127.0.0.1:5000
"""

import os
import json
import time
import threading

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from circle.web3 import utils, developer_controlled_wallets
from web3 import Web3

load_dotenv()

AGENT = "0xf195bf8b147a4c5c94f3dedf147a5f283fddf50a"     # ugynok
BUSINESS = "0xfd38e25aca03e65d4b203b329733cf7e9c1a414b"  # megbizo / ellenor

cimek = json.load(open("cimek.json", encoding="utf-8"))
USDC = cimek["USDC"]; AGENTBOND = cimek["AgentBond"]; STREAMPAY = cimek["StreamPay"]; COMMITSTAKE = cimek["CommitStake"]

dcw = utils.init_developer_controlled_wallets_client(
    api_key=os.getenv("CIRCLE_API_KEY"), entity_secret=os.getenv("CIRCLE_ENTITY_SECRET"))
tx_api = developer_controlled_wallets.TransactionsApi(dcw)
web3 = Web3(Web3.HTTPProvider("https://rpc.testnet.arc.network"))

abi_bond = [
    {"name":"bonded","type":"function","stateMutability":"view","inputs":[{"type":"address"}],"outputs":[{"type":"uint256"}]},
    {"name":"locked","type":"function","stateMutability":"view","inputs":[{"type":"address"}],"outputs":[{"type":"uint256"}]},
    {"name":"freeBond","type":"function","stateMutability":"view","inputs":[{"type":"address"}],"outputs":[{"type":"uint256"}]},
    {"name":"obligationCount","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"uint256"}]},
]
abi_stream = [
    {"name":"recipientBalance","type":"function","stateMutability":"view","inputs":[{"type":"uint256"}],"outputs":[{"type":"uint256"}]},
    {"name":"streamCount","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"uint256"}]},
]
abi_commit = [
    {"name":"commitmentCount","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"uint256"}]},
]
c_bond = web3.eth.contract(address=Web3.to_checksum_address(AGENTBOND), abi=abi_bond)
c_stream = web3.eth.contract(address=Web3.to_checksum_address(STREAMPAY), abi=abi_stream)
c_commit = web3.eth.contract(address=Web3.to_checksum_address(COMMITSTAKE), abi=abi_commit)


def wait_for(tx_id):
    for _ in range(60):
        time.sleep(2)
        try:
            t = tx_api.get_transaction(id=tx_id).data.transaction
        except Exception:
            continue
        if t.state == "COMPLETE" and t.tx_hash:
            return t.tx_hash
        if t.state == "FAILED":
            raise RuntimeError("a tranzakcio hibazott a lancon")
    raise RuntimeError("idotullepes")


def call(wallet, contract, sig, params):
    req = developer_controlled_wallets.CreateContractExecutionTransactionForDeveloperRequest.from_dict({
        "walletAddress": wallet, "blockchain": "ARC-TESTNET",
        "contractAddress": contract, "abiFunctionSignature": sig,
        "abiParameters": params, "feeLevel": "MEDIUM"})
    resp = tx_api.create_developer_transaction_contract_execution(req)
    return wait_for(resp.data.id)


def to_units(usdc_str):
    return str(int(round(float(usdc_str) * 1_000_000)))


app = Flask(__name__)


@app.errorhandler(Exception)
def handle_err(e):
    # Minden hiba tiszta JSON-kent menjen vissza (ne HTML hibalap)
    return jsonify({"ok": False, "message": f"Hiba: {e}"}), 200


@app.route("/")
def index():
    return HTML


@app.route("/api/status")
def status():
    a = Web3.to_checksum_address(AGENT)
    return jsonify({
        "freeBond": c_bond.functions.freeBond(a).call() / 1e6,
        "bonded": c_bond.functions.bonded(a).call() / 1e6,
        "locked": c_bond.functions.locked(a).call() / 1e6,
        "obligations": c_bond.functions.obligationCount().call(),
        "streams": c_stream.functions.streamCount().call(),
        "commitments": c_commit.functions.commitmentCount().call(),
    })


def ok(msg, tx=None, **extra):
    d = {"ok": True, "message": msg}
    if tx: d["tx"] = f"https://testnet.arcscan.app/tx/{tx}"
    d.update(extra); return jsonify(d)


@app.route("/api/bond", methods=["POST"])
def bond():
    amt = to_units(request.json["amount"])
    call(AGENT, USDC, "approve(address,uint256)", [AGENTBOND, amt])
    tx = call(AGENT, AGENTBOND, "deposit(uint256)", [amt])
    return ok(f"Az ugynok letett {request.json['amount']} USDC kauciot.", tx)


@app.route("/api/lock", methods=["POST"])
def lock():
    amt = to_units(request.json["amount"])
    tx = call(BUSINESS, AGENTBOND, "lockObligation(address,uint256)", [AGENT, amt])
    new_id = c_bond.functions.obligationCount().call() - 1
    return ok(f"A megbizo lekotott {request.json['amount']} USDC-t. Obligation ID: {new_id}", tx, id=new_id)


@app.route("/api/release", methods=["POST"])
def release():
    oid = str(int(request.json["id"]))
    try:
        tx = call(BUSINESS, AGENTBOND, "release(uint256)", [oid])
    except Exception:
        return jsonify({"ok": False, "message": f"Felszabaditas sikertelen: az obligation #{oid} valoszinuleg mar nem aktiv, vagy rossz az ID. Hozz letre egy uj Lekotest, es annak az ID-jat hasznald."})
    return ok(f"Obligation #{oid} felszabaditva (a kaucio visszajar).", tx)


@app.route("/api/slash", methods=["POST"])
def slash():
    oid = str(int(request.json["id"]))
    try:
        tx = call(BUSINESS, AGENTBOND, "slash(uint256)", [oid])
    except Exception:
        return jsonify({"ok": False, "message": f"Slash sikertelen: az obligation #{oid} valoszinuleg mar nem aktiv (felszabaditva/slashelve), vagy rossz az ID. Nyiss egy uj Lekotest, jegyezd meg az ID-jat, es AZT slasheld."})
    return ok(f"Obligation #{oid} SLASHELVE - a kaucio a megbizohoz kerult.", tx)


@app.route("/api/stream", methods=["POST"])
def stream():
    amt = to_units(request.json["amount"]); sec = str(int(request.json["seconds"]))
    call(BUSINESS, USDC, "approve(address,uint256)", [STREAMPAY, amt])
    tx = call(BUSINESS, STREAMPAY, "createStream(address,uint256,uint256)", [AGENT, amt, sec])
    new_id = c_stream.functions.streamCount().call() - 1
    return ok(f"Stream nyitva: {request.json['amount']} USDC / {sec} mp. Stream ID: {new_id}", tx, id=new_id)


@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    sid = int(request.json["id"])
    avail = c_stream.functions.recipientBalance(sid).call()
    if avail == 0:
        return jsonify({"ok": False, "message": "Meg nincs kivehető osszeg ezen a streamen."})
    tx = call(AGENT, STREAMPAY, "withdraw(uint256,uint256)", [str(sid), str(avail)])
    return ok(f"Az ugynok kivett {avail/1e6:.2f} USDC-t a #{sid} streambol.", tx)


@app.route("/api/commit", methods=["POST"])
def commit():
    amt = to_units(request.json["amount"]); goal = request.json.get("goal", "vallalas")[:120]
    deadline = str(web3.eth.get_block("latest")["timestamp"] + 3600)
    call(AGENT, USDC, "approve(address,uint256)", [COMMITSTAKE, amt])
    tx = call(AGENT, COMMITSTAKE, "createCommitment(address,address,uint256,uint256,string)",
              [BUSINESS, BUSINESS, deadline, amt, goal])
    new_id = c_commit.functions.commitmentCount().call() - 1
    return ok(f"Vallalas letrehozva: {request.json['amount']} USDC tet. Commitment ID: {new_id}", tx, id=new_id)


@app.route("/api/confirm", methods=["POST"])
def confirm():
    cid = str(int(request.json["id"]))
    try:
        tx = call(BUSINESS, COMMITSTAKE, "confirm(uint256)", [cid])
    except Exception:
        return jsonify({"ok": False, "message": f"Megerosites sikertelen: a vallalas #{cid} valoszinuleg mar lezarult, vagy rossz az ID. Hozz letre egy uj Vallalast, es annak az ID-jat erositsd meg."})
    return ok(f"Commitment #{cid} megerositve - a tet visszajart a stakelohoz.", tx)


HTML = """<!DOCTYPE html><html lang="hu"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>BoitBlance vezerlo</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c232d;--border:#2d3540;--text:#e6edf3;--muted:#8b949e;--accent:#2ea88a;--accent2:#3fb950;--err:#f85149;--link:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,Segoe UI,Roboto,sans-serif;padding:24px;line-height:1.5}
.wrap{max-width:760px;margin:0 auto}h1{font-size:22px;margin:0 0 2px}.sub{color:var(--muted);font-size:13px;margin:0 0 20px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:16px}
.card h2{font-size:15px;margin:0 0 12px}
.stats{display:flex;gap:12px;flex-wrap:wrap}.stat{flex:1;min-width:90px;background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:12px}
.stat .n{font-size:22px;font-weight:700}.stat .l{font-size:11px;color:var(--muted)}
.usdc{color:var(--accent2)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:10px}
label{display:block;font-size:11px;color:var(--muted);margin-bottom:3px}
input{background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:8px 10px;font-size:14px;width:110px;font-family:inherit}
input.wide{width:240px}
button{background:var(--accent);color:#06120e;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer}
button:hover{background:var(--accent2)}button:disabled{opacity:.5}
button.danger{background:var(--err);color:#fff}
#log{background:#0a0e13;border:1px solid var(--border);border-radius:8px;padding:12px;font-family:ui-monospace,Menlo,monospace;font-size:12px;min-height:60px;max-height:240px;overflow:auto;white-space:pre-wrap}
a{color:var(--link)}.muted{color:var(--muted)}
</style></head><body><div class="wrap">
<h1>BoitBlance vezerlo</h1>
<p class="sub">Gombnyomasra inditott on-chain muveletek a sajat szerzodeseiden (Arc Testnet)</p>

<div class="card"><h2>Allapot <button onclick="refresh()" style="float:right">Frissites</button></h2>
<div class="stats" id="stats"><span class="muted">Betoltes...</span></div></div>

<div class="card"><h2>1. AgentBond - kaucio</h2>
<div class="row"><div><label>Kaucio (USDC)</label><input id="bondAmt" value="5"></div>
<button onclick="act('bond',{amount:val('bondAmt')})">Kaucio letetele (ugynok)</button></div>
<div class="row"><div><label>Lekotes (USDC)</label><input id="lockAmt" value="2"></div>
<button onclick="act('lock',{amount:val('lockAmt')})">Lekotes (megbizo)</button></div>
<div class="row"><div><label>Obligation ID</label><input id="oblId" value="0"></div>
<button onclick="act('release',{id:val('oblId')})">Felszabaditas</button>
<button class="danger" onclick="act('slash',{id:val('oblId')})">Slash (bukja)</button></div></div>

<div class="card"><h2>2. StreamPay - folyamatos fizetes</h2>
<div class="row"><div><label>Osszeg (USDC)</label><input id="strAmt" value="3"></div>
<div><label>Idotartam (mp)</label><input id="strSec" value="60"></div>
<button onclick="act('stream',{amount:val('strAmt'),seconds:val('strSec')})">Stream nyitasa (megbizo)</button></div>
<div class="row"><div><label>Stream ID</label><input id="strId" value="0"></div>
<button onclick="act('withdraw',{id:val('strId')})">Kivet (ugynok)</button></div></div>

<div class="card"><h2>3. CommitStake - vallalas</h2>
<div class="row"><div><label>Tet (USDC)</label><input id="comAmt" value="2"></div>
<div><label>Cel</label><input class="wide" id="comGoal" value="Elkeszitem a riportot"></div>
<button onclick="act('commit',{amount:val('comAmt'),goal:val('comGoal')})">Vallalas (ugynok)</button></div>
<div class="row"><div><label>Commitment ID</label><input id="comId" value="0"></div>
<button onclick="act('confirm',{id:val('comId')})">Megerosites (ellenor)</button></div></div>

<div class="card"><h2>Naplo</h2><div id="log" class="muted">Keszen all. Kattints egy gombra.</div></div>
</div>
<script>
const val=id=>document.getElementById(id).value.trim();
const logEl=document.getElementById('log');
function logLine(t){ logEl.textContent = "› "+t+"\\n"+logEl.textContent; }
async function refresh(){
  try{ const r=await fetch('/api/status'); const s=await r.json();
    document.getElementById('stats').innerHTML=
      `<div class="stat"><div class="n usdc">${s.freeBond.toFixed(2)}</div><div class="l">szabad kaucio (USDC)</div></div>`+
      `<div class="stat"><div class="n">${s.bonded.toFixed(2)}</div><div class="l">teljes kaucio</div></div>`+
      `<div class="stat"><div class="n">${s.locked.toFixed(2)}</div><div class="l">lekotve</div></div>`+
      `<div class="stat"><div class="n">${s.obligations}</div><div class="l">obligation</div></div>`+
      `<div class="stat"><div class="n">${s.streams}</div><div class="l">stream</div></div>`+
      `<div class="stat"><div class="n">${s.commitments}</div><div class="l">vallalas</div></div>`;
  }catch(e){ document.getElementById('stats').innerHTML='<span class="muted">Nem elerheto</span>'; }
}
async function act(path,body){
  const btns=document.querySelectorAll('button'); btns.forEach(b=>b.disabled=true);
  logLine("Folyamatban: "+path+" ... (ez 10-30 mp lehet)");
  try{
    const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d=await r.json();
    if(d.ok){ logLine("OK: "+d.message+(d.tx?("  "+d.tx):"")); }
    else { logLine("HIBA: "+d.message); }
  }catch(e){ logLine("HIBA: "+e.message); }
  btns.forEach(b=>b.disabled=false); refresh();
}
refresh();
</script></body></html>"""


if __name__ == "__main__":
    print("BoitBlance vezerlo fut: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000)
