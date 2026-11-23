/* dash.js: the dashboard. Every folder in repo/ as a card with its state,
   and when evaluated the four verdict names, the hearts and the run summary
   (CONTRACT.md B1); drop folders / clone a URL (B2). From rush00's dash.html. */

"use strict";

const DASH_SKIP = new Set(["node_modules", ".DS_Store", ".git"]);
const DASH_MAX_BYTES = 40 * 1024 * 1024;
const DASH_POLL_MS = 1500;

/* the stamp: the eval sheet's outcome (page_sheet), never a grade; our
   bank is shown apart as "extra checks" */
function dash_stamp(team)
{
	const s = team.summary;

	if (PAGE_BUSY.indexOf(team.status) >= 0)
		return {cls: "na", text: team.status, small: "", busy: true};
	if (team.status === "error")
		return {cls: "bad", text: "error", small: "see below", busy: false};
	if (!s)
		return {cls: "na", text: "new", small: "not evaluated", busy: false};
	const sh = page_sheet(s);
	return {cls: sh.cls, text: sh.text, small: sh.small, busy: false};
}

/* our bank: "extra checks", a count of facts, not part of the sheet */
function dash_extra_html(s, cls_prefix)
{
	const x = page_extra(s.groups);
	const total = x.pass + x.fail;
	const pct = total ? Math.round(100 * x.pass / total) : 0;

	if (!total)
		return `<span class="${cls_prefix} na"></span>`;
	return `<span class="${cls_prefix} ${x.fail ? "bad" : "ok"}" `
		+ `title="our extra checks (not the eval sheet): ${x.pass} of ${total} pass">`
		+ `<span class="mini"><i style="width:${pct}%"></i></span>`
		+ `<b>${x.pass}/${total}</b></span>`;
}

function dash_chips(parts)
{
	let out = "";

	for (const part of PAGE_PARTS)
	{
		const v = parts[part];
		const cls = page_conf_class(v.confidence);
		let name = page_esc(v.name);

		if (v.confidence === "unrecognized")
			name = "? unrecognized";
		else if (v.also.length)
			name += ` <i>+ ${v.also.length} more</i>`;
		out += `<div class="vchip ${cls}"><b>${PAGE_PART_LABEL[part]}</b>`
			+ `<span class="vn">${name}</span>`
			+ `<span class="cw">${page_esc(v.confidence)}</span></div>`;
	}
	return out;
}

function dash_groups(groups)
{
	let out = "";

	for (const group of page_group_order(Object.keys(groups)))
	{
		const c = groups[group];
		const total = c.pass + c.fail;
		let cls = "ok";
		let pct = 0;

		if (total === 0)
		{
			out += `<div class="stg na"><span class="rn">${page_esc(page_group_label(group))}</span>`
				+ "<span class=\"track\"></span>"
				+ `<span class="sc">${c.info} info</span></div>`;
			continue;
		}
		if (c.fail > 0)
			cls = "bad";
		pct = Math.round(100 * c.pass / total);
		out += `<div class="stg ${cls}"><span class="rn">${page_esc(page_group_label(group))}</span>`
			+ `<span class="track"><i style="width:${pct}%"></i></span>`
			+ `<span class="sc">${c.pass}/${total}</span></div>`;
	}
	return out;
}

