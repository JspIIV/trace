// Prove Trace end to end on GenLayer Asimov.
//
//   AT=0x... PADV=<padv pw> PPUB=<ppub pw> node scripts/prove.mjs
//
// padv registers a work that copies an earlier page (challenged -> COPY, flagged);
// ppub registers an independent work (challenged -> INDEPENDENT, cleared); a
// challenge whose earlier page cannot be read is UNCLEAR and leaves the work open.
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
const ORIGINAL = RAW + 'original-essay.txt';
const COPY_WORK = { url: RAW + 'copy-derivative.txt', title: 'The Silent Economics of Aging Bridges' };
const INDEP_WORK = { url: RAW + 'independent-note.txt', title: 'Notes on Harvesting Rainwater in a Small Garden' };
const UNREADABLE = RAW + 'no-such-page-9f2c.txt';

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
  await write(who, 'register', [work.url, work.title]);
  for (let i = 0; i < 20; i++) { const s = await read('size'); if (s.total > n) return String(s.total - 1); await sleep(4000); }
  throw new Error('registration not made');
}
async function challengeUntilJudged(who, id, prior, label) {
  for (let attempt = 1; attempt <= 4; attempt++) {
    let g = await read('get', [id]);
    if (g.status === 'FLAGGED' || g.status === 'CLEARED') { say(`  ${label}: already ${g.status}`); return g; }
    try { await write(who, 'challenge', [id, prior]); } catch (e) { say(`  ${label} challenge err ${String(e.message).slice(0, 50)}`); }
    for (let i = 0; i < 36; i++) {
      await sleep(15000);
      g = await read('get', [id]);
      if (g.status === 'FLAGGED' || g.status === 'CLEARED') { say(`  ${label}: ${g.status} (${(i + 1) * 15}s)`); return g; }
    }
    say(`  ${label}: not judged after poll, retrying`);
  }
  return await read('get', [id]);
}

say('Trace, proven on GenLayer Asimov');
say('  contract ' + AT);
say('  padv ' + padv.addr + '  ppub ' + ppub.addr);
say('');

const id0 = await registerWork(padv, COPY_WORK);
say('padv registered #' + id0 + ' (a work copied from an earlier page)');
const id1 = await registerWork(ppub, INDEP_WORK);
say('ppub registered #' + id1 + ' (an independent work)');
const id2 = await registerWork(padv, { url: ORIGINAL, title: 'The Quiet Economics of Old Bridges' });
say('padv registered #' + id2 + ' (to be challenged against an unreadable source)');
say('');

say('challenging #' + id0 + ' against the earlier essay...');
const r0 = await challengeUntilJudged(ppub, id0, ORIGINAL, 'copy');
say('  status ' + r0.status + ' | ' + (r0.reason || ''));
say('challenging #' + id1 + ' against the unrelated essay...');
const r1 = await challengeUntilJudged(padv, id1, ORIGINAL, 'independent');
say('  status ' + r1.status + ' | ' + (r1.reason || ''));
say('');

say('challenging #' + id2 + ' against an unreadable page...');
try { await write(ppub, 'challenge', [id2, UNREADABLE]); } catch (e) { say('  challenge err ' + String(e.message).slice(0, 50)); }
let r2 = await read('get', [id2]);
for (let i = 0; i < 20 && r2.status === 'REGISTERED' && Number(r2.challenges) === 0; i++) { await sleep(15000); r2 = await read('get', [id2]); }
say('  #' + id2 + ' status: ' + r2.status + ' (challenges: ' + r2.challenges + ')');
say('');

const recPadv = await read('record', [padv.addr]);
const recPpub = await read('record', [ppub.addr]);
const size = await read('size');
say('record(padv) = ' + JSON.stringify(recPadv) + ' ; record(ppub) = ' + JSON.stringify(recPpub));
say('register: ' + JSON.stringify(size));

const checks = [
  ['a work that copies its source is judged COPY and flagged', r0.status === 'FLAGGED'],
  ['an independent work is judged INDEPENDENT and cleared', r1.status === 'CLEARED'],
  ["the copier's record gains a flagged", recPadv.flagged >= 1],
  ["the cleared author's record gains a cleared", recPpub.cleared >= 1],
  ['a challenge whose earlier page cannot be read is UNCLEAR, the work stays registered', r2.status === 'REGISTERED'],
  ['the register counts one cleared and one flagged', size.cleared === 1 && size.flagged === 1],
];
say('');
for (const [label, ok] of checks) say((ok ? '  ok   ' : ' FAIL  ') + label);
const failed = checks.filter(([, ok]) => !ok);
say('');
say(failed.length ? `${failed.length} of ${checks.length} checks failed` : `${checks.length} checks. The two pages judged the work, and the record remembered.`);

fs.mkdirSync(path.join(ROOT, 'results'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'results', 'proved.json'), JSON.stringify({
  proved_at: new Date().toISOString(), network: 'genlayer testnet asimov', contract: AT,
  copy: r0, independent: r1, unreadable: r2, record: { padv: recPadv, ppub: recPpub }, size,
  checks: checks.map(([label, ok]) => ({ label, ok })), transcript: out,
}, null, 2));
say('Written to results/proved.json');
process.exit(failed.length ? 1 : 0);
