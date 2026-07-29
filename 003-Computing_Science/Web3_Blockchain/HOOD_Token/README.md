# HOOD Token — Neighborhood Blockchain Hub

## Contract Addresses (Sepolia Testnet)

| Contract | Address |
|----------|---------|
| HoodToken (HOOD) | `0xd1FB5Cc32160957298E702B0a5dC53CD33E3F916` |
| HoodTimelock | `0x3dcC64c79c22045608dE3775419112F26c557264` |
| HoodGovernor | `0x7f5a904582921a1Fa49b9765f0F38641433C7A10` |
| Admin Wallet | `0x312fC758b9e6C7F38Ee3E8563B45a9937eaf59B4` |
| Deploy TX | `0xb976d0e94b20455378aef7a757b71682199bc673acf22fd4c3574581341d9bd3` |

## Tokenomics — 100M HOOD Total

| Allocation | Amount | Location | Purpose |
|------------|--------|----------|---------|
| Community Reward Pool | 40M HOOD | Contract (self) | Earn-by-learning, referrals, jobs |
| Liquidity Pool | 20M HOOD | Admin wallet | DEX trading liquidity |
| Team/Advisors | 15M HOOD | Admin wallet | 2yr vesting |
| Ecosystem Fund | 15M HOOD | Admin wallet | Partnerships, grants |
| Airdrop Reserve | 10M HOOD | Contract (self) | Free claims, promotions |

## Smart Contract Features

- **ERC-20** with burnable + votes (governance)
- **AccessControl**: DEFAULT_ADMIN_ROLE, COMMUNITY_ROLE, BRIDGE_ROLE
- **Capped supply**: 100M max, enforced in `_update()`
- **Community rewards**: `rewardCommunityMember()` — COMMUNITY_ROLE only, draws from 40M pool
- **Airdrop claims**: `claimAirdrop()` — COMMUNITY_ROLE only, draws from 10M pool
- **Bridge minting**: `bridgeMint()` — BRIDGE_ROLE only, for multichain expansion
- **Timelock**: 2-day delay on governance proposals
- **Governor**: 5% quorum, 1-day voting period, 1-block delay

## Private Key & Wallet

- Wallet: `0x312fC758b9e6C7F38Ee3E8563B45a9937eaf59B4`
- Private key: stored in `.env` as `WEB3_PRIVATE_KEY`
- ETH balance (Sepolia): ~0.08 ETH (gas money)
- HOOD balance: 50M (admin allocation)

## Earning HOOD (No Buying Required)

| Action | HOOD Reward |
|--------|-------------|
| Join the Hood | 5 |
| Week 1: What is Blockchain? | 5 |
| Week 2: Wallets & Security | 10 |
| Week 3: Bitcoin Basics | 10 |
| Week 4: Ethereum & Smart Contracts | 15 |
| Week 5: DeFi Basics | 20 |
| Week 6: Security & Scams | 25 |
| Week 7: DAOs & Governance | 30 |
| Week 8: Building Track | 50 |
| Attend a meetup | 10 |
| Refer a member | 25 |
| Build a project | 50-500 |
| Create content | 100-1000 |

## Infrastructure

| Service | Port | Status |
|---------|------|--------|
| Website (hoodtoken.io) | 8130 | Running |
| API endpoints | 8130 | /api/status, /api/members, /api/join |
| Telegram bot | N/A | Needs BotFather token |
| DB | /home/allenai/data/hood_token.db | Active |
| SSO | Integrated with CC (8090) | Active |

## File Locations

- Contracts: `/home/allenai/hood_token/contracts/`
- Deployed ABIs: `/home/allenai/hood_token/deployed/`
- Web server: `/home/allenai/hood_token/website/hood_web_server.py`
- Landing page: `/home/allenai/hood_token/website/index.html`
- Telegram bot: `/home/allenai/hood_token/bot/hood_tg_bot.py`
- DB: `/home/allenai/data/hood_token.db`
- API (standalone): `/home/allenai/scripts/hood_api.py`

## Transfer Status

- [ ] 50M admin tokens need distribution plan (liquidity pool, team vesting, ecosystem)
- [ ] 50M contract tokens (community + airdrop) distributed via smart contract functions
- [ ] Telegram bot needs BotFather token
- [ ] Mainnet deployment (after testnet validation)