function dash_card(team, index, count)
{
	const s = team.summary;
	const st = dash_stamp(team);
	const enc = encodeURIComponent(team.name);
	let body = "";
	let acts = "";

	/* 1. the evaluated part: verdicts, hearts, runs, diagnosis */
	if (s)
	{
		const line = page_diagnosis_line(s.diagnosis);

		body += page_stop_lines(s.stops);
		body += `<div class="vchips">${dash_chips(s.parts)}</div>`;
		body += "<div class=\"row2\"><div><p class=\"lab\">LIVES</p>"
			+ `<div class="hearts">${page_hearts(s.built, s.forbidden, s.norm)}`
			+ "</div></div></div>";
		if (Object.keys(s.groups).length)
		{
			body += "<div class=\"stages\"><p class=\"lab\">RUNS "
				+ "<span class=\"hint\">(eliminatory = the sheet; the rest = "
				+ "our extra checks)</span></p>"
				+ dash_groups(s.groups) + "</div>";
		}
		if (line)
			body += `<p class="diag ${line.cls}">${page_esc(line.text)}</p>`;
		if (s.bonus && s.bonus.largest_n)
		{
			body += `<p class="diag ${s.bonus.counted ? "ok" : "na"}">bonus: up to `
				+ `${s.bonus.largest_n}x${s.bonus.largest_n}`
				+ (s.bonus.counted ? "" : " (not counted)") + "</p>";
		}
		if (s.detect_error)
		{
			body += "<p class=\"diag na\">detect crashed: "
				+ `${page_esc(s.detect_error)}</p>`;
		}
	}
	/* 2. what went wrong, folded */
	if (team.error)
	{
		body += "<details class=\"err\"><summary>what went wrong</summary>"
			+ `<pre>${page_esc(team.error)}</pre></details>`;
	}
	/* 3. actions: a clone in progress has no folder yet */
	if (team.url === undefined)
	{
		if (s)
			acts += `<a class="btn go" href="/team/${enc}">&#9654; Open</a>`;
		acts += "<button class=\"btn\" type=\"button\" data-act=\"rerun\">"
			+ "Re-run</button>";
	}
	else
		acts += `<span class="hint">${page_esc(team.url)}</span>`;
	return "<span class=\"tape c\"></span><div class=\"top\"><div class=\"who\">"
		+ `<div class="kick">TEAM ${index + 1}/${count}</div>`
		+ `<h2 class="name">${page_esc(team.name)}</h2>`
		+ `<div class="why">${s && s.made_at ? "evaluated "
			+ page_esc(s.made_at.replace("T", " ")) : ""}</div></div>`
		+ `<div class="stamp ${st.cls}">${st.busy ? "<span class=\"spin\"></span> " : ""}`
		+ `${page_esc(st.text)}<small>${page_esc(st.small)}</small></div></div>`
		+ body + `<div class="acts">${acts}</div>`;
}

/* ---- the team select: list, select or cards; search, filters ---------- */

const DASH_VIEWS = ["list", "select", "cards"];
const DASH_FILTERS = [
	["all", "all"], ["stop", "stopped"], ["ok", "sheet OK"],
	["extra", "extra fails"], ["new", "not evaluated"]];
const dash = {state: null, view: "list", filter: "all", find: "",
	cursor: null, drawn: null};
const dash_seen = {};

/* which filters a team falls in (besides "all") */
function dash_kinds(team)
{
	const s = team.summary;
	const kinds = new Set(["all"]);
	const st = dash_stamp(team);

	if (!s || st.busy || team.status === "error")
		kinds.add("new");
	if (s && !st.busy)
	{
		const sh = page_sheet(s);

		if (sh.cls === "bad")
			kinds.add("stop");
		if (sh.cls === "ok")
			kinds.add("ok");
		if (page_extra(s.groups).fail > 0)
			kinds.add("extra");
	}
	return kinds;
}

function dash_shown(team)
{
	const q = dash.find.trim().toLowerCase();

	if (q && team.name.toLowerCase().indexOf(q) < 0)
		return false;
	return dash_kinds(team).has(dash.filter);
}

