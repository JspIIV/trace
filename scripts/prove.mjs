// Prove Trace end to end on GenLayer Asimov, with the challenge flow un-gameable.
//
//   AT=0x... PADV=<padv pw> PPUB=<ppub pw> node scripts/prove.mjs
//
// padv registers a work that copies an earlier dated source, then self-challenges it
// against an unrelated page: that INDEPENDENT verdict must NOT clear it or move
// reputation. Anyone then challenges it against the real earlier source: only that
// flags it. A challenge against an unreadable page is UNCLEAR and leaves the work
// open. History is preserved across every challenge.
import { Wallet } from 'ethers';
import { createClient, createAccount } from 'genlayer-js';
import { testnetAsimov } from 'genlayer-js/chains';
import fs from 'fs';
import os from 'os';
import path from 'path';
import url from 'url';

const AT = process.env.AT;
const PADV = process.env.PADV || '';
const PPUB = process.env.PPUB || '';
if (!AT || !PADV || !PPUB) { console.error('set AT, PADV and PPUB'); process.exit(1); }

const ROOT = path.join(path.dirname(url.fileURLToPath(import.meta.url)), '..');
const KS = path.join(os.homedir(), '.genlayer', 'keystores');
async function acct(file, pw) {
  const w = await Wallet.fromEncryptedJson(fs.readFileSync(path.join(KS, file), 'utf8'), pw);
  return { addr: w.address.toLowerCase(), client: createClient({ chain: testnetAsimov, account: createAccount(w.privateKey) }) };
}
const padv = await acct('padv.json', PADV);
const ppub = await acct('ppub.json', PPUB);
const anybody = createClient({ chain: testnetAsimov });

const RAW = 'https://raw.githubusercontent.com/JspIIV/trace/master/docs/';
const ORIGINAL = RAW + 'original-essay.txt';       // earlier, dated 2024-01-15
const UNRELATED = RAW + 'independent-note.txt';     // a strawman for the self-clear attempt
const UNREADABLE = RAW + 'no-such-page-9f2c.txt';   // 404
const COPY_WORK = { url: RAW + 'copy-derivative.txt', title: 'The Silent Economics of Aging Bridges' };

