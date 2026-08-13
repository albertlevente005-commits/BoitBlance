// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
 * BoitBlance - 3 agentic primitiv, ami penzugyileg megbizhatova teszi az AI-ugynokot.
 * Arc Testnet, USDC-alapu (USDC = 0x3600000000000000000000000000000000000000).
 *
 *  1) AgentBond   - az ugynok USDC-kauciot tesz le; a szabad kaucio a "credit score".
 *                   Egy counterparty lekotheti (obligation), majd felszabaditja vagy slasheli.
 *  2) StreamPay   - USDC folyik masodpercenkent a fogadonak; barmikor kivehetо/leallithato.
 *  3) CommitStake - az ugynok penzt tesz egy vallalasra; egy ellenor megerositi hatarido elott,
 *                   kulonben a tet a kedvezmenyezetthez kerul (slash).
 *
 * Demo, teszthalozatra - nem auditalt, eles hasznalatra nem ajanlott.
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/* ============================================================
 * 1) AGENTBOND - kaucio-alapu bizalom
 * ============================================================ */
contract AgentBond {
    IERC20 public immutable usdc;

    mapping(address => uint256) public bonded;   // teljes letett kaucio agentenkent
    mapping(address => uint256) public locked;   // lekotott (obligation) osszeg agentenkent

    struct Obligation {
        address agent;
        address counterparty;
        uint256 amount;
        uint8 status;            // 0 = aktiv, 1 = felszabaditva, 2 = slashelve
    }
    Obligation[] public obligations;

    event Bonded(address indexed agent, uint256 amount, uint256 newTotal);
    event Withdrawn(address indexed agent, uint256 amount);
    event Locked(uint256 indexed id, address indexed agent, address indexed counterparty, uint256 amount);
    event Released(uint256 indexed id);
    event Slashed(uint256 indexed id, uint256 amount);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function freeBond(address agent) public view returns (uint256) {
        return bonded[agent] - locked[agent];
    }

    function deposit(uint256 amount) external {
        require(amount > 0, "amount=0");
        require(usdc.transferFrom(msg.sender, address(this), amount), "transfer failed");
        bonded[msg.sender] += amount;
        emit Bonded(msg.sender, amount, bonded[msg.sender]);
    }

    function withdraw(uint256 amount) external {
        require(amount <= freeBond(msg.sender), "not enough free bond");
        bonded[msg.sender] -= amount;
        require(usdc.transfer(msg.sender, amount), "transfer failed");
        emit Withdrawn(msg.sender, amount);
    }

    // A counterparty lekot egy szelet az agent szabad kauciojabol egy munka moge.
    function lockObligation(address agent, uint256 amount) external returns (uint256 id) {
        require(amount <= freeBond(agent), "agent: not enough free bond");
        locked[agent] += amount;
        obligations.push(Obligation(agent, msg.sender, amount, 0));
        id = obligations.length - 1;
        emit Locked(id, agent, msg.sender, amount);
    }

    function release(uint256 id) external {
        Obligation storage o = obligations[id];
        require(msg.sender == o.counterparty, "only counterparty");
        require(o.status == 0, "not active");
        o.status = 1;
        locked[o.agent] -= o.amount;
        emit Released(id);
    }

    // Az agent nem teljesitett -> a lekotott kaucio a counterparty-hoz kerul.
    function slash(uint256 id) external {
        Obligation storage o = obligations[id];
        require(msg.sender == o.counterparty, "only counterparty");
        require(o.status == 0, "not active");
        o.status = 2;
        locked[o.agent] -= o.amount;
        bonded[o.agent] -= o.amount;
        require(usdc.transfer(o.counterparty, o.amount), "transfer failed");
        emit Slashed(id, o.amount);
    }

    function obligationCount() external view returns (uint256) {
        return obligations.length;
    }
}

/* ============================================================
 * 2) STREAMPAY - folyamatos USDC fizetes masodpercenkent
 * ============================================================ */