function dash_row(team, index)
{
	const s = team.summary;
	const st = dash_stamp(team);
	const enc = encodeURIComponent(team.name);
	let elim = "<span class=\"r-el na\" title=\"not in this report: re-run\">–</span>";
	let runs = "<span class=\"r-runs na\"></span>";
	let parts = "";
	let flags = "";
	let act = "";

	if (s)
	{
		const e = s.groups.evalsheet;

		if (e && e.pass + e.fail)
		{
			elim = `<span class="r-el ${e.fail ? "bad" : "ok"}" title="eliminatory tests (eval sheet)">`
				+ `${e.pass}/${e.pass + e.fail}</span>`;
		}
		runs = dash_extra_html(s, "r-runs");
		for (const part of PAGE_PARTS)
		{
			const v = s.parts[part];
			const name = v.confidence === "unrecognized" ? "?" : v.name;

			parts += `<span class="r-part ${page_conf_class(v.confidence)}" `
				+ `title="${PAGE_PART_LABEL[part]}: ${page_esc(v.name)} (${page_esc(v.confidence)})">`
				+ `${page_esc(name)}</span>`;
		}
		flags = dash_flags(s);
	}
	if (team.status === "error")
		flags += `<span class="r-flag stop" title="${page_esc(team.error || "")}">error</span>`;
	if (team.url === undefined)
	{
		act = "<button class=\"btn small\" type=\"button\" data-act=\"rerun\" "
			+ "title=\"re-run this team\">&#8635;</button>";
	}
	const name = `<b title="${page_esc(team.name)}">${page_esc(team.name)}</b><small>${team.url !== undefined
		? page_esc(team.url) : s && s.made_at ? page_esc(s.made_at.replace("T", " ").slice(5, 16)) : ""}</small>`;
	const open = s && team.url === undefined
		? `<a class="r-name" href="/team/${enc}">${name}</a>`
		: `<span class="r-name">${name}</span>`;
	return `<span class="r-no">${index + 1}</span>${open}`
		+ `<span class="r-stamp ${st.cls}" title="${page_esc(st.small)}">`
		+ `${st.busy ? "<span class=\"spin\"></span> " : ""}`
		+ `${page_esc(st.text)}</span>${elim}${runs}`
		+ `<span class="r-parts">${parts}</span>`
		+ `<span class="r-flags">${flags}</span><span class="r-act">${act}</span>`;
}

/* the sheet's badges: STOP / check, and the bonus size */
function dash_flags(s)
{
	let flags = "";

	for (const x of s.stops || [])
	{
		flags += `<span class="r-flag ${x.level}" title="${page_esc(x.text)}">`
			+ `${x.level === "stop" ? "STOP" : "check"} `
			+ `${page_esc(page_stop_word(x.key))}</span>`;
	}
	if (s.bonus && s.bonus.largest_n)
	{
		flags += `<span class="r-flag bonus${s.bonus.counted ? "" : " off"}" `
			+ `title="${page_esc(s.bonus.note || "bonus counted")}">bonus `
			+ `${s.bonus.largest_n}x${s.bonus.largest_n}</span>`;
	}
	return flags;
}

function dash_counts(teams)
{
	const counts = {};

	for (const [key] of DASH_FILTERS)
		counts[key] = 0;
	for (const t of teams)
	{
		for (const k of dash_kinds(t))
			counts[k]++;
	}
	page_q("#filters").innerHTML = DASH_FILTERS.map(function ([key, label])
	{
		return `<button class="btn small${dash.filter === key ? " on" : ""}" `
			+ `type="button" data-filter="${key}"${counts[key] || key === "all" ? ""
				: " disabled"}>${label} <i>${counts[key]}</i></button>`;
	}).join("");
}

function dash_render(state)
{
	dash.state = state;
	dash_draw();
}

function dash_shown_teams()
{
	return dash.state ? dash.state.teams.filter(dash_shown) : [];
}

/* the cursor (arrow keys, the select view's preview) stays on a shown team */
function dash_fix_cursor()
{
	const shown = dash_shown_teams();

	if (!shown.some(function (t)
	{
		return t.name === dash.cursor;
	}))
		dash.cursor = dash.view === "select" && shown.length ? shown[0].name : null;
}

