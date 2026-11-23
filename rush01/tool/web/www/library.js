/* library.js: the /library page (CONTRACT.md B8): lists every catalog entry
   grouped by part/tier, plays its preset demo, and offers side-by-side compare
   mode for any two solving approaches on the same puzzle. */

"use strict";

const lib = {
	catalog: [],
	by_demo: {},
	active: null,
	player: null,
	cmp_left: null,
	cmp_right: null,
	race: null
};

async function lib_main()
{
	page_theme();
	/* 1. load catalog from /api/catalog */
	try
	{
		lib.catalog = await page_api("/api/catalog");
	}
	catch (e)
	{
		page_q("#lib-list").innerHTML = `<p class="diag warn">Failed to load catalog: `
			+ `${page_esc(e.message)}</p>`;
		return;
	}
	for (const entry of lib.catalog)
	{
		const key = (entry.demo || entry.id).replace(".", "_");
		lib.by_demo[key] = entry;
	}
	/* 2. draw the catalog sidebar and wire compare selects */
	lib_render_list();
	lib_init_compare();
	/* 3. mode toggles */
	page_q("#mode-browse").onclick = function ()
	{
		lib_set_mode("browse");
	};
	page_q("#mode-compare").onclick = function ()
	{
		lib_set_mode("compare");
	};
	/* 4. pick entry from URL hash, or the first solving entry */
	const hash = decodeURIComponent((location.hash || "").slice(1)).replace(".", "_");
	const start = lib.by_demo[hash] || lib.by_demo["solve_bt_clue_line"]
		|| lib.catalog[0];
	if (start)
		lib_select(start);
}

function lib_set_mode(mode)
{
	const is_cmp = mode === "compare";

	page_q("#browse-view").hidden = is_cmp;
	page_q("#compare-view").hidden = !is_cmp;
	page_q("#mode-browse").classList.toggle("on", !is_cmp);
	page_q("#mode-compare").classList.toggle("on", is_cmp);
	if (is_cmp)
	{
		if (lib.player)
			demo_stop(lib.player);
		lib_mount_compare();
	}
	else
	{
		lib_race_stop();
		if (lib.cmp_left)
			demo_stop(lib.cmp_left);
		if (lib.cmp_right)
			demo_stop(lib.cmp_right);
	}
}

function lib_key(e)
{
	return (e.demo || e.id).replace(".", "_");
}

/* the sidebar: one folding group per part; the filter box hides what
   doesn't match (name, id or tier, e.g. "t3") */
function lib_render_list()
{
	let html = "";

	for (const part of PAGE_PARTS)
	{
		const items = lib.catalog.filter(function (e)
		{
			return e.part === part;
		});
		if (!items.length)
			continue;
		html += `<details open data-part="${part}"><summary><span class="lab lib-group">`
			+ `${PAGE_PART_LABEL[part].toUpperCase()} <i>(${items.length})</i></span>`
			+ "</summary><ul class=\"lib-items\">";
		for (const e of items)
		{
			const tier = e.tier !== null && e.tier !== undefined
				? `<span class="tier">T${e.tier}</span> ` : "";
			const words = [e.name, e.id, e.tier !== null && e.tier !== undefined
				? "t" + e.tier : ""].join(" ").toLowerCase();
			html += `<li data-words="${page_esc(words)}"><button type="button" class="lib-item" `
				+ `data-key="${page_esc(lib_key(e))}" title="${page_esc(e.name)}">${tier}<span>${page_esc(e.name)}</span>`
				+ "</button></li>";
		}
		html += "</ul></details>";
	}
	html += "<p class=\"lib-none\" hidden>Nothing matches.</p>";
	const box = page_q("#lib-list");
	box.innerHTML = html;
	box.addEventListener("click", function (ev)
	{
		const btn = ev.target.closest(".lib-item");
		if (!btn)
			return;
		const entry = lib.by_demo[btn.dataset.key];
		if (!entry)
			return;
		lib_select(entry);
		/* one column (narrow page): the demo is under the list */
		if (getComputedStyle(page_q(".lib-nav")).position !== "sticky")
			page_q(".lib-stage").scrollIntoView({block: "start"});
	});
	lib_filter_keys();
}

function lib_filter(q)
{
	const box = page_q("#lib-list");
	let any = 0;

	q = q.trim().toLowerCase();
	for (const group of box.querySelectorAll("details"))
	{
		let n = 0;

		for (const li of group.querySelectorAll("li"))
		{
			li.hidden = q !== "" && li.dataset.words.indexOf(q) < 0;
			n += li.hidden ? 0 : 1;
		}
		group.hidden = n === 0;
		if (q && n)
			group.open = true;
		any += n;
	}
	page_q(".lib-none", box).hidden = any > 0;
}

/* "/" focuses the filter, Enter picks the first match, Esc clears;
   up / down walk the list when the focus is not in a field */
