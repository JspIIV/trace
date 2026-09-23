"""The anti-gaming rules of the challenge flow, exercised through the real methods.

A steward pointed out that the first version let an author self-challenge against an
unrelated page to permanently clear a work, inflate a reputation, and block later
evidence. Testing the helpers alone would not prove the fix, so trace.py is loaded
against a stub of the runtime, a real Trace is built, and the assertions go through
register() and challenge(). The stub controls the two things the contract cannot: the
pages the round fetches and the verdict it returns.

Covers the cases the steward named: self-challenge, malicious early clearing, later
valid evidence after a no-op challenge, and mutable pages (history is preserved as the
pages change), plus the consistency of unrelated and unreadable handling.

    python tests/trace_rules.py
"""

import io
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "..", "contracts", "trace.py")


class _Store:
    def __init__(self, kind): self.kind = kind
    def __class_getitem__(cls, item): return cls("map" if isinstance(item, tuple) else "list")
    def make(self): return {} if self.kind == "map" else []


class _Address:
    def __init__(self, hex_value): self.as_hex = hex_value
    def __str__(self): return str(self.as_hex)


class _Message:
    def __init__(self):
        self.sender_address = _Address("0x" + "0" * 40)
        self.value = 0


class _Web:
    """Pages the contract fetches. `pages[url]` overrides a URL; a value of None makes
    render() raise, standing in for an unreadable page. Anything else gets `default`."""
    def __init__(self):
        self.pages = {}
        self.default = "some ordinary page text"

    def render(self, url):
        if url in self.pages:
            val = self.pages[url]
            if val is None:
                raise RuntimeError("could not fetch")
            return val
        return self.default


class _Nondet:
    def __init__(self, web):
        self.web = web
        self.last_prompt = None
        self.answer = "{}"

    def exec_prompt(self, task):
        self.last_prompt = task
        return self.answer


class _Write:
    def __call__(self, fn): return fn
    def payable(self, fn): return fn


class _PublicNS:
    def __init__(self):
        self.write = _Write()
        self.view = lambda fn: fn


class _EqPrinciple:
    def prompt_comparative(self, run, principle=None): return run()


class _GL:
    def __init__(self):
        self.Contract = object
        self.public = _PublicNS()
        self.message = _Message()
        self.nondet = _Nondet(_Web())
        self.eq_principle = _EqPrinciple()


def load():
    gl = _GL()
    fake = types.ModuleType("genlayer")
    fake.gl = gl
    fake.DynArray = _Store
    fake.TreeMap = _Store
    fake.u32 = int
    fake.u256 = int
    fake.Address = _Address
    sys.modules["genlayer"] = fake
    module = types.ModuleType("trace_under_test")
    exec(compile(io.open(CONTRACT, encoding="utf-8").read(), CONTRACT, "exec"), module.__dict__)
    return module, gl


def fresh(module):
    contract = module.Trace.__new__(module.Trace)
    for field, declared in module.Trace.__annotations__.items():
        setattr(contract, field, declared.make())
    contract.__init__()
    return contract


RESULTS = []


def check_(label, condition):
    RESULTS.append((label, bool(condition)))
    print(("  ok  " if condition else " FAIL "), label)


AUTHOR = "0x1111111111111111111111111111111111111111"
OTHER = "0x2222222222222222222222222222222222222222"

WORK = "https://example.org/my-essay"
UNRELATED = "https://example.org/rainwater"
REAL_SOURCE = "https://example.org/the-original"


def answer(verdict, earlier="UNKNOWN", a_date="", b_date="", quote="q", reason="r", reproduces="UNCLEAR"):
    return json.dumps({"verdict": verdict, "reproduces": reproduces, "earlier": earlier,
                       "a_date": a_date, "b_date": b_date, "quote": quote, "reason": reason})