function dash_draw()
{
	const state = dash.state;
	const box = page_q("#teams");
	let ok = 0;

	if (!state)
		return;
	const teams = state.teams;
	/* 1. header: where teams live, how many the sheet lets through */
	page_q("#repo").textContent = state.repo_dir_abs;
	for (const t of teams)
	{
		if (t.summary && page_sheet(t.summary).cls === "ok")
			ok++;
	}
	const pct = teams.length ? Math.round(100 * ok / teams.length) : 0;
	page_q("#hud").innerHTML = "<span class=\"lv\">RUSH 01</span>"
		+ "<span class=\"lbl\">SHEET OK</span>"
		+ `<span class="n">${ok}/${teams.length}</span>`
		+ `<span class="bar"><i style="width:${pct}%"></i></span>`;
	dash_counts(teams);
	dash_fix_cursor();
	/* 2. a new view starts from an empty box */
	if (dash.drawn !== dash.view)
	{
		box.innerHTML = "";
		for (const k of Object.keys(dash_seen))
			delete dash_seen[k];
		dash.drawn = dash.view;
	}
	box.className = "teams " + dash.view;
	page_q("#thead").hidden = dash.view !== "list" || !teams.length;
	/* 3. no teams yet */
	if (!teams.length)
	{
		box.innerHTML = "<div class=\"card\"><span class=\"tape c\"></span>"
			+ "<h2 class=\"name marker\">No teams yet</h2><p class=\"empty\">"
			+ "Drop a team folder on the page to start.</p></div>";
		dash.drawn = null;
		page_q("#nomatch").hidden = true;
		return;
	}
	if (box.querySelector(".empty"))
		box.innerHTML = "";
	const shown = dash.view === "select" ? dash_draw_select(box, teams)
		: dash_draw_items(box, teams);
	page_q("#nomatch").hidden = shown > 0;
}

/* list and cards: one element per team, redrawn only when its data changed */
function dash_draw_items(box, teams)
{
	const names = new Set();
	let shown = 0;

	teams.forEach(function (t, i)
	{
		let el = box.querySelector(`:scope > [data-team="${CSS.escape(t.name)}"]`);
		const hash = JSON.stringify([dash.view, t, i, teams.length]);

		names.add(t.name);
		if (!el)
		{
			el = document.createElement("article");
			el.dataset.team = t.name;
		}
		if (box.children[i] !== el)
			box.insertBefore(el, box.children[i] || null);
		if (dash_seen[t.name] !== hash)
		{
			dash_seen[t.name] = hash;
			if (dash.view === "list")
			{
				el.className = "trow";
				el.innerHTML = dash_row(t, i);
			}
			else
			{
				el.className = "card team r" + (1 + i % 3);
				el.innerHTML = dash_card(t, i, teams.length);
			}
		}
		el.classList.toggle("on", t.name === dash.cursor);
		el.hidden = !dash_shown(t);
		shown += el.hidden ? 0 : 1;
	});
	for (const el of Array.from(box.children))
	{
		if (!names.has(el.dataset.team))
		{
			delete dash_seen[el.dataset.team];
			el.remove();
		}
	}
	return shown;
}