function lib_filter_keys()
{
	const find = page_q("#lib-find");

	find.oninput = function ()
	{
		lib_filter(find.value);
	};
	find.onkeydown = function (ev)
	{
		if (ev.key === "Escape")
		{
			find.value = "";
			lib_filter("");
			find.blur();
		}
		else if (ev.key === "Enter")
		{
			const first = page_q("#lib-list li:not([hidden]) .lib-item");

			if (first)
				first.click();
		}
	};
	document.addEventListener("keydown", function (ev)
	{
		const tag = (document.activeElement || {}).tagName;

		if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA"
			|| page_q("#browse-view").hidden)
			return;
		if (ev.key === "/")
		{
			ev.preventDefault();
			find.focus();
			find.select();
		}
		else if (ev.key === "ArrowDown" || ev.key === "ArrowUp")
		{
			const all = Array.from(document.querySelectorAll(
				"#lib-list li:not([hidden]) .lib-item"));
			const at = all.findIndex(function (b)
			{
				return b.classList.contains("on");
			});
			const next = all[at + (ev.key === "ArrowDown" ? 1 : -1)];

			if (next)
			{
				ev.preventDefault();
				next.click();
			}
		}
	});
}

/* scroll the catalog box (only it, never the page) to show the button */
function lib_list_show(btn)
{
	const list = page_q("#lib-list");
	const r = btn.getBoundingClientRect();
	const lr = list.getBoundingClientRect();

	if (r.top < lr.top || r.bottom > lr.bottom)
		list.scrollTop += r.top - lr.top - lr.height / 3;
}

function lib_select(entry)
{
	const key = (entry.demo || entry.id).replace(".", "_");

	/* 1. highlight active button */
	lib.active = entry;
	for (const btn of document.querySelectorAll(".lib-item"))
	{
		btn.classList.toggle("on", btn.dataset.key === key);
		if (btn.dataset.key === key)
		{
			btn.closest("details").open = true;
			lib_list_show(btn);
		}
	}
	const stage = page_q(".lib-stage");
	if (stage.getBoundingClientRect().top < 0)
		stage.scrollIntoView({block: "start"});
	/* 2. header, explanation, defense questions */
	const tier = entry.tier !== null && entry.tier !== undefined
		? ` · TIER ${entry.tier}` : "";
	page_q("#lib-part").textContent = `${entry.part.toUpperCase()}${tier} · ${entry.id}`;
	page_q("#lib-name").textContent = entry.name;
	page_q("#lib-explain").textContent = entry.explain || "";
	const qs = page_q("#lib-qs");
	if (entry.questions && entry.questions.length)
	{
		qs.hidden = false;
		qs.innerHTML = `<summary>Defense questions (${entry.questions.length})</summary><ol>`
			+ entry.questions.map(function (q)
			{
				return `<li>${page_esc(q)}</li>`;
			}).join("") + "</ol>";
	}
	else
		qs.hidden = true;
	/* 3. mount preset demo */
	if (lib.player)
		demo_stop(lib.player);
	lib.player = demo_mount(page_q("#lib-demo"), {
		demo_id: key,
		entry: entry,
		show_puzzle_pick: true
	});
	if (history.replaceState)
		history.replaceState(null, "", "#" + encodeURIComponent(key));
}

/* ---- Compare mode: two solving presets side by side ---------------------- */

function lib_init_compare()
{
	const solvers = lib.catalog.filter(function (e)
	{
		return e.part === "solve";
	});
	const opts = solvers.map(function (e)
	{
		const key = (e.demo || e.id).replace(".", "_");
		return `<option value="${page_esc(key)}">T${e.tier} · ${page_esc(e.name)}</option>`;
	}).join("");
	const left = page_q("#cmp-left");
	const right = page_q("#cmp-right");
	const puz = page_q("#cmp-puzzle");

	left.innerHTML = opts;
	right.innerHTML = opts;
	left.value = lib.by_demo["solve_bt_unique"] ? "solve_bt_unique"
		: (solvers[0] ? (solvers[0].demo || solvers[0].id).replace(".", "_") : "");
	right.value = lib.by_demo["solve_bt_clue_line"] ? "solve_bt_clue_line"
		: (solvers[1] ? (solvers[1].demo || solvers[1].id).replace(".", "_") : left.value);
	puz.innerHTML = DEMO_PUZZLES.map(function (p)
	{
		return `<option value="${page_esc(p.id)}">${page_esc(p.label)}</option>`;
	}).join("");
	puz.value = "asym";

	left.onchange = lib_mount_compare;
	right.onchange = lib_mount_compare;
	puz.onchange = lib_mount_compare;
	page_q("#cmp-reset").onclick = function ()
	{
		if (lib.cmp_left)
			demo_control(lib.cmp_left, "reset");
		if (lib.cmp_right)
			demo_control(lib.cmp_right, "reset");
	};
	page_q("#cmp-play").onclick = function ()
	{
		if (lib.cmp_left)
			demo_control(lib.cmp_left, "play");
		if (lib.cmp_right)
			demo_control(lib.cmp_right, "play");
	};
	page_q("#cmp-step").onclick = function ()
	{
		if (lib.cmp_left)
			demo_control(lib.cmp_left, "next");
		if (lib.cmp_right)
			demo_control(lib.cmp_right, "next");
	};
	page_q("#cmp-end").onclick = function ()
	{
		if (lib.cmp_left)
			demo_control(lib.cmp_left, "end");
		if (lib.cmp_right)
			demo_control(lib.cmp_right, "end");
	};
}