contract StreamPay {
    IERC20 public immutable usdc;

    struct Stream {
        address sender;
        address recipient;
        uint256 deposit;
        uint256 startTime;
        uint256 stopTime;
        uint256 withdrawn;
        bool active;
    }
    Stream[] public streams;

    event StreamCreated(uint256 indexed id, address indexed sender, address indexed recipient, uint256 deposit, uint256 stopTime);
    event Withdraw(uint256 indexed id, address indexed recipient, uint256 amount);
    event Cancelled(uint256 indexed id, uint256 toRecipient, uint256 toSender);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function createStream(address recipient, uint256 deposit, uint256 durationSec) external returns (uint256 id) {
        require(recipient != address(0) && recipient != msg.sender, "bad recipient");
        require(deposit > 0 && durationSec > 0, "bad params");
        require(usdc.transferFrom(msg.sender, address(this), deposit), "transfer failed");
        streams.push(Stream(msg.sender, recipient, deposit, block.timestamp, block.timestamp + durationSec, 0, true));
        id = streams.length - 1;
        emit StreamCreated(id, msg.sender, recipient, deposit, block.timestamp + durationSec);
    }

    // Mennyi USDC "erett be" eddig a fogadonak (a teljes letetbol).
    function vestedAmount(uint256 id) public view returns (uint256) {
        Stream storage s = streams[id];
        if (block.timestamp <= s.startTime) return 0;
        if (block.timestamp >= s.stopTime) return s.deposit;
        uint256 elapsed = block.timestamp - s.startTime;
        uint256 total = s.stopTime - s.startTime;
        return (s.deposit * elapsed) / total;
    }

    // Amit a fogado most kivehet.
    function recipientBalance(uint256 id) public view returns (uint256) {
        return vestedAmount(id) - streams[id].withdrawn;
    }

    function withdraw(uint256 id, uint256 amount) external {
        Stream storage s = streams[id];
        require(s.active, "inactive");
        require(msg.sender == s.recipient, "only recipient");
        require(amount <= recipientBalance(id), "exceeds available");
        s.withdrawn += amount;
        require(usdc.transfer(s.recipient, amount), "transfer failed");
        emit Withdraw(id, s.recipient, amount);
    }

    // Barmelyik fel leallithatja: a fogado megkapja a beerettet, a kuldo a maradekot.
    function cancelStream(uint256 id) external {
        Stream storage s = streams[id];
        require(s.active, "inactive");
        require(msg.sender == s.sender || msg.sender == s.recipient, "not party");
        uint256 toRecipient = recipientBalance(id);
        uint256 toSender = s.deposit - vestedAmount(id);
        s.active = false;
        s.withdrawn = s.deposit; // lezarva
        if (toRecipient > 0) require(usdc.transfer(s.recipient, toRecipient), "r transfer failed");
        if (toSender > 0) require(usdc.transfer(s.sender, toSender), "s transfer failed");
        emit Cancelled(id, toRecipient, toSender);
    }

    function streamCount() external view returns (uint256) {
        return streams.length;
    }
}

/* ============================================================
 * 3) COMMITSTAKE - vallalas zalogba teve, ellenorrel
 * ============================================================ */
contract CommitStake {
    IERC20 public immutable usdc;

    struct Commitment {
        address staker;
        address verifier;
        address beneficiary;
        uint256 amount;
        uint256 deadline;
        uint8 status;            // 0 = nyitott, 1 = teljesitve, 2 = slashelve
        string goal;
    }
    Commitment[] public commitments;

    event Committed(uint256 indexed id, address indexed staker, address indexed verifier, uint256 amount, uint256 deadline, string goal);
    event Confirmed(uint256 indexed id);
    event Slashed(uint256 indexed id, address beneficiary, uint256 amount);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    function createCommitment(address verifier, address beneficiary, uint256 deadline, uint256 amount, string calldata goal)
        external returns (uint256 id)
    {
        require(verifier != address(0) && beneficiary != address(0), "bad addr");
        require(deadline > block.timestamp, "deadline in past");
        require(amount > 0, "amount=0");
        require(usdc.transferFrom(msg.sender, address(this), amount), "transfer failed");
        commitments.push(Commitment(msg.sender, verifier, beneficiary, amount, deadline, 0, goal));
        id = commitments.length - 1;
        emit Committed(id, msg.sender, verifier, amount, deadline, goal);
    }

    // Az ellenor megerositi a teljesitest (hatarido elott) -> a tet visszajar a stakelonek.
    function confirm(uint256 id) external {
        Commitment storage c = commitments[id];
        require(msg.sender == c.verifier, "only verifier");
        require(c.status == 0, "not open");
        require(block.timestamp <= c.deadline, "deadline passed");
        c.status = 1;
        require(usdc.transfer(c.staker, c.amount), "transfer failed");
        emit Confirmed(id);
    }

    // Hatarido utan, ha nem lett megerositve -> barki kivaltja, a tet a kedvezmenyezetthez kerul.
    function slash(uint256 id) external {
        Commitment storage c = commitments[id];
        require(c.status == 0, "not open");
        require(block.timestamp > c.deadline, "deadline not passed");
        c.status = 2;
        require(usdc.transfer(c.beneficiary, c.amount), "transfer failed");
        emit Slashed(id, c.beneficiary, c.amount);
    }

    function commitmentCount() external view returns (uint256) {
        return commitments.length;
    }
}