/* select: the roster on the left (arrow keys), the picked team on the right */
function dash_draw_select(box, teams)
{
	const shown = dash_shown_teams();
	const hash = JSON.stringify([teams, dash.cursor, dash.filter, dash.find]);

	if (dash_seen["\u0000select"] === hash)
		return shown.length;
	dash_seen["\u0000select"] = hash;
	const old = page_q(".sel-roster ol", box);
	const scroll = old ? old.scrollTop : 0;
	const items = shown.map(function (t)
	{
		const st = dash_stamp(t);
		const mark = {ok: "✓", bad: "✗"}[st.cls] || "·";

		return `<li data-pick="${page_esc(t.name)}"${t.name === dash.cursor ? " class=\"on\"" : ""}>`
			+ `<span class="mk ${st.cls}">${mark}</span>`
			+ `<span class="nm">${page_esc(t.name)}</span>`
			+ `<span class="rs ${st.cls}">${page_esc(st.text)}</span></li>`;
	}).join("");
	const pick = teams.find(function (t)
	{
		return t.name === dash.cursor;
	});
	const i = pick ? teams.indexOf(pick) : -1;
	box.innerHTML = "<div class=\"card r1 roster sel-roster\"><span class=\"tape l\"></span>"
		+ `<div class="head"><h3>Teams</h3><span class="n">${shown.length}</span></div>`
		+ `<ol>${items}</ol>`
		+ "<p class=\"keys\"><kbd>↑</kbd> <kbd>↓</kbd> pick · <kbd>Enter</kbd> open "
		+ "· <kbd>/</kbd> find</p></div>"
		+ (pick ? `<article class="card team r2 sel-preview" data-team="${page_esc(pick.name)}">`
			+ dash_card(pick, i, teams.length) + "</article>"
			: "<div class=\"sel-preview\"></div>");
	page_q(".sel-roster ol", box).scrollTop = scroll;
	const on = page_q(".sel-roster li.on", box);
	if (on)
		dash_keep_visible(on, page_q(".sel-roster ol", box));
	return shown.length;
}

function dash_keep_visible(el, list)
{
	const r = el.getBoundingClientRect();
	const lr = list.getBoundingClientRect();

	if (r.top < lr.top)
		list.scrollTop -= lr.top - r.top;
	else if (r.bottom > lr.bottom)
		list.scrollTop += r.bottom - lr.bottom;
}

/* ↑ / ↓ move the cursor through the shown teams */
function dash_move(step)
{
	const shown = dash_shown_teams();
	let i = shown.findIndex(function (t)
	{
		return t.name === dash.cursor;
	});

	if (!shown.length)
		return;
	i = i < 0 ? (step > 0 ? 0 : shown.length - 1)
		: Math.min(shown.length - 1, Math.max(0, i + step));
	dash.cursor = shown[i].name;
	dash_draw();
	if (dash.view !== "select")
	{
		const el = page_q(`#teams > [data-team="${CSS.escape(dash.cursor)}"]`);
		if (el)
			el.scrollIntoView({block: "nearest"});
	}
}

/* Enter: the cursor's team, else the first one shown */
function dash_open()
{
	const shown = dash_shown_teams().filter(function (t)
	{
		return t.summary && t.url === undefined;
	});
	const pick = shown.find(function (t)
	{
		return t.name === dash.cursor;
	}) || shown[0];

	if (pick)
		location.href = "/team/" + encodeURIComponent(pick.name);
}

function dash_set(key, value)
{
	dash[key] = value;
	try
	{
		localStorage.setItem("rush01." + key, value);
	}
	catch (e)
	{
		/* private window: the choice lasts for this page only */
	}
	if (key === "view")
	{
		for (const b of document.querySelectorAll("[data-view]"))
			b.classList.toggle("on", b.dataset.view === value);
	}
	dash_draw();
}

/* list (default), select or cards; ?view= in the URL wins */
function dash_restore()
{
	const url = new URLSearchParams(location.search).get("view");
	let view = url;
	let filter = null;

	try
	{
		view = view || localStorage.getItem("rush01.view");
		filter = localStorage.getItem("rush01.filter");
	}
	catch (e)
	{
		view = view || null;
	}
	dash.view = DASH_VIEWS.indexOf(view) >= 0 ? view : "list";
	dash.filter = DASH_FILTERS.some(function ([k])
	{
		return k === filter;
	}) ? filter : "all";
	for (const b of document.querySelectorAll("[data-view]"))
		b.classList.toggle("on", b.dataset.view === dash.view);
}

