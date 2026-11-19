# TapeOut integration, phase 1

## Rule and deployed dependency

Decision Check reuses the author's Money Lab processor 0x4f3b708af365b8f339dd35a8985ffe06c2553400 on X Layer (196), circuit #49 (49.2.167). It is AND3 through four native REF calls to NAND #48. No new circuit, processor, container, wallet connection or transaction is required.

Call #49 with [Wyckoff valid, SMC valid, Portfolio valid], then [Wyckoff pass, SMC pass, Portfolio pass], then [validity output, conditions output, 1]. The result equals the six-input AND. The input order and exact packed calldata are recorded.

Before accepting a result the client pins a block number/hash, checks chain ID, both circuits' metadata and exact netlists, verifies the proxy's ERC-1967 beacon pointer, reads the beacon implementation/code and checks #48's four and #49's eight truth-table cases at that block. Three actual decision calls are then made. The final block hash must be unchanged. No RPC or semantic failure falls back to a verified local result.

## Receipt and replay

The exported analysis includes a separate `tapeout` receipt: supplied bits, hashes of portfolio/market source inputs, rules, engine version, analysis time, block tag/hash, implementation/code, circuit and REF netlists, calldata/raw outputs, truth table, three-stage results and receipt SHA-256. The SHA is content integrity, not a signature or chain storage proof. A malicious RPC is not excluded by one-provider reads.

`verify.html` imports an exported report or receipt locally, checks the hash and rereads the same block. Historical state may require an archive RPC; failure means not verified, not automatically fraudulent. New current-state analysis requires new agent data rather than replaying old decisions as live advice.

The circuit checks supplied Boolean composition only. It does not validate Wyckoff/SMC interpretation, authenticate account data, calculate all risk quantities, execute trades, or put the private portfolio onchain. Only circuit inputs (bits) are sent to the public RPC. Local agent results remain clearly separate.

## Phase 2 numeric cash-safety draft

`circuits/cash-safety.mjs` generates a TAP-02 NAND netlist: 24-bit cash cents, 24-bit NAV cents, 14-bit minimum cash basis points. It compares cash × 10000 >= NAV × basis points with 38-bit products, and gates the answer on NAV > 0, cash <= NAV and basis points <= 10000. Inputs are exact cents, with no silent rounding; maximum NAV is USD 167772.15. Output bits are valid then pass.

The generated JSON is NOT_DEPLOYED. Measure target-chain gas, fee, transistor requirements and viable transaction size before proposing a publication. Gate count is 6106, netlist size 42742 bytes; do not assume low-cost execution. No numeric onchain verification is claimed yet.

## Tests and sources

Run `node --test tests/tapeout.test.mjs`. It covers all 64 input combinations, receipts/replay/tampering, wrong chain, changed design, reorg, missing data and RPC errors, plus exact arithmetic boundaries/random vectors. Live observations are separate from mocked transport tests.

TAP-02 draft: https://github.com/TapeOutProtocol/TAPs/blob/main/TAPs/TAP-02.md
Money Lab deployment: https://github.com/superfual/money-lab-hub/blob/main/docs/ref-deployment.md

Netlist encoding/ABI must also be checked against the live X Layer contracts; the TAP-02 draft's historical verified-source claims focus on BNB Chain.

## Observed read-only test

The synthetic all-true integration vector was read from X Layer block `0x48cadd8` (hash `0x758c40646206d03275f58e381f68df38bf2d2c1b67f941b1f1afb1ec540ca161`). Native output was 1. Re-reading the same block returned REPLAY_MATCH. `docs/evidence/tapeout-synthetic-live-read.json` contains the raw receipt. This vector is deliberately synthetic; zero/one input hashes are placeholders, not a customer report or a verified investment signal.
