# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Trace: a registry that flags a work as a copy, on dated evidence, and can never be self-cleared.

Claiming a public page as your own original is cheap and proves nothing: the same
words can be registered by whoever posts them, copied or not. Trace does not try to
certify originality, because on the open web nobody can prove a negative about
themselves from pages they may control. It does the one thing that can be settled
from evidence: it flags a work as a copy when an earlier source shows it to be one.

An author registers a work. That registration is a claim, and it stays open. Anyone
may challenge it by naming an earlier public page the work is said to be taken from.
The contract fetches both pages and a round of GenLayer validators decides whether
the work reproduces the earlier page AND that the earlier page is in fact the earlier
one, from dates or credit shown on the pages themselves. Only then is the work
flagged. A flag is permanent and it accrues to the registrant.

## What it refuses to be gamed into

A challenge that does not show a copy never clears the work and never earns its
author anything: an unrelated page and an unreadable page are treated the same, as
no evidence, and the work stays open to later, better evidence. So an author cannot
self-challenge against a strawman to lock in a clean record, inflate a reputation, or
block a real challenge that comes afterwards. Originality here is simply the absence
of a proven copy, and that absence can never be manufactured, only left standing.

## What it answers

    record(address) -> works, flagged

for anyone weighing an author's originality claim: how many of their registered works
have been shown, from an earlier dated source, to be copies. A clean record is not a
certificate; it is the fact that nobody has proven otherwise.

## Evidence and history

Every challenge is kept, append-only, in the work's log: who raised it, whether it
was the author challenging their own work, the page named, the verdict, and the dates
and passage the round cited. The pages are fetched live, so the stored quote and dates
are the round's cited evidence at the time it judged; to bind a specific version of a
page, name an archived snapshot as the URL. History is preserved, never overwritten.

## Where it stops, plainly

It judges whether one page reproduces an earlier one, from what the pages show. It
does not see private drafts, and it will not flag on reproduction alone when the pages
give no way to tell which came first: that is left unresolved rather than guessed.
"""

from genlayer import *
import json

COPY = "COPY"
INDEPENDENT = "INDEPENDENT"
UNCLEAR = "UNCLEAR"
VERDICTS = (COPY, INDEPENDENT, UNCLEAR)

REGISTERED = "REGISTERED"
FLAGGED = "FLAGGED"

MAX_TITLE = 200
MAX_URL = 300
MAX_PAGE = 5000
MAX_REASON = 300
MAX_QUOTE = 300
MAX_DATE = 40
MAX_LOG = 50

FETCH_FAILED = "__FETCH_FAILED__"


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _clip(text: str, limit: int) -> str:
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit] + " [...]"


def _addr(value) -> str:
    text = str(value).strip().lower()
    if not text.startswith("0x") or len(text) != 42:
        return ""
    for character in text[2:]:
        if character not in "0123456789abcdef":
            return ""
    return text


def _whole(value) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return -1


def _url_ok(url: str) -> bool:
    text = str(url).strip()
    if len(text) < 8 or len(text) > MAX_URL or " " in text:
        return False
    return text.startswith("https://") or text.startswith("http://")


def _status_after(verdict: str):
    """Map a round verdict to the work's status and the registrant's flagged delta.

    Only COPY, a work shown to reproduce an earlier dated source, ever changes
    anything: it flags the work and adds one to the author's flagged count.
    INDEPENDENT (not a copy of this page) and UNCLEAR (unreadable or undecidable)
    are handled identically, as no evidence: the work stays registered and no
    reputation moves. Kept pure so the anti-gaming rule can be tested on its own.
    Returns (status, flagged_delta).
    """
    if verdict == COPY:
        return FLAGGED, 1
    return REGISTERED, 0


def _field(raw: str, name: str, allowed, fallback: str) -> str:
    try:
        text = str(raw).strip()
        obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
        if isinstance(obj, dict):
            said = str(obj.get(name, "")).strip().upper()
            return said if said in allowed else fallback
    except Exception:
        pass
    return fallback


def _text_field(raw: str, name: str, limit: int) -> str:
    try:
        text = str(raw).strip()
        obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
        if isinstance(obj, dict):
            return _clip(str(obj.get(name, "")), limit)
    except Exception:
        pass
    return ""


def _fetch(url: str) -> str:
    try:
        got = gl.nondet.web.render(url)
        page = got if isinstance(got, str) else getattr(got, "body", "")
        if isinstance(page, (bytes, bytearray)):
            page = page.decode("utf-8", "replace")
        page = _clip(str(page), MAX_PAGE)
        return page if page else FETCH_FAILED
    except Exception:
        return FETCH_FAILED


def _task(title: str, work_page: str, prior_page: str) -> str:
    return f"""PAGE A is a work its author registered as their own original. A challenger says PAGE