/* keys: "/" find, ↑ ↓ move, Enter open, Esc clears the search */
function dash_find_keys()
{
	const find = page_q("#find");

	find.oninput = function ()
	{
		dash.find = find.value;
		dash_draw();
	};
	find.onkeydown = function (ev)
	{
		if (ev.key === "Escape")
		{
			find.value = "";
			dash.find = "";
			dash_draw();
			find.blur();
		}
		else if (ev.key === "Enter")
			dash_open();
		else if (ev.key === "ArrowDown" || ev.key === "ArrowUp")
		{
			ev.preventDefault();
			dash_move(ev.key === "ArrowDown" ? 1 : -1);
		}
	};
	document.addEventListener("keydown", function (ev)
	{
		const tag = (document.activeElement || {}).tagName;

		if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT")
			return;
		if (ev.key === "/")
		{
			ev.preventDefault();
			find.focus();
			find.select();
		}
		else if (ev.key === "ArrowDown" || ev.key === "ArrowUp")
		{
			ev.preventDefault();
			dash_move(ev.key === "ArrowDown" ? 1 : -1);
		}
		else if (ev.key === "Enter" && dash.cursor && tag !== "BUTTON"
			&& tag !== "A")
			dash_open();
	});
	page_q("#clearfind").onclick = function ()
	{
		find.value = "";
		dash.find = "";
		dash_set("filter", "all");
	};
	/* select view: a click on the roster picks, a double click opens */
	page_q("#teams").addEventListener("click", function (ev)
	{
		const li = ev.target.closest("[data-pick]");

		if (!li)
			return;
		dash.cursor = li.dataset.pick;
		dash_draw();
	});
	page_q("#teams").addEventListener("dblclick", function (ev)
	{
		if (ev.target.closest("[data-pick]"))
			dash_open();
	});
}

async function dash_refresh()
{
	try
	{
		dash_render(await page_api("/api/state"));
	}
	catch (e)
	{
		/* the server is restarting: try again on the next tick */
	}
}

/* ---- dropping folders (rush00's dash.html, same rules) ---------------- */

function dash_b64(buf)
{
	const bytes = new Uint8Array(buf);
	let s = "";

	for (let i = 0; i < bytes.length; i += 0x8000)
		s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
	return btoa(s);
}

async function dash_read_dir(dir_entry)
{
	const reader = dir_entry.createReader();
	const out = [];

	for (;;)
	{
		const batch = await new Promise(function (ok, bad)
		{
			reader.readEntries(ok, bad);
		});
		if (!batch.length)
			return out;
		out.push(...batch);
	}
}

async function dash_walk(entry, prefix, acc)
{
	if (DASH_SKIP.has(entry.name))
		return;
	if (entry.isFile)
	{
		const file = await new Promise(function (ok, bad)
		{
			entry.file(ok, bad);
		});
		acc.push({path: prefix + entry.name, file: file});
		return;
	}
	for (const child of await dash_read_dir(entry))
		await dash_walk(child, prefix + entry.name + "/", acc);
}

/* a dropped "ex00" is the exercise folder itself: ask for the team name */
function dash_team_name(dir_name)
{
	if (/^ex\d+$/i.test(dir_name))
	{
		const name = prompt(`"${dir_name}" looks like the exercise folder `
			+ "itself. Team name?") || "";
		return [name, dir_name + "/"];
	}
	return [dir_name, ""];
}

async function dash_upload(team, files, prefix)
{
	let total = 0;
	const payload = [];

	/* 1. check the size before reading anything */
	team = (team || "").trim();
	if (!team)
		return;
	for (const f of files)
		total += f.file.size;
	if (total > DASH_MAX_BYTES)
	{
		page_toast(`${team}: ${(total / 1e6).toFixed(1)} MB is too big`);
		return;
	}
	/* 2. send; an existing team is replaced only after asking */
	for (const f of files)
	{
		payload.push({path: prefix + f.path,
			b64: dash_b64(await f.file.arrayBuffer())});
	}
	try
	{
		await page_api("/api/upload", {team: team, files: payload});
	}
	catch (e)
	{
		if (e.status !== 409)
		{
			page_toast(e.message);
			return;
		}
		if (!confirm(`${team} already exists. Replace it? `
			+ "(the old copy goes to repo/.trash)"))
			return;
		await page_api("/api/upload", {team: team, files: payload,
			replace: true});
	}
	page_toast(`${team}: ${files.length} file(s) added`);
	dash_refresh();
}

