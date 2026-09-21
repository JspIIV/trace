# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Trace: register a work as your own, and let a challenge check it against an earlier source.

Anyone can claim a public page as their original work. That claim is cheap, and on
its own it proves nothing: the same words can be registered by whoever posts them
first, copied or not. Trace makes the claim answerable. A challenger names an
earlier public page the work is said to be taken from, and the contract fetches
both pages itself and a round of GenLayer validators reads them and decides whether
the registered work reproduces the earlier one or stands on its own.

The verdict is permanent and it accrues to the registrant, so a record of whose
registrations held up as original, and whose were flagged as copies, builds up next
to the claim. The evidence is the two pages the contract read, not either party's
word for it.

## What it answers

    record(address) -> cleared, flagged

for anyone deciding how much an author's originality claim is worth: a track record
of works that survived a challenge and works that did not, each judged from the two
public pages, not from the author's own account of themselves.

## What it refuses

It never flags a work on an accusation alone: a challenge runs a round over the two
actual pages, and only a verdict that the work reproduces the earlier source flags
it. It never decides on silence: if either page cannot be read the verdict is
UNCLEAR, the registration stays open, and it can be challenged again. The registrant
is bound to the caller of register, and the challenger to the caller of challenge,
so nobody is credited or flagged for a claim they did not make.

## Where it stops, plainly

It judges whether one page reproduces another, not who authored either first: name
an earlier source a challenger can point to, not a private draft. Two independent
works on the same subject can read alike; the round is asked for reproduction, not
mere resemblance, but a loose judgement is possible, so the record is a signal, not
a court ruling.
"""

from genlayer import *
import json

COPY = "COPY"
INDEPENDENT = "INDEPENDENT"
UNCLEAR = "UNCLEAR"
VERDICTS = (COPY, INDEPENDENT, UNCLEAR)

REGISTERED = "REGISTERED"
CLEARED = "CLEARED"
FLAGGED = "FLAGGED"

MAX_TITLE = 200
MAX_URL = 300
MAX_PAGE = 5000
MAX_REASON = 300
MAX_QUOTE = 300

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
    return f"""Someone registered the work on PAGE A as their own original. A challenger says it
was taken from the earlier PAGE B. Read both pages and decide whether PAGE A
reproduces PAGE B.

WHAT THE REGISTRANT TITLED PAGE A:
{title}

PAGE A, the registered work:
{work_page}

PAGE B, the earlier source it is said to be copied from:
{prior_page}

Decide one of:
  {COPY} PAGE A substantially reproduces PAGE B: the same text, structure or
    passages, allowing for small edits, so A is a copy of B rather than its own work
  {INDEPENDENT} both pages were read and PAGE A does not reproduce PAGE B: it is its
    own work, even if the two share a subject or a few common phrases
  {UNCLEAR} one of the pages could not be read, or there is not enough on them to tell

Judge reproduction, not mere resemblance: two independent pieces on the same topic
are {INDEPENDENT}. Do not treat an unreachable or unrelated page as proof of a copy:
that is {UNCLEAR}, and the registration is left open rather than flagged.

