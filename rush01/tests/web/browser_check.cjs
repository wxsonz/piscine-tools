// browser_check.cjs: headless chromium on the fixture server (B4, B6).
//   node browser_check.cjs <playwright-core dir> <chromium> <base url> <mode>
// mode "load": / and /team/c01, /team/d3 load without JS errors (B6).
// mode "sky":  the 3D view: blocks, a clicked clue's sightline, 9x9, 2D (B4).
// Prints one JSON line: {errors: [...], facts: {...}}.
const [pw_dir, chrome, base, mode] = process.argv.slice(2);
const { chromium } = require(pw_dir);

async function open_page(browser, path, errors)
{
	const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });

	page.on("console", function (m)
	{
		if (m.type() === "error")
			errors.push(path + ": " + m.text());
	});
	page.on("pageerror", function (e)
	{
		errors.push(path + ": page error: " + e.message);
	});
	await page.goto(base + path);
	return page;
}

async function check_load(browser, errors, facts)
{
	/* 1. the dashboard, list view (the default): one row per team; the
	   filters and the search box hide rows */
	let page = await open_page(browser, "/", errors);
	await page.evaluate(function ()
	{
		localStorage.clear();
	});
	await page.reload();
	await page.waitForSelector(".trow[data-team] .r-part", { timeout: 15000 });
	facts.list = await page.evaluate(function ()
	{
		const out = {rows: {}};
		for (const row of document.querySelectorAll(".trow[data-team]"))
		{
			out.rows[row.dataset.team] = {
				parts: row.querySelectorAll(".r-part").length,
				unrec: row.querySelectorAll(".r-part.c-unrecognized").length,
				stamp: row.querySelector(".r-stamp").textContent.trim(),
				link: Boolean(row.querySelector("a.r-name"))
			};
		}
		out.filters = Array.from(document.querySelectorAll("#filters [data-filter]"))
			.map(function (b)
			{
				return b.textContent.trim();
			});
		return out;
	});
	await page.click("#filters [data-filter=\"stop\"]");
	facts.list.stop_shown = await page.evaluate(function ()
	{
		return Array.from(document.querySelectorAll(".trow[data-team]:not([hidden])"))
			.map(function (r)
			{
				return r.dataset.team;
			});
	});
	await page.click("#filters [data-filter=\"all\"]");
	await page.fill("#find", "c0");
	facts.list.find_shown = await page.evaluate(function ()
	{
		return Array.from(document.querySelectorAll(".trow[data-team]:not([hidden])"))
			.map(function (r)
			{
				return r.dataset.team;
			});
	});
	await page.fill("#find", "zzz");
	facts.list.nomatch = await page.evaluate(function ()
	{
		return !document.getElementById("nomatch").hidden;
	});
	await page.close();
	/* the select view: a roster, ↓ picks a team, its card on the right */
	page = await open_page(browser, "/?view=select", errors);
	await page.waitForSelector(".sel-roster li[data-pick]", { timeout: 15000 });
	await page.keyboard.press("ArrowDown");
	facts.select = await page.evaluate(function ()
	{
		const card = document.querySelector(".sel-preview[data-team]");
		return {
			roster: document.querySelectorAll(".sel-roster li[data-pick]").length,
			on: (document.querySelector(".sel-roster li.on") || {dataset: {}}).dataset.pick,
			preview: card ? card.dataset.team : null,
			chips: card ? card.querySelectorAll(".vchip").length : 0
		};
	});
	await page.close();
	/* 2. the dashboard, cards: one card per team, four verdict chips each */
	page = await open_page(browser, "/?view=cards", errors);
	await page.waitForSelector(".card.team .vchip", { timeout: 15000 });
	facts.dash = await page.evaluate(function ()
	{
		const out = {};
		for (const card of document.querySelectorAll(".card.team"))
		{
			out[card.dataset.team] = {
				chips: card.querySelectorAll(".vchip").length,
				unrec: card.querySelectorAll(".vchip.c-unrecognized").length,
				hearts: card.querySelectorAll(".heart").length,
				stamp: card.querySelector(".stamp").textContent.trim()
			};
		}
		return out;
	});
	await page.close();
	/* 3. the team pages: four part cards, the runs, the 3D view, the source */
	for (const name of ["c01", "d3"])
	{
		page = await open_page(browser, "/team/" + name, errors);
		/* the source lives in the Source tab: there, not shown */
		await page.waitForSelector("#source .src, #source .diag",
			{ timeout: 15000, state: "attached" });
		facts[name] = await page.evaluate(function ()
		{
			const diag = document.querySelector("#runs .diag");
			return {
				parts: document.querySelectorAll(".part").length,
				unrec: document.querySelectorAll(".part.c-unrecognized").length,
				diag: diag ? diag.textContent : "",
				groups: document.querySelectorAll("details.group").length,
				boxes: document.querySelectorAll(".sky-box").length,
				sky_empty: Boolean(document.querySelector("#skybox .empty")),
				files: document.querySelectorAll("#source .pane").length,
				graph: Boolean(document.querySelector("#source svg.graph")),
				gates: Array.from(document.querySelectorAll("#gates .gate"))
					.map(function (g)
					{
						return g.className.replace("gate ", "");
					}),
				hud: document.getElementById("hud").textContent,
				slots: document.querySelectorAll("#loadout .slot").length
			};
		});
		/* the deck: Runs shows the runs and hides the parts; a gate
		   opens the tab its detail lives in */
		await page.click("[data-deck=\"runs\"]");
		facts[name].deck_runs = await page.evaluate(function ()
		{
			return {
				runs: getComputedStyle(document.getElementById("runs")).display !== "none",
				parts: getComputedStyle(document.getElementById("parts")).display !== "none"
			};
		});
		await page.click("#gates .gate[data-goto=\"norm\"]");
		facts[name].gate_norm = await page.evaluate(function ()
		{
			return getComputedStyle(document.getElementById("strip")).display !== "none";
		});
		await page.click("[data-deck=\"defense\"]");
		await page.close();
	}
}