def main():
    module, gl = load()

    def as_(address): gl.message.sender_address = _Address(address)

    # ---- the pure rule the flow is built on ----
    print("only a COPY verdict changes anything")
    check_("COPY flags the work and adds a flag", module._status_after("COPY") == ("FLAGGED", 1))
    check_("INDEPENDENT changes nothing", module._status_after("INDEPENDENT") == ("REGISTERED", 0))
    check_("UNCLEAR changes nothing, exactly like INDEPENDENT", module._status_after("UNCLEAR") == ("REGISTERED", 0))

    print("\nregistering a work")
    c = fresh(module)
    as_(AUTHOR)
    reg = json.loads(c.register(WORK, "My Essay"))
    wid = reg["id"]
    check_("a work registers as REGISTERED", reg["ok"] and reg["status"] == "REGISTERED")
    check_("the author's record counts the work, with no flag",
           json.loads(c.record(AUTHOR)) == {"exists": True, "address": AUTHOR, "works": 1, "flagged": 0})
    check_("challenging with the same page as the work is refused",
           not json.loads(c.challenge(wid, WORK))["ok"])

    print("\nan author cannot self-clear against an unrelated page")
    as_(AUTHOR)  # the author challenges their own work
    gl.nondet.answer = answer("INDEPENDENT", earlier="UNKNOWN", quote="unrelated", reason="different subjects")
    self_ch = json.loads(c.challenge(wid, UNRELATED))
    check_("a self-challenge is allowed but recorded as self", self_ch["ok"] and self_ch["self"] is True)
    check_("an INDEPENDENT verdict does not clear the work; it stays REGISTERED",
           json.loads(c.status(wid))["status"] == "REGISTERED")
    check_("and earns the author no reputation (still no flag, no positive count)",
           json.loads(c.record(AUTHOR)) == {"exists": True, "address": AUTHOR, "works": 1, "flagged": 0})
    check_("the work is still open to challenge", json.loads(c.get(wid))["status"] == "REGISTERED")

    print("\nlater valid evidence still flags the work despite the earlier no-op")
    as_(OTHER)
    gl.nondet.answer = answer("COPY", earlier="B", a_date="2025-03-01", b_date="2024-01-01",
                              quote="identical passage", reason="A reproduces the earlier B, dated 2024 before A's 2025")
    real = json.loads(c.challenge(wid, REAL_SOURCE))
    check_("a real earlier source produces COPY and flags the work", real["ok"] and real["status"] == "FLAGGED")
    check_("the author's record now shows one flagged work",
           json.loads(c.record(AUTHOR)) == {"exists": True, "address": AUTHOR, "works": 1, "flagged": 1})
    hist = json.loads(c.history(wid))
    check_("both challenges are preserved in history, oldest first",
           len(hist["log"]) == 2 and hist["log"][0]["verdict"] == "INDEPENDENT" and hist["log"][1]["verdict"] == "COPY")
    check_("the flagging challenge bound the dates and order as evidence",
           hist["log"][1]["earlier"] == "B" and hist["log"][1]["b_date"] == "2024-01-01" and hist["log"][1]["a_date"] == "2025-03-01")
    check_("a flagged work cannot be challenged again", not json.loads(c.challenge(wid, REAL_SOURCE))["ok"])

    print("\nunrelated and unreadable pages are handled the same: no evidence")
    as_(AUTHOR)
    w2 = json.loads(c.register(WORK + "/2", "Second Essay"))["id"]
    gl.nondet.answer = answer("INDEPENDENT", reason="unrelated")
    c.challenge(w2, UNRELATED)
    after_unrelated = json.loads(c.status(w2))["status"]
    gl.nondet.web.pages[REAL_SOURCE] = None  # this source is now unreadable
    unread = json.loads(c.challenge(w2, REAL_SOURCE))
    check_("an unreadable page yields UNCLEAR", unread["verdict"] == "UNCLEAR")
    check_("unrelated and unreadable both leave the work REGISTERED",
           after_unrelated == "REGISTERED" and json.loads(c.status(w2))["status"] == "REGISTERED")
    check_("neither moved the author's reputation",
           json.loads(c.record(AUTHOR)) == {"exists": True, "address": AUTHOR, "works": 2, "flagged": 1})
    gl.nondet.web.pages.pop(REAL_SOURCE, None)

    print("\nmutable pages: history preserves the evidence from each challenge as pages change")
    as_(AUTHOR)
    w3 = json.loads(c.register("https://example.org/mut", "Mutable"))["id"]
    gl.nondet.web.pages["https://example.org/mut"] = "first version, benign text"
    gl.nondet.answer = answer("INDEPENDENT", quote="benign first-version passage", reason="looked independent at first")
    c.challenge(w3, UNRELATED)
    first_quote = json.loads(c.history(w3))["log"][0]["quote"]
    gl.nondet.web.pages["https://example.org/mut"] = "second version, now clearly copied text"
    gl.nondet.answer = answer("COPY", earlier="B", a_date="2025-05-01", b_date="2024-02-02",
                              quote="second-version copied passage", reason="now reproduces the earlier source")
    c.challenge(w3, REAL_SOURCE)
    log3 = json.loads(c.history(w3))["log"]
    check_("each challenge over a changed page is appended, not overwritten", len(log3) == 2)
    check_("the first challenge's cited evidence is preserved unchanged",
           log3[0]["quote"] == first_quote == "benign first-version passage")
    check_("the second challenge records its own evidence", log3[1]["quote"] == "second-version copied passage")
    check_("the work is flagged on the later, dated evidence", json.loads(c.status(w3))["status"] == "FLAGGED")

    print("\nno unrelated comparison ever inflated a clean record")
    reg_final = json.loads(c.record(AUTHOR))
    check_("the author has three works and exactly two proven copies",
           reg_final["works"] == 3 and reg_final["flagged"] == 2)
    check_("a stranger with no registrations has an empty record",
           json.loads(c.record("0x3333333333333333333333333333333333333333")) ==
           {"exists": False, "address": "0x3333333333333333333333333333333333333333", "works": 0, "flagged": 0})

    failed = [label for label, ok in RESULTS if not ok]
    print()
    if failed:
        print("%d of %d checks failed" % (len(failed), len(RESULTS)))
        return 1
    print("%d checks, all through register() and challenge() on a real Trace, the flag un-gameable"
          % len(RESULTS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