Reply with bare JSON and nothing else:
{{"verdict": "{COPY}" or "{INDEPENDENT}" or "{UNCLEAR}",
  "quote": "a short passage that decided it, or empty",
  "reason": "one sentence naming what decided it"}}"""


class Trace(gl.Contract):
    """Registered works, each answerable to a challenge that checks it against an earlier source."""

    # str(id) -> the registration as JSON.
    items: TreeMap[str, str]
    ids: DynArray[str]
    # address -> {"cleared": n, "flagged": n} as JSON.
    records: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def register(self, work_url: str, title: str) -> str:
        """Claim a public page as your own original work. Bound to the caller.

        The claim starts REGISTERED and proves nothing on its own; it becomes
        CLEARED or FLAGGED only if someone challenges it and a round decides.
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
            "prior_url": "",
            "challenger": "",
            "reason": "",
            "quote": "",
            "judged_at": "",
        }
        self.items[wid] = json.dumps(record)
        self.ids.append(wid)
        return json.dumps({"ok": True, "id": wid, "status": REGISTERED})

    @gl.public.write
    def challenge(self, work_id: str, prior_url: str) -> str:
        """Challenge a registration: name an earlier page it is said to be copied from. Open to anybody.

        The contract fetches both the registered work and the earlier page inside
        the round; nobody passes in the verdict. COPY flags the registration and
        the registrant's record; INDEPENDENT clears it.
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
        if record["status"] != REGISTERED:
            return json.dumps({"ok": False, "error": "this registration is already " + record["status"].lower(),
                               "status": record["status"]})
        if prior == record["work_url"]:
            return json.dumps({"ok": False, "error": "the earlier source must be a different page from the work"})

        # Copy into locals before the round. Nothing inside the block reads self
        # and nothing inside it raises.
        title = record["title"]
        work_url = record["work_url"]

        def look() -> str:
            work_page = _fetch(work_url)
            prior_page = _fetch(prior)
            if work_page == FETCH_FAILED or prior_page == FETCH_FAILED:
                return json.dumps({"verdict": UNCLEAR, "quote": "",
                                   "reason": "one of the two pages could not be read"})
            try:
                return str(gl.nondet.exec_prompt(_task(title, work_page, prior_page)))
            except Exception as error:
                return json.dumps({"verdict": UNCLEAR, "quote": "",
                                   "reason": _clip("the prompt failed: " + str(error), MAX_REASON)})

        raw = gl.eq_principle.prompt_comparative(
            look,
            principle=(
                f"Both answers must carry the same value in the field named verdict, one of "
                f"{COPY}, {INDEPENDENT} or {UNCLEAR}. That single field decides whether a work is "
                "flagged as a copy on its author's permanent record, so two readers differing on it "
                "are not wording a judgement differently, they disagree about whether one page "
                "reproduces the other. The quote and the reason are not compared, and the two "
                "readers will not have fetched byte-identical copies of the pages."
            ),
        )

        verdict = _field(raw, "verdict", VERDICTS, "")
        if not verdict:
            return json.dumps({"ok": False,
                               "error": "the round produced no verdict this contract recognises",
                               "round_said": _clip(str(raw), 400)})

        record["challenges"] = int(record.get("challenges", 0)) + 1
        record["reason"] = _text_field(raw, "reason", MAX_REASON)
        record["quote"] = _text_field(raw, "quote", MAX_QUOTE)
        record["prior_url"] = prior
        record["challenger"] = challenger
        if verdict == COPY or verdict == INDEPENDENT:
            record["status"] = FLAGGED if verdict == COPY else CLEARED
            record["judged_at"] = _now_iso()
            author = record["author"]
            rec_raw = self.records.get(author, None)
            rec = json.loads(rec_raw) if rec_raw is not None else {"cleared": 0, "flagged": 0}
            if verdict == COPY:
                rec["flagged"] = int(rec.get("flagged", 0)) + 1
            else:
                rec["cleared"] = int(rec.get("cleared", 0)) + 1
            self.records[author] = json.dumps(rec)
        # UNCLEAR leaves the registration REGISTERED, to be challenged again later.
        self.items[wid] = json.dumps(record)
        return json.dumps({"ok": True, "id": wid, "verdict": verdict,
                           "status": record["status"], "reason": record["reason"]})

    # ------------------------------------------------------------------ reads

    @gl.public.view
    def record(self, address: str) -> str:
        """An author's permanent originality record: registrations cleared and flagged."""
        who = _addr(address)
        if not who:
            return json.dumps({"exists": False, "cleared": 0, "flagged": 0})
        rec_raw = self.records.get(who, None)
        if rec_raw is None:
            return json.dumps({"exists": False, "address": who, "cleared": 0, "flagged": 0})
        rec = json.loads(rec_raw)
        return json.dumps({"exists": True, "address": who,
                           "cleared": int(rec.get("cleared", 0)), "flagged": int(rec.get("flagged", 0))})

    @gl.public.view
    def status(self, work_id: str) -> str:
        """A registration's current standing and the reason it was judged."""
        wid = str(work_id).strip()
        stored = self.items.get(wid, None)
        if stored is None:
            return json.dumps({"exists": False})
        record = json.loads(stored)
        return json.dumps({"exists": True, "id": wid, "status": record["status"],
                           "challenges": record["challenges"], "reason": record["reason"]})

    @gl.public.view
    def get(self, work_id: str) -> str:
        """The whole registration, including the deciding quote and reason once judged."""
        wid = str(work_id).strip()
        stored = self.items.get(wid, None)
        if stored is None:
            return json.dumps({"exists": False})
        return stored

    @gl.public.view
    def size(self) -> str:
        """How many registrations are open, cleared and flagged."""
        registered = 0
        cleared = 0
        flagged = 0
        for position in range(len(self.ids)):
            record = json.loads(self.items[self.ids[position]])
            state = record["status"]
            if state == REGISTERED:
                registered += 1
            elif state == CLEARED:
                cleared += 1
            elif state == FLAGGED:
                flagged += 1
        return json.dumps({"total": len(self.ids), "registered": registered,
                           "cleared": cleared, "flagged": flagged})

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
            out.append(json.loads(self.items[self.ids[position]]))
            position -= 1
            seen += 1
        return json.dumps({"total": total, "start": begin, "count": len(out), "items": out})