function lib_mount_compare()
{
	const lkey = page_q("#cmp-left").value;
	const rkey = page_q("#cmp-right").value;
	const pid = page_q("#cmp-puzzle").value;
	const le = lib.by_demo[lkey];
	const re = lib.by_demo[rkey];

	if (lib.cmp_left)
		demo_stop(lib.cmp_left);
	if (lib.cmp_right)
		demo_stop(lib.cmp_right);
	page_q("#cmp-left-title").textContent = le ? le.name : lkey;
	page_q("#cmp-right-title").textContent = re ? re.name : rkey;
	lib.cmp_left = demo_mount(page_q("#cmp-left-box"), {
		demo_id: lkey, entry: le, puzzle_id: pid,
		show_puzzle_pick: false, compact: true
	});
	lib.cmp_right = demo_mount(page_q("#cmp-right-box"), {
		demo_id: rkey, entry: re, puzzle_id: pid,
		show_puzzle_pick: false, compact: true
	});
	const lt = lib.cmp_left.rec ? lib.cmp_left.rec.total : 0;
	const rt = lib.cmp_right.rec ? lib.cmp_right.rec.total : 0;
	const lcap = lib.cmp_left.rec && lib.cmp_left.rec.capped ? "+" : "";
	const rcap = lib.cmp_right.rec && lib.cmp_right.rec.capped ? "+" : "";
	page_q("#cmp-summary").textContent =
		`${le ? le.name : lkey}: ${lt}${lcap} steps  vs  ${re ? re.name : rkey}: ${rt}${rcap} steps`;
	lib_race_start(le ? le.name : lkey, re ? re.name : rkey);
}

/* ---- the VS race: each side's step bar follows its player --------------- */

const LIB_RACE_MS = 80;

function lib_race_side(side, name)
{
	return `<div class="vs-side ${side}"><span class="vs-p">${side === "l" ? "P1" : "P2"}</span>`
		+ `<span class="vs-name">${page_esc(name)}</span>`
		+ `<span class="vs-track"><i id="vs-${side}-bar" style="width:0%"></i></span>`
		+ `<span class="vs-count" id="vs-${side}-count"></span>`
		+ `<span id="vs-${side}-done"></span></div>`;
}

function lib_race_start(lname, rname)
{
	lib_race_stop();
	page_q("#vs-head").innerHTML = lib_race_side("l", lname)
		+ "<span class=\"vs-emblem\">VS</span>" + lib_race_side("r", rname);
	lib.race = setInterval(lib_race_tick, LIB_RACE_MS);
	lib_race_tick();
}

function lib_race_stop()
{
	if (lib.race)
		clearInterval(lib.race);
	lib.race = null;
}

/* the facts of one side: where its player is, and how it ended */
function lib_race_state(player)
{
	const rec = player && player.rec;

	if (!rec || !rec.steps.length)
		return null;
	const last = rec.steps.length - 1;
	const done = player.idx >= last;
	return {pct: Math.round(100 * (player.idx + 1) / rec.steps.length),
		count: `step ${player.idx + 1}/${rec.steps.length}`
			+ (rec.capped ? ` (${rec.total}+ total, capped)`
				: rec.total > rec.steps.length ? ` (${rec.total} total)` : ""),
		done: done, solved: done && rec.steps[last].op === "done",
		total: rec.total, capped: Boolean(rec.capped)};
}

function lib_race_tick()
{
	const sides = {l: lib_race_state(lib.cmp_left), r: lib_race_state(lib.cmp_right)};
	const both = sides.l && sides.r && sides.l.done && sides.r.done;

	for (const k of ["l", "r"])
	{
		const st = sides[k];
		const other = sides[k === "l" ? "r" : "l"];
		const bar = page_q(`#vs-${k}-bar`);

		if (!bar)
			return;
		if (!st)
		{
			page_q(`#vs-${k}-count`).textContent = "no preset";
			continue;
		}
		bar.style.width = st.pct + "%";
		page_q(`#vs-${k}-count`).textContent = st.count;
		let done = "";
		if (st.done)
		{
			const fewer = both && other && !st.capped
				&& (other.capped || st.total < other.total);
			done = `<span class="vs-done${st.solved ? "" : " end"}${fewer ? " vs-first" : ""}">`
				+ `${st.solved ? "SOLVED" : "ENDED"} · ${st.total}${st.capped ? "+" : ""} steps`
				+ `${fewer ? " · fewer steps" : ""}</span>`;
		}
		const box = page_q(`#vs-${k}-done`);
		if (box.innerHTML !== done)
			box.innerHTML = done;
	}
}

lib_main();