A was copied from the earlier PAGE B. Read both pages and decide whether PAGE A is a
copy of PAGE B, using any publication dates or credits shown ON the pages to judge
which one came first.

WHAT THE AUTHOR TITLED PAGE A:
{title}

PAGE A, the registered work:
{work_page}

PAGE B, the earlier source it is said to be copied from:
{prior_page}

Decide one of:
  {COPY} PAGE A substantially reproduces PAGE B (the same text, structure or passages,
    allowing small edits) AND PAGE B is the earlier or original one: a date on the
    pages shows B at or before A, or PAGE A itself credits B as its source. So A is the
    copy.
  {INDEPENDENT} PAGE A does not reproduce PAGE B, OR the pages show that PAGE A is
    itself the earlier or original one, so A is not a copy of B even if they share text.
  {UNCLEAR} a page could not be read, or there is not enough on the pages to tell
    whether A reproduces B, or which of the two came first.

Judge reproduction, not a shared subject: two independent pieces on one topic are
{INDEPENDENT}. Do not answer {COPY} on reproduction alone: if A clearly reproduces B
but nothing on the pages says which came first, answer {UNCLEAR}, not {COPY}. Never
treat an unrelated or unreachable page as proof of anything.

Reply with bare JSON and nothing else:
{{"verdict": "{COPY}" or "{INDEPENDENT}" or "{UNCLEAR}",
  "reproduces": "YES" or "NO" or "UNCLEAR",
  "earlier": "A" or "B" or "UNKNOWN",
  "a_date": "the date shown on PAGE A, or empty",
  "b_date": "the date shown on PAGE B, or empty",
  "quote": "a short passage that decided it, or empty",
  "reason": "one sentence naming what decided it, including which came first"}}"""


class Trace(gl.Contract):
    """Registered works, each flagged only when an earlier dated source shows it to be a copy."""

    # str(id) -> the registration as JSON, including its append-only challenge log.
    items: TreeMap[str, str]
    ids: DynArray[str]
    # address -> {"works": n, "flagged": n} as JSON.
    records: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    def _bump(self, author: str, works_delta: int, flagged_delta: int) -> None:
        rec_raw = self.records.get(author, None)
        rec = json.loads(rec_raw) if rec_raw is not None else {"works": 0, "flagged": 0}
        rec["works"] = int(rec.get("works", 0)) + works_delta
        rec["flagged"] = int(rec.get("flagged", 0)) + flagged_delta
        self.records[author] = json.dumps(rec)

    @gl.public.write
    def register(self, work_url: str, title: str) -> str:
        """Claim a public page as your own original work. Bound to the caller.

        The claim starts REGISTERED and proves nothing on its own. It never becomes
        a certificate of originality; it can only be FLAGGED if a challenge shows it
        to be a copy of an earlier dated source.
        """
        author = gl.message.sender_address.as_hex.lower()
        link = str(work_url).strip()
        name = _clip(title, MAX_TITLE)
        if not _url_ok(link):
            return json.dumps({"ok": False, "error": "give an http(s) URL for the work you are registering"})
        if not name:
            return json.dumps({"ok": False, "error": "give the work a short title"})

        wid = str(len(self.ids))
        record = {
            "id": wid,
            "author": author,
            "registered_at": _now_iso(),
            "title": name,
            "work_url": link,
            "status": REGISTERED,
            "challenges": 0,
            "flag_reason": "",
            "flag_quote": "",
            "flag_prior_url": "",
            "flagged_at": "",
            "log": [],
        }
        self.items[wid] = json.dumps(record)
        self.ids.append(wid)
        self._bump(author, 1, 0)
        return json.dumps({"ok": True, "id": wid, "status": REGISTERED})

    @gl.public.write
    def challenge(self, work_id: str, prior_url: str) -> str:
        """Challenge a registration: name an earlier page it is said to be copied from. Open to anybody.

        The contract fetches both pages inside the round; nobody passes in the verdict.
        A COPY verdict, which the round gives only when the work reproduces the earlier
        page and that page is shown to be the earlier one, flags the work permanently.
        Any other verdict is recorded as no evidence and leaves the work open. Every
        challenge, whatever its verdict, is appended to the work's history.
        """
        challenger = gl.message.sender_address.as_hex.lower()
        wid = str(work_id).strip()
        prior = str(prior_url).strip()
        stored = self.items.get(wid, None)
        if stored is None:
            return json.dumps({"ok": False, "error": "no registration with that id"})
        if not _url_ok(prior):
            return json.dumps({"ok": False, "error": "give an http(s) URL for the earlier source"})
        record = json.loads(stored)
        if record["status"] == FLAGGED:
            return json.dumps({"ok": False, "error": "this work is already flagged as a copy", "status": FLAGGED})
        if prior == record["work_url"]:
            return json.dumps({"ok": False, "error": "the earlier source must be a different page from the work"})

        author = record["author"]
        is_self = challenger == author

        # Copy into locals before the round. Nothing inside the block reads self
        # and nothing inside it raises.
        title = record["title"]
        work_url = record["work_url"]

        def look() -> str:
            work_page = _fetch(work_url)
            prior_page = _fetch(prior)
            if work_page == FETCH_FAILED or prior_page == FETCH_FAILED:
                return json.dumps({"verdict": UNCLEAR, "reproduces": "UNCLEAR", "earlier": "UNKNOWN",
                                   "a_date": "", "b_date": "", "quote": "",
                                   "reason": "one of the two pages could not be read"})
            try:
                return str(gl.nondet.exec_prompt(_task(title, work_page, prior_page)))
            except Exception as error:
                return json.dumps({"verdict": UNCLEAR, "reproduces": "UNCLEAR", "earlier": "UNKNOWN",
                                   "a_date": "", "b_date": "", "quote": "",
                                   "reason": _clip("the prompt failed: " + str(error), MAX_REASON)})

        raw = gl.eq_principle.prompt_comparative(
            look,
            principle=(
                f"Both answers must carry the same value in the field named verdict, one of "
                f"{COPY}, {INDEPENDENT} or {UNCLEAR}. That single field decides whether a work is "
                "flagged as a copy on its author's permanent record, so two readers differing on it "
                "disagree about whether one page reproduces an earlier one, not about how to word a "
                "judgement. The other fields are not compared, and the two readers will not have "
                "fetched byte-identical copies of the pages."
            ),
        )

        verdict = _field(raw, "verdict", VERDICTS, "")
        if not verdict:
            return json.dumps({"ok": False,
                               "error": "the round produced no verdict this contract recognises",
                               "round_said": _clip(str(raw), 400)})

        reason = _text_field(raw, "reason", MAX_REASON)
        quote = _text_field(raw, "quote", MAX_QUOTE)
        entry = {
            "n": int(record.get("challenges", 0)) + 1,
            "at": _now_iso(),
            "challenger": challenger,
            "self": is_self,
            "prior_url": prior,
            "verdict": verdict,
            "earlier": _field(raw, "earlier", ("A", "B", "UNKNOWN"), "UNKNOWN"),
            "a_date": _text_field(raw, "a_date", MAX_DATE),
            "b_date": _text_field(raw, "b_date", MAX_DATE),
            "quote": quote,
            "reason": reason,
        }
        log = list(record.get("log", []))
        log.append(entry)
        if len(log) > MAX_LOG:
            log = log[-MAX_LOG:]
        record["log"] = log
        record["challenges"] = int(record.get("challenges", 0)) + 1

        status, flagged_delta = _status_after(verdict)
        if status == FLAGGED:
            record["status"] = FLAGGED
            record["flagged_at"] = _now_iso()
            record["flag_reason"] = reason
            record["flag_quote"] = quote
            record["flag_prior_url"] = prior
            self._bump(author, 0, flagged_delta)
        # INDEPENDENT and UNCLEAR: no status change, no reputation change; the work
        # stays open to later evidence, and the challenge is preserved in the log.
        self.items[wid] = json.dumps(record)
        return json.dumps({"ok": True, "id": wid, "verdict": verdict, "self": is_self,
                           "status": record["status"], "reason": reason})

    # ------------------------------------------------------------------ reads

    @gl.public.view
    def record(self, address: str) -> str:
        """An author's originality record: works registered, and works flagged as copies."""
        who = _addr(address)
        if not who:
            return json.dumps({"exists": False, "works": 0, "flagged": 0})
        rec_raw = self.records.get(who, None)
        if rec_raw is None:
            return json.dumps({"exists": False, "address": who, "works": 0, "flagged": 0})
        rec = json.loads(rec_raw)
        return json.dumps({"exists": True, "address": who,
                           "works": int(rec.get("works", 0)), "flagged": int(rec.get("flagged", 0))})

    @gl.public.view
    def status(self, work_id: str) -> str:
        """A registration's current standing and how many times it has been challenged."""
        wid = str(work_id).strip()
        stored = self.items.get(wid, None)
        if stored is None:
            return json.dumps({"exists": False})
        record = json.loads(stored)
        return json.dumps({"exists": True, "id": wid, "status": record["status"],
                           "challenges": record["challenges"], "reason": record.get("flag_reason", "")})

    @gl.public.view
    def history(self, work_id: str) -> str:
        """The full, append-only log of every challenge raised against a work."""
        wid = str(work_id).strip()
        stored = self.items.get(wid, None)
        if stored is None:
            return json.dumps({"exists": False})
        record = json.loads(stored)
        return json.dumps({"exists": True, "id": wid, "status": record["status"],
                           "challenges": record["challenges"], "log": record.get("log", [])})

    @gl.public.view
    def get(self, work_id: str) -> str:
        """The whole registration, including its challenge history."""
        wid = str(work_id).strip()
        stored = self.items.get(wid, None)
        if stored is None:
            return json.dumps({"exists": False})
        return stored

    @gl.public.view
    def size(self) -> str:
        """How many registrations are open and how many are flagged as copies."""
        registered = 0
        flagged = 0
        for position in range(len(self.ids)):
            record = json.loads(self.items[self.ids[position]])
            state = record["status"]
            if state == REGISTERED:
                registered += 1
            elif state == FLAGGED:
                flagged += 1
        return json.dumps({"total": len(self.ids), "registered": registered, "flagged": flagged})

    @gl.public.view
    def page(self, start: str, count: str) -> str:
        """A slice of the register, newest first, for a frontend to render."""
        total = len(self.ids)
        begin = _whole(start)
        want = _whole(count)
        if begin < 0:
            begin = 0
        if want < 1:
            want = 20
        if want > 50:
            want = 50
        out = []
        seen = 0
        position = total - 1 - begin
        while position >= 0 and seen < want:
            record = json.loads(self.items[self.ids[position]])
            record["challenge_count"] = len(record.get("log", []))
            record.pop("log", None)
            out.append(record)
            position -= 1
            seen += 1
        return json.dumps({"total": total, "start": begin, "count": len(out), "items": out})
