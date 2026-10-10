const { Connection, PublicKey } = require('@solana/web3.js');

const RPC_ENDPOINTS = [
    'https://api.mainnet-beta.solana.com',
    'https://public.rpc.solanavibestation.com',
    'https://solana.api.pocket.network'
];

const PROGRAM_ID = new PublicKey('7rAgHPLDc9NryZmNdeEzyDui6D9PHkvTxMjKhNSa7w3a');
const TOKEN_MINT = new PublicKey('ApZuxdpzMrbEYTGEzeY9afh5pj9d6qPRJCTgQYiipbKg');
const TOKEN_PROGRAM_ID = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const ASSOCIATED_TOKEN_PROGRAM_ID = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');
const POLL_DISCRIMINATOR = '5Qpj1hsHT4k';

function getOptionATA(pollIdBytes, optionIndex) {
    const [optionPDA] = PublicKey.findProgramAddressSync(
        [Buffer.from('option'), pollIdBytes, Buffer.from([optionIndex])],
        PROGRAM_ID
    );
    const [ata] = PublicKey.findProgramAddressSync(
        [optionPDA.toBuffer(), TOKEN_PROGRAM_ID.toBuffer(), TOKEN_MINT.toBuffer()],
        ASSOCIATED_TOKEN_PROGRAM_ID
    );
    return ata;
}

class BinaryReader {
    constructor(buf) {
        this.buf = buf;
        this.offset = 0;
    }
    readI64() {
        const val = this.buf.readBigInt64LE(this.offset);
        this.offset += 8;
        return Number(val);
    }
    readU32() {
        const val = this.buf.readUInt32LE(this.offset);
        this.offset += 4;
        return val;
    }
    readBytes(len) {
        const slice = this.buf.subarray(this.offset, this.offset + len);
        this.offset += len;
        return slice;
    }
    readString() {
        const len = this.readU32();
        const str = this.readBytes(len).toString('utf8');
        return str;
    }
    readVecString() {
        const count = this.readU32();
        const arr = [];
        for (let i = 0; i < count; i++) {
            arr.push(this.readString());
        }
        return arr;
    }
    readVecBool() {
        const count = this.readU32();
        const arr = [];
        for (let i = 0; i < count; i++) {
            arr.push(this.buf.readUInt8(this.offset) === 1);
            this.offset += 1;
        }
        return arr;
    }
    readVecU64() {
        const count = this.readU32();
        const arr = [];
        for (let i = 0; i < count; i++) {
            arr.push(this.buf.readBigUInt64LE(this.offset));
            this.offset += 8;
        }
        return arr;
    }
}

function decodePoll(raw) {
    try {
        const r = new BinaryReader(raw.subarray(8));
        const authority = r.readBytes(32);
        const timestamp = r.readI64();
        const pollId = r.readBytes(32);
        const title = r.readString();
        const choices = r.readVecString();
        const endsAt = r.readI64();
        const isFinalized = r.readVecBool();
        let finalBalances = [];
        if (raw.length - r.offset >= 4) {
            try { finalBalances = r.readVecU64(); } catch (e) {}
        }
        return { timestamp, pollId, title, choices, endsAt, isFinalized, finalBalances };
    } catch (e) {
        return null;
    }
}

async function getLivePoll() {
    let connection = new Connection(RPC_ENDPOINTS[0], 'confirmed');
    let accounts;
    try {
        accounts = await connection.getProgramAccounts(PROGRAM_ID, {
            filters: [{ memcmp: { offset: 0, bytes: POLL_DISCRIMINATOR } }]
        });
    } catch (e) {
        connection = new Connection(RPC_ENDPOINTS[1], 'confirmed');
        accounts = await connection.getProgramAccounts(PROGRAM_ID, {
            filters: [{ memcmp: { offset: 0, bytes: POLL_DISCRIMINATOR } }]
        });
    }

    const now = Math.floor(Date.now() / 1000);
    const polls = [];

    for (const acc of accounts) {
        const p = decodePoll(acc.account.data);
        if (!p) continue;
        polls.push(p);
    }

    polls.sort((a, b) => b.timestamp - a.timestamp);
    const currentPoll = polls[0];
    if (!currentPoll) {
        console.log(JSON.stringify(null));
        return;
    }

    const isEnded = now >= currentPoll.endsAt;
    const remSec = Math.max(0, currentPoll.endsAt - now);
    const h = Math.floor(remSec / 3600);
    const m = Math.floor((remSec % 3600) / 60);
    const countdown = isEnded ? 'Expiré' : `${h}h ${m}m`;

    const balances = [];
    let total = 0n;

    for (let i = 0; i < currentPoll.choices.length; i++) {
        const ata = getOptionATA(currentPoll.pollId, i);
        let bal = 0n;
        try {
            const resp = await connection.getTokenAccountBalance(ata);
            bal = BigInt(resp.value.amount);
        } catch (e) {}
        balances.push(bal);
        total += bal;
    }

    const choices = currentPoll.choices.map((c, i) => {
        const pct = total > 0n ? Number((balances[i] * 10000n) / total) / 100 : 0.0;
        const uiAmount = Number(balances[i]) / 1e9;
        return {
            choice: c,
            pct: Number(pct.toFixed(1)),
            amount: uiAmount
        };
    });

    const result = {
        title: currentPoll.title,
        status: isEnded ? 'Terminé' : 'En cours',
        countdown,
        ends_at: currentPoll.endsAt,
        total_donated: (Number(total) / 1e9).toFixed(2),
        choices
    };

    console.log(JSON.stringify(result));
}

getLivePoll().catch(err => {
    console.error(err);
    process.exit(1);
});
