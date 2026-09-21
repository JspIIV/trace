# Trace

**Register a work as your own, and let a challenge check it against an earlier source.** An originality primitive for GenLayer, with a live register.

Claiming a public page as your original work is cheap, and on its own it proves nothing: the same words can be registered by whoever posts them, copied or not. Trace makes the claim answerable. A challenger names an earlier public page the work is said to be taken from, and the contract fetches both pages itself and a round of GenLayer validators reads them and decides whether the registered work reproduces the earlier one or stands on its own.

## How it works

1. **`register(work_url, title)`** — an author claims a public page as their own original. Bound to `gl.message.sender_address`. It starts `REGISTERED` and proves nothing yet.
2. **`challenge(work_id, prior_url)`** — open to anybody. It names an earlier page the work is said to be copied from. The contract **fetches both pages** and a GenLayer round decides `COPY` / `INDEPENDENT` / `UNCLEAR`. `COPY` flags the registration, `INDEPENDENT` clears it, and the verdict accrues to the registrant.
3. **`record(address)`** — the author's originality track record: registrations cleared and flagged, each judged from two public pages, not from their own account of themselves.

Reads: `status(id)`, `get(id)`, `size()`, `page(start, count)`.

## Why it needs GenLayer

Whether one page reproduces another is a judgement over real-world text that no ordinary contract can make and no single referee should be trusted with. GenLayer validators each fetch both pages and reach consensus on one categorical field; the record is built from the evidence the contract read, not from an accusation.

## What it refuses

- **Never flags on an accusation alone.** A challenge runs a round over the two actual pages; only a verdict that the work reproduces the earlier source flags it.
- **Never decides on silence.** If either page cannot be read the verdict is `UNCLEAR`; the registration stays open and can be challenged again.
- **Binds each actor to the caller.** The registrant is the caller of `register`, the challenger the caller of `challenge`; nobody is credited or flagged for a claim they did not make.

## Live

- **Contract (GenLayer Asimov):** `0x8bdB1e4Da7dfef1018950295Cb51B406B84bab67`
- Explorer: https://explorer-asimov.genlayer.com/address/0x8bdB1e4Da7dfef1018950295Cb51B406B84bab67
- **App:** https://jspiiv.github.io/trace/ — reads the register from chain without a wallet; registering and challenging are transactions on Asimov.

## Proven on Asimov

`scripts/prove.mjs`, `results/proved.json`. Three registrations against the pages in `docs/`:
- a work that reproduces an earlier essay (`copy-derivative.txt` vs `original-essay.txt`), challenged → **COPY**, and the registrant's `record` gains a flagged.
- an independent work (`independent-note.txt`) challenged against the same essay → **INDEPENDENT**, and the registrant's `record` gains a cleared.
- a challenge naming an unreadable earlier page → `UNCLEAR`, and the registration stays `REGISTERED`.

## Try it

Browse the live app, or from the CLI:

```
genlayer call 0x8bdB1e4Da7dfef1018950295Cb51B406B84bab67 size
genlayer call 0x8bdB1e4Da7dfef1018950295Cb51B406B84bab67 get --args '"0"'
```

Reproduce: `AT=0x8bdB1e4Da7dfef1018950295Cb51B406B84bab67 PADV=<pw> PPUB=<pw> node scripts/prove.mjs` (after `npm i`).

## Where it stops, plainly

It judges whether one page reproduces another, not who authored either first, so name an earlier source a challenger can point to, not a private draft. Two independent works on the same subject can read alike; the round is asked for reproduction, not resemblance, but a loose judgement is possible. It records a signal, not a court ruling.

## Licence

AGPL-3.0-or-later.