async function check_sky(browser, errors, facts)
{
	const page = await open_page(browser, "/team/c01", errors);

	await page.waitForSelector(".sky-box", { timeout: 15000 });
	/* 1. the first run shown is a wrong 4x4 grid: 16 blocks, 16 clues */
	facts.first = await page.evaluate(function ()
	{
		return {
			run: document.querySelector(".sky-pick").value,
			boxes: document.querySelectorAll(".sky-box").length,
			clues: document.querySelectorAll(".sky-board .sky-clue").length,
			bad: document.querySelectorAll(".sky-board .sky-clue.bad").length
		};
	});
	/* 2. click each clue: seen blocks = the count shown = sky_counts */
	facts.lines = await page.evaluate(function ()
	{
		const out = [];
		const counts = sky_counts(team.sky.grid);
		for (const chip of document.querySelectorAll(".sky-board .sky-clue"))
		{
			chip.click();
			const k = Number(chip.dataset.k);
			out.push({
				k: k,
				want: team.sky.clues[k],
				count: counts[k],
				shown: chip.querySelector(".cnt").textContent,
				seen: document.querySelectorAll(".sky-box.seen").length,
				hidden: document.querySelectorAll(".sky-box.hidden").length,
				bad: chip.classList.contains("bad")
			});
			chip.click();
		}
		return out;
	});
	/* 3. the views turn the board */
	await page.click("[data-view=top]");
	facts.top = await page.evaluate(function ()
	{
		return document.querySelector(".sky-board").style.transform;
	});
	/* 4. a 9x9 through the picker, then the 2D fallback */
	await page.selectOption(".sky-pick", "bonusN-03");
	facts.nine = await page.evaluate(function ()
	{
		return document.querySelectorAll(".sky-box").length;
	});
	await page.click(".sky-mode");
	await page.click(".sky-flat .sky-clue[data-k=\"0\"]");
	facts.flat = await page.evaluate(function ()
	{
		return {
			visible: !document.querySelector(".sky-flat").hidden,
			cells: document.querySelectorAll(".sky-cell[data-r]").length,
			seen: document.querySelectorAll(".sky-cell.seen").length,
			count: sky_counts(team.sky.grid)[0]
		};
	});
	/* 5. a run with no grid: the output is written, no blocks */
	await page.selectOption(".sky-pick", "nosol4-easy-01");
	facts.error_run = await page.evaluate(function ()
	{
		return {
			boxes: document.querySelectorAll(".sky-box").length,
			msg: document.querySelector(".sky-flatmsg, .sky-msg").textContent
		};
	});
	await page.close();
}

