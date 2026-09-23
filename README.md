# Trace

**A work is flagged as a copy only when an earlier, dated source shows it to be one.** An originality primitive for GenLayer, with a live register.

Claiming a public page as your own original is cheap and proves nothing. Trace does not try to certify originality, because on the open web nobody can prove a negative about themselves from pages they may control. It settles the one thing evidence can: it flags a work as a copy when an earlier, dated source shows it to be one. An author registers a work; anyone can challenge it by naming an earlier page it is said to be taken from; the contract fetches both and a round of GenLayer validators flags the work only if it reproduces the earlier page **and** the pages show that page came first.

## How it works

1. **`register(work_url, title)`** — an author claims a public page as their own original. Bound to `gl.message.sender_address`. It starts `REGISTERED` and is never a certificate; it can only be flagged.
2. **`challenge(work_id, prior_url)`** — open to anybody. It names an earlier page the work is said to be copied from. The contract **fetches both pages** and a GenLayer round returns `COPY` / `INDEPENDENT` / `UNCLEAR`. `COPY` — the work reproduces the earlier page **and** the pages date that page first — flags the work permanently and adds a flag to the author. `INDEPENDENT` and `UNCLEAR` are treated identically, as **no evidence**: nothing is cleared, no reputation moves, the work stays open. Every challenge is appended to the work's history.
3. **`record(address)`** — the author's record: works registered, and works flagged as copies. A clean record is not a certificate; it is the fact that nobody has proven otherwise.

Reads: `status(id)`, `history(id)`, `get(id)`, `size()`, `page(start, count)`.

## Why it cannot be gamed

The first version let an author self-challenge their own work against an unrelated page, take the resulting `INDEPENDENT` as a permanent clear, inflate a reputation, and block later evidence. This version fixes that at the root: only a `COPY` verdict changes anything, and `COPY` requires the pages themselves to show the challenged work is the later, derivative one. An unrelated page and an unreadable page are the same — no evidence — so a strawman challenge can never clear a work or move reputation, and the work stays open to a real challenge that comes afterwards. History is preserved append-only, so nothing is overwritten.

## Why it needs GenLayer

Whether one page reproduces an earlier one, and which came first, is a judgement over real-world text that no ordinary contract can make and no single referee should be trusted with. GenLayer validators each fetch both pages and reach consensus on one categorical field that already folds in the ordering; the record is built from the evidence the contract read, not from an accusation.

## What it refuses

- **Never flags on an accusation alone.** A challenge runs a round over the two actual pages, and `COPY` requires the pages to show the earlier one came first.
- **Never certifies originality.** There is no positive verdict to farm; a work is either open or flagged. A self-challenge against a strawman earns nothing and clears nothing.
- **Treats no-evidence consistently.** An unrelated page (`INDEPENDENT`) and an unreadable page (`UNCLEAR`) both leave the work open and move no reputation.
- **Never blocks later evidence.** Only `COPY` is terminal; any non-flagging challenge leaves the work challengeable again.
- **Binds each actor to the caller and preserves history.** The registrant is the caller of `register`, the challenger of `challenge`; every challenge, including a self-challenge, is kept append-only in the log.

## Live

- **Contract (GenLayer Asimov):** `0x6f92198Cf810413074712d0A064469639BB002f8`
- Explorer: https://explorer-asimov.genlayer.com/address/0x6f92198Cf810413074712d0A064469639BB002f8
- **App:** https://jspiiv.github.io/trace/ — reads the register from chain without a wallet; registering and challenging are transactions on Asimov.

## Proven on Asimov

`scripts/prove.mjs`, `results/proved.json`, against the dated pages in `docs/`:
- a work (`copy-derivative.txt`, dated 2025) that reproduces an earlier essay (`original-essay.txt`, dated 2024) is registered, then its author **self-challenges it against an unrelated page** (`independent-note.txt`) → `INDEPENDENT` → it is **not** cleared, reputation does not move, it stays `REGISTERED`.
- anyone then challenges it against the real earlier source → **COPY** → `FLAGGED`, and only now does the author's `record` gain a flag. The earlier no-op did not block it.
- a challenge naming an unreadable page → `UNCLEAR`, the work stays `REGISTERED`.
- `history(id)` shows every challenge preserved, oldest first.

Deterministic unit tests: `python tests/trace_rules.py` runs the real `register()`/`challenge()` against a runtime stub with the pages and verdict controlled, covering self-challenge, malicious early clearing, later valid evidence, and mutable pages (history preserved as pages change). 24 checks.

## Try it

Browse the live app, or from the CLI:

```
genlayer call 0x6f92198Cf810413074712d0A064469639BB002f8 size
genlayer call 0x6f92198Cf810413074712d0A064469639BB002f8 get --args '"0"'
```

Reproduce: `AT=0x6f92198Cf810413074712d0A064469639BB002f8 PADV=<pw> PPUB=<pw> node scripts/prove.mjs` (after `npm i`).

## Where it stops, plainly

It judges whether one page reproduces an earlier one from what the pages show, so name a source with a visible date or credit, not a private draft. Two independent works on one subject can read alike; the round is asked for reproduction with an ordering, not resemblance, but a loose judgement is possible. The pages are fetched live, so the stored quote and dates are the round's cited evidence at judging time; to bind a specific version, name an archived snapshot as the URL. It records a signal, not a court ruling.

## Licence

AGPL-3.0-or-later.