const out = [];
const say = l => { console.log(l); out.push(l); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const transient = e => /-32005|-32006|-32029|-32603|at capacity|rate limit|gas rate|reverted.*consensus|consensus.*reverted|backpressure|fetch failed|timeout|502|503|429|ECONNRESET|ENOTFOUND|EAI_AGAIN|getaddrinfo/i
  .test(String(e?.details || e?.shortMessage || e?.message || e) + ' ' + String(e?.cause?.cause?.code || e?.cause?.code || ''));

async function read(fn, args = []) {
  for (let a = 1; ; a++) {
    try { return JSON.parse(await anybody.readContract({ address: AT, functionName: fn, args })); }
    catch (e) { if (!transient(e) || a >= 8) throw e; await sleep(4000 * a); }
  }
}
async function write(who, fn, args) {
  for (let a = 1; ; a++) {
    try { return await who.client.writeContract({ address: AT, functionName: fn, args, value: 0n }); }
    catch (e) { if (!transient(e) || a >= 8) throw e; say(`  (${fn} transient, wait ${8 * a}s)`); await sleep(8000 * a); }
  }
}
async function registerWork(who, work) {
  const n = (await read('size')).total;
  for (let attempt = 1; attempt <= 3; attempt++) {
    await write(who, 'register', [work.url, work.title]);
    for (let i = 0; i < 30; i++) { const s = await read('size'); if (s.total > n) return String(s.total - 1); await sleep(5000); }
    say('  (register #' + attempt + ' not seen after 150s, retrying)');
  }
  throw new Error('registration not made');
}
async function challengeUntil(who, id, prior, want, label) {
  // want: 'FLAGGED' to wait for a flag, or 'CHALLENGE' to wait for the challenge count to rise.
  const before = await read('get', [id]);
  const beforeN = Number(before.challenges || 0);
  for (let attempt = 1; attempt <= 4; attempt++) {
    try { await write(who, 'challenge', [id, prior]); } catch (e) { say(`  ${label} err ${String(e.message).slice(0, 50)}`); }
    for (let i = 0; i < 36; i++) {
      await sleep(15000);
      const g = await read('get', [id]);
      if (want === 'FLAGGED' && g.status === 'FLAGGED') { say(`  ${label}: FLAGGED (${(i + 1) * 15}s)`); return g; }
      if (want === 'CHALLENGE' && Number(g.challenges || 0) > beforeN) { say(`  ${label}: recorded (${(i + 1) * 15}s)`); return g; }
    }
    say(`  ${label}: not settled after poll, retrying`);
  }
  return await read('get', [id]);
}

say('Trace, proven on GenLayer Asimov (challenge flow un-gameable)');
say('  contract ' + AT);
say('  padv ' + padv.addr + '  ppub ' + ppub.addr);
say('');

const id0 = await registerWork(padv, COPY_WORK);
say('padv registered #' + id0 + ' (a work copied from an earlier dated source)');
const rec0 = await read('record', [padv.addr]);
say('  padv record after register: ' + JSON.stringify(rec0));
say('');

say('padv self-challenges #' + id0 + ' against an unrelated page, trying to lock in a clean record...');
const selfCh = await challengeUntil(padv, id0, UNRELATED, 'CHALLENGE', 'self-challenge');
const afterSelf = await read('get', [id0]);
const recAfterSelf = await read('record', [padv.addr]);
say('  #' + id0 + ' status after self-challenge: ' + afterSelf.status + ' | last verdict ' + (afterSelf.log?.[afterSelf.log.length - 1]?.verdict || '?'));
say('  padv record after self-challenge: ' + JSON.stringify(recAfterSelf));
say('');

say('anyone challenges #' + id0 + ' against the real earlier source...');
const flagged = await challengeUntil(ppub, id0, ORIGINAL, 'FLAGGED', 'real-source');
const recFlagged = await read('record', [padv.addr]);
say('  #' + id0 + ' status: ' + flagged.status + ' | ' + (flagged.flag_reason || ''));
say('  padv record after real challenge: ' + JSON.stringify(recFlagged));
const hist0 = await read('history', [id0]);
say('  history entries: ' + hist0.log.length + ' [' + hist0.log.map(e => e.verdict).join(', ') + ']');
say('');

const id1 = await registerWork(ppub, { url: UNRELATED, title: 'Notes on Harvesting Rainwater' });
say('ppub registered #' + id1 + ' (to be challenged against an unreadable page)');
const unreadable = await challengeUntil(ppub, id1, UNREADABLE, 'CHALLENGE', 'unreadable');
say('  #' + id1 + ' status: ' + unreadable.status + ' | last verdict ' + (unreadable.log?.[unreadable.log.length - 1]?.verdict || '?'));
say('');

const size = await read('size');
say('register: ' + JSON.stringify(size));

const selfVerdict = afterSelf.log?.[afterSelf.log.length - 1]?.verdict;
const checks = [
  ['a self-challenge against an unrelated page does not flag the work', afterSelf.status === 'REGISTERED'],
  ['and it does not clear it or move reputation (still 0 flagged)', recAfterSelf.flagged === 0 && recAfterSelf.works === 1],
  ['the self-challenge is recorded but decides nothing (INDEPENDENT)', selfVerdict === 'INDEPENDENT'],
  ['later real evidence still flags the work despite the earlier no-op', flagged.status === 'FLAGGED'],
  ["the copier's record then gains exactly one flag", recFlagged.flagged === 1 && recFlagged.works === 1],
  ['every challenge is preserved in history, oldest first', hist0.log.length >= 2 && hist0.log[hist0.log.length - 1].verdict === 'COPY'],
  ['a challenge against an unreadable page is UNCLEAR and leaves the work registered',
    unreadable.status === 'REGISTERED' && unreadable.log[unreadable.log.length - 1].verdict === 'UNCLEAR'],
  ['the register counts one flagged work', size.flagged === 1],
];
say('');
for (const [label, ok] of checks) say((ok ? '  ok   ' : ' FAIL  ') + label);
const failed = checks.filter(([, ok]) => !ok);
say('');
say(failed.length ? `${failed.length} of ${checks.length} checks failed` : `${checks.length} checks. Only earlier dated evidence flags a work, and a clean record cannot be manufactured.`);

fs.mkdirSync(path.join(ROOT, 'results'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'results', 'proved.json'), JSON.stringify({
  proved_at: new Date().toISOString(), network: 'genlayer testnet asimov', contract: AT,
  self_challenge: afterSelf, record_after_self: recAfterSelf, flagged, record_after_flag: recFlagged,
  history: hist0, unreadable, size,
  checks: checks.map(([label, ok]) => ({ label, ok })), transcript: out,
}, null, 2));
say('Written to results/proved.json');
process.exit(failed.length ? 1 : 0);