async function check_demos(browser, errors, facts)
{
	/* 1. /team/c01: click "show how it works" on a recognized card */
	let page = await open_page(browser, "/team/c01", errors);
	await page.waitForSelector(".part .demo-btn", { timeout: 15000 });
	await page.click(".part .demo-btn");
	await page.waitForSelector("#demo-modal .demo-stage", { timeout: 15000 });
	await page.click("#demo-modal [data-act=\"next\"]");
	await page.click("#demo-modal [data-act=\"end\"]");
	facts.modal = await page.evaluate(function ()
	{
		const dlg = document.getElementById("demo-modal");
		return {
			open: Boolean(dlg && !dlg.hidden),
			banner: dlg.querySelector(".demo-preset-tag").textContent,
			count: dlg.querySelector(".demo-count").textContent
		};
	});
	await page.click("#dm-close");
	await page.close();
	/* 2. /library: catalog renders, preset plays, compare mode works */
	page = await open_page(browser, "/library", errors);
	await page.waitForSelector(".lib-item", { timeout: 15000 });
	await page.click("#lib-demo [data-act=\"end\"]");
	facts.library = await page.evaluate(function ()
	{
		return {
			items: document.querySelectorAll(".lib-item").length,
			banner: document.querySelector("#lib-demo .demo-preset-tag").textContent,
			count: document.querySelector("#lib-demo .demo-count").textContent
		};
	});
	/* the catalog filter: a tier word ("t2") keeps only that tier's entries */
	await page.fill("#lib-find", "t2");
	facts.library.t2 = await page.evaluate(function ()
	{
		return Array.from(document.querySelectorAll("#lib-list li:not([hidden]) .tier"))
			.map(function (t)
			{
				return t.textContent;
			});
	});
	await page.fill("#lib-find", "zzz");
	facts.library.none = await page.evaluate(function ()
	{
		return !document.querySelector(".lib-none").hidden;
	});
	await page.fill("#lib-find", "");
	await page.click("#mode-compare");
	await page.waitForSelector("#cmp-left-box .demo-stage", { timeout: 15000 });
	await page.click("#cmp-step");
	await page.click("#cmp-end");
	await page.waitForTimeout(300);
	facts.compare = await page.evaluate(function ()
	{
		return {
			visible: !document.getElementById("compare-view").hidden,
			summary: document.getElementById("cmp-summary").textContent,
			vs_l: document.getElementById("vs-l-done").textContent,
			vs_r: document.getElementById("vs-r-done").textContent,
			left_boxes: document.querySelectorAll("#cmp-left-box .sky-box").length,
			right_boxes: document.querySelectorAll("#cmp-right-box .sky-box").length
		};
	});
	await page.close();
}

(async function ()
{
	const browser = await chromium.launch({ executablePath: chrome,
		args: ["--no-sandbox", "--disable-extensions"] });
	const errors = [];
	const facts = {};

	try
	{
		if (mode === "sky")
			await check_sky(browser, errors, facts);
		else if (mode === "demos")
			await check_demos(browser, errors, facts);
		else
			await check_load(browser, errors, facts);
	}
	catch (e)
	{
		errors.push("failure: " + e.message.split("\n")[0]);
	}
	await browser.close();
	console.log(JSON.stringify({ errors: errors, facts: facts }));
})();
