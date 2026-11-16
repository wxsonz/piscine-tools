// node browser_check.cjs <playwright-core dir> <chromium path> <base url> '<json list of teams>'
// Opens /team/<name> for every team, waits for the trace, and prints one JSON line:
// { team: { errors: [...], lead: "...", cells: n, chars: n, flags: n } }
const [pwDir, chrome, base, namesJson] = process.argv.slice(2);
const { chromium } = require(pwDir);
(async () => {
  const names = JSON.parse(namesJson);
  const b = await chromium.launch({ executablePath: chrome, args: ['--no-sandbox'] });
  const out = {};
  for (const name of names) {
    const p = await b.newPage({ viewport: { width: 1360, height: 900 } });
    const errors = [];
    p.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    p.on('pageerror', e => errors.push('page error: ' + e.message));
    try {
      await p.goto(`${base}/team/${encodeURIComponent(name)}`);
      await p.waitForSelector('#run, #main .err', { timeout: 60000 });
      const info = await p.evaluate(() => {
        const err = document.querySelector('#main .err');
        const lead = document.querySelector('.idea .lead');
        const cells = document.querySelectorAll('.mainmap .cmap .c[data-step]').length;
        // A is a top-level `let` in viz.html: reachable by name, not as window.A
        const a = typeof A !== 'undefined' ? A : null;
        const chars = (a && a.T && typeof a.T.output === 'string') ? a.T.output.replace(/\n/g, '').length : -1;
        const flags = document.querySelectorAll('.sizes .flag').length;
        return { err: err ? err.textContent : null, lead: lead ? lead.textContent : '', cells, chars, flags };
      });
      if (info.err) errors.push('page shows: ' + info.err.slice(0, 200));
      if (info.chars >= 0 && info.cells !== info.chars) errors.push(`map has ${info.cells} cells for ${info.chars} printed chars`);
      // step through a bit: the stepper must not throw
      if (await p.$('#next')) { for (let i = 0; i < 5; i++) await p.click('#next'); }
      out[name] = { errors, lead: info.lead, cells: info.cells, chars: info.chars, flags: info.flags };
    } catch (e) {
      out[name] = { errors: [...errors, 'timeout/failure: ' + e.message.split('\n')[0]] };
    }
    await p.close();
  }
  await b.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