async function dash_drop(ev)
{
	const loose = [];

	ev.preventDefault();
	const entries = Array.from(ev.dataTransfer.items).map(function (item)
	{
		return item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
	}).filter(Boolean);
	for (const entry of entries)
	{
		if (entry.isDirectory)
		{
			const acc = [];

			for (const child of await dash_read_dir(entry))
				await dash_walk(child, "", acc);
			const [name, prefix] = dash_team_name(entry.name);
			await dash_upload(name, acc, prefix);
		}
		else
		{
			const file = await new Promise(function (ok)
			{
				entry.file(ok);
			});
			loose.push({path: entry.name, file: file});
		}
	}
	if (loose.length)
	{
		const name = prompt("Team name for these files? "
			+ "(they go into <team>/ex00/)");
		if (name)
			await dash_upload(name, loose, "ex00/");
	}
}

async function dash_pick(ev)
{
	const groups = {};

	for (const f of ev.target.files)
	{
		const parts = f.webkitRelativePath.split("/");

		if (parts.some(function (p)
		{
			return DASH_SKIP.has(p);
		}))
			continue;
		if (!groups[parts[0]])
			groups[parts[0]] = [];
		groups[parts[0]].push({path: parts.slice(1).join("/"), file: f});
	}
	for (const [dir, files] of Object.entries(groups))
	{
		const [name, prefix] = dash_team_name(dir);

		await dash_upload(name, files, prefix);
	}
	ev.target.value = "";
}

function dash_main()
{
	const drop = page_q("#drop");

	page_theme();
	dash_restore();
	dash_find_keys();
	page_q("#filters").onclick = function (ev)
	{
		const b = ev.target.closest("[data-filter]");

		if (b)
			dash_set("filter", b.dataset.filter);
	};
	for (const b of document.querySelectorAll("[data-view]"))
	{
		b.onclick = function ()
		{
			dash_set("view", b.dataset.view);
		};
	}
	page_q("#addbtn").onclick = function ()
	{
		drop.hidden = !drop.hidden;
		this.setAttribute("aria-expanded", String(!drop.hidden));
		if (!drop.hidden)
			drop.querySelector("input[name=url]").focus();
	};
	/* 1. state, polled */
	setInterval(dash_refresh, DASH_POLL_MS);
	dash_refresh();
	/* 2. buttons */
	page_q("#teams").addEventListener("click", async function (ev)
	{
		const btn = ev.target.closest("[data-act]");

		if (!btn)
			return;
		const team = btn.closest("[data-team]").dataset.team;
		await page_api("/api/rerun", {team: team});
		dash_refresh();
	});
	page_q("#rerunall").onclick = async function ()
	{
		await page_api("/api/rerun", {all: true});
		dash_refresh();
	};
	page_q("#gitform").onsubmit = async function (ev)
	{
		const form = new FormData(ev.target);

		ev.preventDefault();
		try
		{
			const res = await page_api("/api/add", {url: form.get("url")});
			page_toast(`cloning ${res.team}…`);
			ev.target.reset();
			dash_refresh();
		}
		catch (e)
		{
			page_toast(e.message);
		}
	};
	/* 3. dropping folders anywhere */
	for (const name of ["dragenter", "dragover"])
	{
		document.addEventListener(name, function (ev)
		{
			ev.preventDefault();
			drop.hidden = false;
			drop.classList.add("over");
		});
	}
	document.addEventListener("dragleave", function (ev)
	{
		if (!ev.relatedTarget)
			drop.classList.remove("over");
	});
	document.addEventListener("drop", function (ev)
	{
		drop.classList.remove("over");
		dash_drop(ev);
	});
	page_q("#pick").onchange = dash_pick;
}

dash_main();
