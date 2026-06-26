# Banking-Blockchain Pipeline + Crypto On-Ramp

## Architecture

```
🏦 RELAY DEPOSIT
       │
       ▼
💳 PLAID API (detects transaction)
       │
       ▼ HTTPS POST → plaid.blacktechsolutionscorp.com:8107
🧠 LOGIC GATE (banking_logic_gate.py)
       │  Matches transaction against rules
       │
       ├── SYNC_BANKING → Dewey blockchain log only
       ├── DEPOSIT_MINT → On-chain self-transfer (Sepolia testnet)
       ├── DEPOSIT_ONRAMP → ACH → crypto via MoonPay/ZeroHash/Transak
       └── ALERT_ONLY → Telegram notification only
       │
       ▼
⛓️ OUTPUT
   ├─ Dewey Block (always)
   ├─ Sepolia TX (DEPOSIT_MINT)
   ├─ Crypto Purchase (DEPOSIT_ONRAMP, production only)
   └─ Telegram Alert (always)
```

## Files

| File | Purpose |
|------|---------|
| `/home/allenai/plaid_webhook.py` | FastAPI webhook listener (port 8107) |
| `/home/allenai/banking_logic_gate.py` | Rule matching engine + Web3 signer |
| `/home/allenai/banking_chain_bridge.py` | Dewey blockchain bridge |
| `/home/allenai/banking_trigger_rules.json` | Rule definitions (5 rules) |
| `/home/allenai/crypto_onramp.py` | Multi-provider ACH→crypto on-ramp |
| `/home/allenai/.hermes/profiles/derrell-black/.env` | Keys: WEB3_PRIVATE_KEY, PLAID_*, ONRAMP_* |

## Trigger Rules (5)

1. **relay_deposit** — Relay ACH/direct deposits → SYNC_BANKING
2. **comed_rebate** — ComEd/EESP credits → SYNC_BANKING
3. **think_energy_commission** — Think Energy payments → SYNC_BANKING
4. **large_deposit** — Any deposit ≥$1,000 → DEPOSIT_MINT (on-chain)
5. **crypto_onramp** — Deposits matching "onramp|crypto buy|convert to eth|swap to crypto" → DEPOSIT_ONRAMP

## On-Ramp Providers

| Provider | API Key Env Var | Min | Plaid Token | Status |
|----------|----------------|-----|-------------|--------|
| MoonPay | MOONPAY_API_KEY | $20 | ✅ Required | Default, easiest |
| ZeroHash | ZEROHASH_API_KEY | $1 | ✅ Required | Institutional |
| Transak | TRANSAK_API_KEY | $30 | ❌ Not needed | DeFi-native |

Set `ONRAMP_PROVIDER=moonpay|zerohash|transak` in .env

## Production Activation Steps

1. Apply for provider account (MoonPay recommended first)
2. Complete KYC/business verification
3. Get API keys → add to .env
4. Switch `PLAID_ENV=production` in .env
5. Set `ONRAMP_PROVIDER=moonpay` in .env
6. Restart webhook: kill + `python3 /home/allenai/plaid_webhook.py &`

## Testing

```bash
# Test logic gate with specific rule
python3 /home/allenai/banking_logic_gate.py --test --amount 1500 --desc "Wire Transfer"

# Test on-ramp sandbox
python3 /home/allenai/crypto_onramp.py --test --amount 100 --provider moonpay

# List providers + key status
python3 /home/allenai/crypto_onramp.py --list-providers
```

## Wallet

- Sepolia: 0x312fC758b9e6C7F38Ee3E8563B45a9937eaf59B4
- Balance: ~0.098 ETH (test funds)
- Network: Sepolia (testnet) → upgrade to Base/mainnet for production