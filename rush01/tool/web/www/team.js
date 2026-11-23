/* team.js: the team page (CONTRACT.md B3): the strip, the four part cards,
   the runs by group with the diagnosis line, the 3D view (sky3d.js), and
   the source + call graph. Reads /api/team/<name> and /api/source/<name>. */

"use strict";

const TEAM_POLL_MS = 2000;
const TEAM_ARGV_CAP = 48;
const TEAM_BROKEN_SHOWN = 4;

const team = {name: decodeURIComponent(location.pathname.slice(6)),
	made_at: null, names: {}, catalog: {}, files: {}, sky: null,
	deck: "defense"};

async function team_load()
{
	let data = null;

	/* 1. state + report */
	try
	{
		data = await page_api("/api/team/" + encodeURIComponent(team.name));
	}
	catch (e)
	{
		team_banner("bad", "Could not load this team: " + e.message);
		return;
	}
	page_q("#name").textContent = data.name;
	document.title = "Rush01 · " + data.name;
	team_status(data);
	/* 2. draw the report once per evaluation */
	const report = data.report;
	if (report && report.made_at !== team.made_at)
	{
		team.made_at = report.made_at;
		team_render(report);
	}
	/* 3. keep watching while it is being evaluated */
	if (PAGE_BUSY.indexOf(data.status) >= 0 || data.status === "new")
		setTimeout(team_load, TEAM_POLL_MS);
}

function team_banner(cls, text)
{
	const el = page_q("#banner");

	el.hidden = !text;
	el.className = "banner " + cls;
	el.textContent = text || "";
}

function team_status(data)
{
	if (data.status === "error")
	{
		team_banner("bad", "The last evaluation failed"
			+ (data.report ? " (the report below is the one before it)" : "")
			+ ": " + (data.error || "").split("\n").slice(-2).join(" "));
	}
	else if (PAGE_BUSY.indexOf(data.status) >= 0)
	{
		team_banner("na", data.status + "…"
			+ (data.report ? " the report below is the previous one" : ""));
	}
	else if (!data.report)
		team_banner("na", "Not evaluated yet.");
	else
		team_banner("", "");
}

function team_render(report)
{
	const judge = report.judge;
	const sh = page_sheet({built: judge.built, stops: judge.stops,
		groups: judge.groups});
	const x = page_extra(judge.groups);

	/* 1. header and HUD: the sheet's outcome first, our bank apart */
	page_q("#sub").textContent = "evaluated " + report.made_at.replace("T", " ")
		+ " · " + report.team_dir_abs;
	page_q("#hud").innerHTML = "<span class=\"lv\">SHEET</span>"
		+ `<span class="n ${sh.cls}" title="${page_esc(sh.small)}">${page_esc(sh.text)}</span>`
		+ "<span class=\"lbl\" title=\"our own bank, not the eval sheet\">EXTRA</span>"
		+ `<span class="n x">${x.pass}/${x.pass + x.fail}</span>`;
	/* 2. the gates, the hero (3D + loadout), the deck */
	for (const id of ["#gatebox", "#hero", "#deck-tabs", "#sheet", "#strip",
		"#parts", "#runs", "#source"])
		page_q(id).hidden = false;
	team_gates(report);
	page_q("#loadout").innerHTML = team_loadout(report);
	page_q("#sheet").innerHTML = team_sheet(report);
	page_q("#strip").innerHTML = team_strip(report);
	page_q("#parts").innerHTML = PAGE_PARTS.map(function (part, i)
	{
		return team_part(part, report.detect.parts[part], i);
	}).join("");
	page_q("#runs").innerHTML = team_runs(judge);
	team_deck_counts(report, x);
	team_deck(team.deck);
	team.sky = sky_mount(page_q("#skybox"), judge.runs);
	team_source();
	/* 3. the names of the "also" entries come from the catalog */
	team_catalog();
}

/* ---- the gates: the eval sheet in its order --------------------------------- */

/* one gate per step of the sheet; state "ok" / "stop" / "check" / "na";
   goto: where its detail lives */
function team_gate_list(report)
{
	const judge = report.judge;
	const stops = judge.stops || [];
	const by = {};
	const gates = [];

	for (const st of stops)
		by[st.key] = st;
	/* 1. turn-in: a folder, sources, no extra files */
	const turn = by.no_ex_dir || by.no_sources;
	gates.push({title: "Turn-in", goto: "strip",
		state: turn ? "stop" : by.files ? "check" : "ok",
		text: turn ? turn.text : by.files ? by.files.text
			: `${judge.ex_dir}/ · ${judge.files.sources.length} .c file(s)`});
	/* 2. norm */
	const norm = judge.norm;
	gates.push({title: "Norminette", goto: "norm",
		state: by.norm ? "stop" : norm.ran ? "ok" : "na",
		text: by.norm ? by.norm.text : norm.ran ? "no errors"
			: "skipped: " + (norm.note || "not run")});
	/* 3. build */
	gates.push({title: "Build", goto: "strip",
		state: judge.built ? "ok" : "stop",
		text: judge.built ? "builds with -Wall -Wextra -Werror"
			: (by.build ? by.build.text : "does not build")});
	/* 4. allowed calls: the subject's rule, a check */
	gates.push({title: "Allowed calls", goto: "strip",
		state: by.forbidden ? "check" : "ok",
		text: by.forbidden ? by.forbidden.text : "allowed functions only"});
	/* 5. the six eliminatory tests */
	const e = judge.groups.evalsheet;
	if (e && e.pass + e.fail)
	{
		gates.push({title: "Eliminatory", goto: "group:evalsheet",
			state: e.fail ? "stop" : "ok",
			text: `${e.pass}/${e.pass + e.fail} pass`
				+ (e.fail ? ": no points" : "")});
	}
	else
	{
		gates.push({title: "Eliminatory", goto: "group:evalsheet", state: "na",
			text: judge.built ? "not run: re-run" : "no binary"});
	}
	/* 6. malloc made to fail */
	const m = judge.malloc_fail;
	if (m && m.crashes && m.crashes.length)
	{
		gates.push({title: "Malloc break", goto: "malloc", state: "stop",
			text: "Crash on malloc #" + m.crashes.join(", #")});
	}
	else if (m && m.ran && m.mallocs)
	{
		gates.push({title: "Malloc break", goto: "malloc", state: "ok",
			text: `${m.tries.length} tried, none broke it`});
	}
	else
	{
		gates.push({title: "Malloc break", goto: "malloc", state: "na",
			text: m ? m.note || "skipped" : "not run: re-run"});
	}
	/* 7. bonus */
	const bo = judge.bonus;
	if (bo && bo.largest_n)
	{
		gates.push({title: "Bonus", goto: "group:bonusN",
			state: bo.counted ? "ok" : "na",
			text: `up to ${bo.largest_n}x${bo.largest_n}`
				+ (bo.counted ? "" : " · not counted")});
	}
	else
	{
		gates.push({title: "Bonus", goto: "group:bonusN", state: "na",
			text: bo ? (Object.keys(bo.sizes).length ? "5x5 fails" : bo.note)
				: "not run: re-run"});
	}
	return gates;
}

function team_gates(report)
{
	const gates = team_gate_list(report);
	const first = gates.findIndex(function (g)
	{
		return g.state === "stop";
	});

	page_q("#gates").innerHTML = gates.map(function (g, i)
	{
		const after = first >= 0 && i > first ? " after" : "";
		const word = {ok: "✓", stop: "STOP", check: "check", na: "—"}[g.state];

		return `<li><button class="gate ${g.state}${after}" type="button" `
			+ `data-goto="${page_esc(g.goto)}" title="${page_esc(g.text)}">`
			+ `<span class="gn">GATE ${i + 1}${after ? " · after stop" : ""}</span>`
			+ `<span class="gt">${page_esc(g.title)}</span>`
			+ `<span class="gs">${word} · ${page_esc(g.text)}</span></button></li>`;
	}).join("");
	page_q("#gates-note").textContent = first >= 0
		? `The sheet stops at gate ${first + 1}. The gates after it were run `
			+ "anyway: their results are facts, not points."
		: "Nothing stops the evaluation. Click a gate for its detail.";
}

/* ---- the loadout: hearts and the four parts, beside the 3D view ----------- */

function team_loadout(report)
{
	const judge = report.judge;
	const names = Array.from(new Set(judge.forbidden.names.map(function (x)
	{
		return x.name;
	})));
	const line = page_diagnosis_line(judge.diagnosis);
	let out = "<span class=\"tape c\"></span><h3>Team build</h3>"
		+ `<div class="hearts">${page_hearts(judge.built, names, judge.norm)}</div>`
		+ "<div class=\"slots\">";

	for (const part of PAGE_PARTS)
	{
		const v = report.detect.parts[part];
		const cls = page_conf_class(v.confidence);
		const unrec = v.confidence === "unrecognized";
		let acts = "";

		if (!unrec && v.id)
		{
			acts = `<button class="btn small" type="button" data-demo="${page_esc(v.id)}">`
				+ "&#9654; how it works</button>";
		}
		if (v.where.length)
		{
			const w = v.where[0];
			acts += team_where_link(w.file, w.line, `${w.file}:${w.line}`);
		}
		out += `<div class="slot ${cls}"><span class="sl-part">${PAGE_PART_LABEL[part].toUpperCase()}</span>`
			+ `<button class="sl-name" type="button" data-slot="${part}" title="evidence and questions">`
			+ `${unrec ? "? unrecognized" : page_esc(v.name)}</button>`
			+ `<span class="sl-meta"><span class="conf ${cls}">${page_esc(v.confidence)}</span>`
			+ (v.tier !== null && v.tier !== undefined ? `<span class="tier">T${v.tier}</span>` : "")
			+ "</span>"
			+ (acts ? `<span class="sl-acts">${acts}</span>` : "") + "</div>";
	}
	out += "</div>";
	if (line)
		out += `<p class="diag ${line.cls}">${page_esc(line.text)}</p>`;
	return out;
}

/* ---- the deck: Defense / Runs / Source / All ------------------------------ */

const TEAM_DECKS = ["defense", "runs", "source", "all"];

function team_deck_counts(report, x)
{
	const ask = (report.detect.project.ask || []).length;
	const label = {defense: `Defense <i>${ask} to ask</i>`,
		runs: `Runs <i>extra ${x.pass}/${x.pass + x.fail}</i>`,
		source: "Source", all: "All"};

	for (const b of document.querySelectorAll("[data-deck]"))
		b.innerHTML = label[b.dataset.deck];
}

function team_deck(name)
{
	team.deck = TEAM_DECKS.indexOf(name) >= 0 ? name : "defense";
	try
	{
		localStorage.setItem("rush01.deck", team.deck);
	}
	catch (e)
	{
		/* private window */
	}
	for (const b of document.querySelectorAll("[data-deck]"))
		b.classList.toggle("on", b.dataset.deck === team.deck);
	let first = true;
	for (const sec of document.querySelectorAll("[data-panel]"))
	{
		const shown = team.deck === "all" || sec.dataset.panel === team.deck;

		sec.style.display = shown ? "" : "none";
		/* the first panel shown joins the open tab */
		sec.classList.toggle("deck-first", shown && first);
		if (shown)
			first = false;
	}
}

/* show the panel an element lives in (unless "All"), then scroll to it */
function team_reveal(el, flash)
{
	const panel = el.closest("[data-panel]");

	if (panel && team.deck !== "all" && panel.dataset.panel !== team.deck)
		team_deck(panel.dataset.panel);
	el.scrollIntoView({block: "start"});
	window.scrollBy(0, -60);
	if (flash)
	{
		el.classList.remove("flash");
		void el.offsetWidth;
		el.classList.add("flash");
	}
}

function team_gate_goto(where)
{
	let el = null;

	if (where.indexOf("group:") === 0)
	{
		el = page_q(`details.group[data-group="${CSS.escape(where.slice(6))}"]`);
		if (el)
			el.open = true;
	}
	else if (where === "norm")
	{
		el = page_q("#strip details.norm") || page_q("#strip");
		if (el.tagName === "DETAILS")
			el.open = true;
	}
	else if (where === "malloc")
		el = page_q("#sheet-malloc") || page_q("#sheet");
	else
		el = page_q("#" + where);
	if (el)
		team_reveal(el, true);
}

/* ---- the eval sheet -------------------------------------------------------- */

const TEAM_ASK_KIND = {shift: "bit shift", complex: "complex", recursion: "recursion",
	malloc: "malloc"};

function team_sheet(report)
{
	const judge = report.judge;
	const sub = report.subject;
	const stops = judge.stops || [];
	const elim = judge.groups.evalsheet;
	const ask = report.detect.project.ask || [];
	let out = "<span class=\"tape r\"></span><h3>Eval sheet: details</h3>";

	/* 1. preliminaries: what stops the evaluation, in the sheet's order */
	if (stops.length)
		out += page_stop_lines(stops);
	else
		out += "<p class=\"diag ok\">Preliminaries: nothing stops the evaluation.</p>";
	/* 2. eliminatory tests: the sheet's six inputs, word for word */
	if (elim)
	{
		const total = elim.pass + elim.fail;

		out += `<p class="diag ${elim.fail ? "warn" : "ok"}">Eliminatory tests: `
			+ `${elim.pass}/${total} pass`
			+ (elim.fail ? " (the sheet: no points)" : "") + "</p>";
	}
	/* 3. malloc made to fail: the sheet's "break their program" */
	out += `<div id="sheet-malloc">${team_malloc_fail(judge.malloc_fail)}</div>`;
	/* 4. bonus: the largest size, counted only when all else passed */
	if (judge.bonus && Object.keys(judge.bonus.sizes).length)
	{
		const b = judge.bonus;
		const sizes = Object.entries(b.sizes).map(function (kv)
		{
			return `${kv[0]}x${kv[0]} ${kv[1]}`;
		}).join(" · ");

		out += `<p class="diag ${b.counted && b.largest_n ? "ok" : "na"}">Bonus: `
			+ (b.largest_n ? `up to ${b.largest_n}x${b.largest_n}` : "none")
			+ (b.note ? ` · ${page_esc(b.note)}` : "")
			+ `</p><p class="hint">${page_esc(sizes)}</p>`;
	}
	/* 5. lines to ask about (the sheet's Explanation) */
	if (ask.length)
	{
		out += "<p class=\"lab\">LINES TO ASK ABOUT</p><ul class=\"asks\">"
			+ ask.map(function (a)
			{
				return `<li><span class="fact ${a.kind === "malloc" ? "warn" : ""}">`
					+ `${page_esc(TEAM_ASK_KIND[a.kind] || a.kind)}</span> `
					+ team_where_link(a.file, a.line, `${a.file}:${a.line}`)
					+ ` <code>${page_esc(a.text)}</code>`
					+ `<br><span class="hint">${page_esc(a.why)}</span></li>`;
			}).join("") + "</ul>";
	}
	else
		out += "<p class=\"hint\">No bit shifts, complex lines, recursion or "
			+ "unchecked malloc found.</p>";
	/* 6. the sheet's binary name vs the subject's */
	if (sub.sheet_binary && sub.sheet_binary !== sub.binary)
	{
		out += `<p class="hint">The sheet runs <code>./${page_esc(sub.sheet_binary)}</code>; `
			+ `the subject builds <code>${page_esc(sub.binary)}</code> (used here).</p>`;
	}
	return out;
}

function team_malloc_fail(m)
{
	if (!m)
		return "";
	if (!m.ran || !m.mallocs)
		return `<p class="hint">malloc made to fail: ${page_esc(m.note || "skipped")}</p>`;
	if (!m.crashes.length)
	{
		return `<p class="diag ok">malloc made to fail: ${m.tries.length} of `
			+ `${m.mallocs} tried, none broke it</p>`
			+ (m.note ? `<p class="hint">${page_esc(m.note)}</p>` : "");
	}
	const how = m.tries.filter(function (t)
	{
		return m.crashes.indexOf(t.nth) >= 0;
	}).map(function (t)
	{
		return `#${t.nth} ${t.signal || t.outcome}`;
	}).join(" · ");
	return `<p class="diag warn">malloc made to fail: it breaks (${page_esc(how)}): `
		+ "Crash (sheet)</p>"
		+ (m.note ? `<p class="hint">${page_esc(m.note)}</p>` : "");
}

/* ---- the strip ------------------------------------------------------------ */

function team_fact(cls, text, title)
{
	return `<span class="fact ${cls}" title="${page_esc(title || "")}">`
		+ `${text}</span>`;
}

function team_where_link(file, line, label)
{
	return `<a class="ln" href="#" data-file="${page_esc(file)}" `
		+ `data-line="${line || ""}">${page_esc(label)}</a>`;
}

function team_strip(report)
{
	const judge = report.judge;
	const project = report.detect.project;
	const names = judge.forbidden.names.map(function (x)
	{
		return x.name;
	});
	const facts = [];
	let out = "<span class=\"tape l\"></span><h3>Project</h3>";

	/* 1. hearts */
	out += `<div class="hearts">${page_hearts(judge.built,
		Array.from(new Set(names)), judge.norm)}</div>`;
	/* 2. files */
	if (judge.files.no_ex_dir)
		facts.push(team_fact("warn", "no ex00/: the root was judged"));
	else
		facts.push(team_fact("", "turn-in: " + page_esc(judge.ex_dir) + "/"));
	for (const f of judge.files.flagged)
		facts.push(team_fact("warn", page_esc(f.path + ": " + f.why)));
	/* 3. forbidden calls and the compiler's own */
	for (const x of judge.forbidden.names)
	{
		let where = "in the binary (nm -u)";

		if (x.where === "source")
			where = team_where_link(x.file, x.line, `${x.file}:${x.line}`);
		facts.push(team_fact("warn", `forbidden <code>${page_esc(x.name)}</code> `
			+ where));
	}
	for (const note of judge.forbidden.notes)
		facts.push(team_fact("", page_esc(note)));
	/* 4. what detect found in the project */
	for (const g of project.globals)
	{
		facts.push(team_fact("", "global "
			+ team_where_link(g.file, g.line, g.text)));
	}
	for (const s of project.structs)
	{
		facts.push(team_fact("", "struct "
			+ team_where_link(s.file, s.line, s.name)));
	}
	facts.push(team_fact("", `${project.functions} functions`));
	if (project.longest)
	{
		facts.push(team_fact("", "longest "
			+ team_where_link(project.longest.file, null,
				project.longest.name + "()")
			+ ` ${project.longest.lines} lines`));
	}
	if (project.never_freed)
		facts.push(team_fact("warn", "malloc'd memory is never freed"));
	if (project.bonus)
		facts.push(team_fact("", "bonus sizes attempted"));
	/* 5. sanitizer, authors, the timing cross-check */
	facts.push(team_sanitizer(judge.sanitizer));
	if (project.authors)
	{
		const who = Object.entries(project.authors).map(function (kv)
		{
			return page_esc(kv[0]) + " " + kv[1] + "%";
		}).join(" · ");
		facts.push(team_fact("", `lines by ${who} · ${project.commits} commits`));
	}
	else
		facts.push(team_fact("na", "authors: not a git repo"));
	for (const line of report.cross_check)
		facts.push(team_fact("warn", page_esc(line)));
	for (const [tool, has] of Object.entries(judge.tools))
	{
		if (!has)
			facts.push(team_fact("na", page_esc(tool) + ": not installed"));
	}
	out += `<div class="facts strip">${facts.join("")}</div>`;
	/* 6. the build log and the norm errors, folded */
	if (!judge.built)
	{
		out += "<details class=\"err\" open><summary>the build failed</summary>"
			+ `<pre>${page_esc(judge.build_log)}</pre></details>`;
	}
	out += team_norm(judge.norm);
	if (report.detect.error)
	{
		out += "<details class=\"err\"><summary>detect crashed</summary>"
			+ `<pre>${page_esc(report.detect.error)}</pre></details>`;
	}
	return out;
}

function team_sanitizer(san)
{
	if (!san.ran)
		return team_fact("na", "sanitizer: " + page_esc(san.note || "skipped"));
	if (!san.findings.length)
	{
		return team_fact("ok", "sanitizer: no findings"
			+ (san.note ? " · " + page_esc(san.note) : ""));
	}
	return san.findings.map(function (f)
	{
		return team_fact("warn", `sanitizer: ${page_esc(f.kind)} on `
			+ `<code>${page_esc(f.case)}</code>`, f.text);
	}).join("");
}

function team_norm(norm)
{
	if (!norm.ran)
	{
		return `<p class="hint">norminette: ${page_esc(norm.note || "skipped")}`
			+ "</p>";
	}
	if (norm.ok)
		return "";
	const rows = norm.errors.map(function (e)
	{
		return "<li>" + team_where_link(e.file, e.line, `${e.file}:${e.line}`)
			+ " " + page_esc(e.text) + "</li>";
	}).join("");
	const count = norm.note ? page_esc(norm.note)
		: `${norm.errors.length} error${norm.errors.length === 1 ? "" : "s"}`;
	return `<details class="norm"><summary>norminette: ${count}</summary><ul>${rows}`
		+ "</ul></details>";
}

/* ---- the four part cards ------------------------------------------------- */

function team_part(part, v, i)
{
	const cls = page_conf_class(v.confidence);
	const tilt = ["r1", "r2", "r3", "r2"][i];
	let head = "";
	let body = "";

	/* 1. the verdict; "unrecognized" never looks like one */
	if (v.confidence === "unrecognized")
	{
		head = "<h3 class=\"vname unrec\">? unrecognized</h3>"
			+ "<div class=\"vmeta\"><span class=\"conf c-unrecognized\">"
			+ "unrecognized</span><span class=\"hint\">the tool can't tell: "
			+ "read the code</span></div>";
	}
	else
	{
		let also = "";
		if (v.also.length)
		{
			also = v.also.map(function (id)
			{
				return `<span class="also" data-id="${page_esc(id)}">`
					+ `+ ${page_esc(team.names[id] || id)}</span>`;
			}).join("");
		}
		head = `<h3 class="vname">${page_esc(v.name)}</h3>${also}`
			+ `<div class="vmeta"><span class="conf ${cls}">`
			+ `${page_esc(v.confidence)}</span>`
			+ (v.tier !== null && v.tier !== undefined
				? `<span class="tier">tier ${v.tier}</span>` : "")
			+ `<code class="vid">${page_esc(v.id)}</code></div>`;
	}
	/* 2. where, then 2-5 evidence lines */
	if (v.where.length)
	{
		const links = v.where.map(function (w)
		{
			const label = (w.func ? w.func + "() · " : "") + `${w.file}:${w.line}`;
			return team_where_link(w.file, w.line, label);
		}).join(", ");
		const word = v.confidence === "unrecognized" ? "look at" : "in";
		body += `<p class="where">${word} ${links}</p>`;
	}
	if (v.evidence.length)
	{
		body += "<ul class=\"evidence\">" + v.evidence.map(function (e)
		{
			return "<li>" + team_where_link(e.file, e.line,
				e.file.split("/").pop() + ":" + e.line)
				+ `<code>${page_esc(e.text)}</code>`
				+ `<span class="why">${page_esc(e.why)}</span></li>`;
		}).join("") + "</ul>";
	}
	/* 3. facts, the explanation, the folded defense questions */
	if (v.facts.length)
	{
		body += "<div class=\"facts\">" + v.facts.map(function (f)
		{
			return team_fact("", page_esc(f.text), f.key);
		}).join("") + "</div>";
	}
	if (v.explain)
		body += `<p class="explain">${page_esc(v.explain)}</p>`;
	if (v.confidence !== "unrecognized" && v.id)
	{
		let btns = `<button class="btn small demo-btn" type="button" `
			+ `data-demo="${page_esc(v.id)}">&#9654; show how it works</button>`;
		for (const aid of v.also)
		{
			btns += `<button class="btn small demo-btn" type="button" `
				+ `data-demo="${page_esc(aid)}">&#9654; ${page_esc(team.names[aid] || aid)}</button>`;
		}
		body += `<div class="demo-acts">${btns}</div>`;
	}
	if (v.questions.length)
	{
		body += `<details class="qs"><summary>Defense questions `
			+ `(${v.questions.length})</summary><ol>`
			+ v.questions.map(function (q)
			{
				return `<li>${page_esc(q)}</li>`;
			}).join("") + "</ol></details>";
	}
	return `<article class="card part ${cls} ${tilt}" data-part="${part}">`
		+ "<span class=\"tape c\"></span>"
		+ `<p class="lab">${PAGE_PART_LABEL[part].toUpperCase()}</p>`
		+ head + body + "</article>";
}

async function team_catalog()
{
	let catalog = [];

	try
	{
		catalog = await page_api("/api/catalog");
	}
	catch (e)
	{
		return; /* ids stay shown as ids */
	}
	for (const entry of catalog)
	{
		team.names[entry.id] = entry.name;
		team.catalog[entry.id] = entry;
	}
	for (const el of document.querySelectorAll(".also[data-id]"))
	{
		if (team.names[el.dataset.id])
			el.textContent = "+ " + team.names[el.dataset.id];
	}
	for (const el of document.querySelectorAll(".demo-btn[data-demo]"))
	{
		if (el.textContent.indexOf("show how it works") < 0
			&& team.names[el.dataset.demo])
			el.innerHTML = "&#9654; " + page_esc(team.names[el.dataset.demo]);
	}
}

/* ---- runs ------------------------------------------------------------------ */

function team_runs(judge)
{
	const line = page_diagnosis_line(judge.diagnosis);
	const groups = [];
	let out = "<span class=\"tape r\"></span><h3>Runs</h3><p class=\"hint\">"
		+ "Eliminatory = the eval sheet's tests. Every other group is our own "
		+ "bank: extra checks, harder than the sheet, to ask about, not points.</p>";

	/* 1. no build, no runs */
	if (!judge.built)
	{
		return out + "<p class=\"diag na\">No runs: the turn-in does not "
			+ "build.</p>";
	}
	/* 2. the diagnosis line, then the extra findings, then the timing */
	if (line)
		out += `<p class="diag big ${line.cls}">${page_esc(line.text)}</p>`;
	for (const extra of (judge.diagnosis && judge.diagnosis.extra) || [])
		out += `<p class="diag warn">${page_esc(extra)}</p>`;
	if (judge.timing)
	{
		const t = judge.timing;
		out += `<p class="hint">slowest: <code>${page_esc(t.slowest_id)}</code> `
			+ `${t.slowest_ms} ms`
			+ (t.slow4_over_ok4 !== null && t.slow4_over_ok4 !== undefined
				? ` · slow4 / ok4 = ${t.slow4_over_ok4}x` : "") + "</p>";
	}
	/* 3. one folded table per group, open when something failed */
	for (const run of judge.runs)
	{
		if (groups.indexOf(run.group) < 0)
			groups.push(run.group);
	}
	for (const group of page_group_order(groups))
	{
		const runs = judge.runs.filter(function (r)
		{
			return r.group === group;
		});
		const c = judge.groups[group] || {pass: 0, fail: 0, info: 0};
		const counts = [];
		let cls = "na";

		if (c.fail)
			cls = "bad";
		else if (c.pass)
			cls = "ok";

		for (const k of ["pass", "fail", "info"])
		{
			if (c[k])
				counts.push(`${c[k]} ${k}`);
		}
		out += `<details class="group ${cls}" data-group="${page_esc(group)}"${c.fail ? " open" : ""}>`
			+ `<summary><span class="gname">${page_esc(group === "evalsheet"
				? "Eliminatory tests (sheet)" : group)}</span>`
			+ `<span class="gcount">${counts.join(" · ")}</span></summary>`
			+ "<div class=\"runswrap\"><table class=\"runs\"><thead><tr>"
			+ "<th>id</th><th>verdict</th>"
			+ "<th>ms</th><th>argv</th><th>output</th><th>why</th><th></th>"
			+ "</tr></thead><tbody>" + runs.map(team_run_row).join("")
			+ "</tbody></table></div></details>";
	}
	return out;
}

function team_run_row(run)
{
	const cls = {pass: "ok", fail: "bad", info: "na"}[run.verdict] || "na";
	let argv = "(no argument)";
	let why = run.reasons.concat(run.notes).map(page_esc).join(" · ");
	let view = "";

	/* 1. argv as given, the invisible made visible */
	if (run.argv.length)
	{
		argv = run.argv.map(function (a)
		{
			return "\"" + page_visible(a, TEAM_ARGV_CAP) + "\"";
		}).join(" ");
	}
	/* 2. the clues it breaks, the first few */
	if (run.broken.length)
	{
		const shown = run.broken.slice(0, TEAM_BROKEN_SHOWN).map(function (b)
		{
			return `${b.side} ${b.index + 1}: want ${b.want}, seen ${b.seen}`;
		});
		if (run.broken.length > TEAM_BROKEN_SHOWN)
			shown.push("…");
		why += `<div class="broken">${page_esc(shown.join(" · "))}</div>`;
	}
	if (run.stderr)
	{
		why += `<div class="hint">stderr: `
			+ `${page_esc(page_visible(run.stderr, 80))}</div>`;
	}
	/* 3. a button to look at it in 3D, when it is a puzzle */
	if (sky_clues_from_argv(run.argv))
	{
		view = `<button class="btn small" type="button" data-sky="`
			+ `${page_esc(run.id)}" title="show in the 3D view">3D</button>`;
	}
	return `<tr class="v-${cls}"><td><code>${page_esc(run.id)}</code></td>`
		+ `<td><span class="st ${cls}">${page_esc(run.verdict)}</span></td>`
		+ `<td class="num">${run.time_ms}</td>`
		+ `<td><code class="argv" title="${page_esc(run.argv.join(" | "))}">`
		+ `${page_esc(argv)}</code></td>`
		+ `<td><span title="${page_esc(page_visible(run.stdout, 400))}">`
		+ `${page_esc(page_run_output(run))}</span></td>`
		+ `<td class="whycol">${why}</td><td>${view}</td></tr>`;
}

/* ---- source + call graph -------------------------------------------------- */

async function team_source()
{
	const box = page_q("#source");
	let data = null;

	try
	{
		data = await page_api("/api/source/" + encodeURIComponent(team.name));
	}
	catch (e)
	{
		box.innerHTML = `<h3>Source</h3><p class="diag na">skipped: `
			+ `${page_esc(e.message)}</p>`;
		return;
	}
	/* 1. the call graph */
	let out = "<span class=\"tape c\"></span><h3>Source + call graph</h3>"
		+ "<p class=\"hint\">Every function, and every outside function it "
		+ "calls. Click a box to jump to its code.</p>"
		+ `<div class="graphwrap">${data.graph || ""}</div>`;
	for (const note of data.notes)
		out += `<p class="diag na">${page_esc(note)}</p>`;
	/* 2. one tab per file */
	team.files = {};
	out += "<div class=\"tabs\">";
	data.files.forEach(function (f, i)
	{
		team.files[f.path] = f.id;
		out += `<button class="btn small${i === 0 ? " on" : ""}" type="button" `
			+ `data-tab="${page_esc(f.id)}">${page_esc(f.path)}</button>`;
	});
	out += "</div>";
	data.files.forEach(function (f, i)
	{
		out += `<div class="pane" data-pane="${page_esc(f.id)}"`
			+ `${i === 0 ? "" : " hidden"}>${f.html}</div>`;
	});
	box.innerHTML = out;
}

function team_show_tab(file_id)
{
	for (const btn of document.querySelectorAll("[data-tab]"))
		btn.classList.toggle("on", btn.dataset.tab === file_id);
	for (const pane of document.querySelectorAll("[data-pane]"))
		pane.hidden = pane.dataset.pane !== file_id;
}

/* jump to a line of a file: show its tab, scroll, flash it */
function team_goto(el)
{
	if (!el)
		return;
	const pane = el.closest("[data-pane]");
	if (pane)
		team_show_tab(pane.dataset.pane);
	if (team.deck !== "all" && team.deck !== "source")
		team_deck("source");
	for (const old of document.querySelectorAll(".sl.hl"))
		old.classList.remove("hl");
	el.classList.add("hl");
	el.scrollIntoView({block: "center"});
}

function team_click(ev)
{
	/* 0. a gate, a loadout slot, a deck tab */
	const gate = ev.target.closest("[data-goto]");
	if (gate)
	{
		team_gate_goto(gate.dataset.goto);
		return;
	}
	const slot = ev.target.closest("[data-slot]");
	if (slot)
	{
		const card = page_q(`.part[data-part="${CSS.escape(slot.dataset.slot)}"]`);
		if (card)
			team_reveal(card, true);
		return;
	}
	const deck = ev.target.closest("[data-deck]");
	if (deck)
	{
		team_deck(deck.dataset.deck);
		return;
	}
	/* 1. a file:line link */
	const link = ev.target.closest("a[data-file]");
	if (link)
	{
		const file_id = team.files[link.dataset.file];

		ev.preventDefault();
		if (!file_id)
			return;
		team_show_tab(file_id);
		const line = link.dataset.line || "1";
		team_goto(document.getElementById(file_id + "-L" + line));
		return;
	}
	/* 2. a source tab */
	const tab = ev.target.closest("[data-tab]");
	if (tab)
	{
		team_show_tab(tab.dataset.tab);
		return;
	}
	/* 3. a call graph box */
	const node = ev.target.closest("svg.graph .node");
	if (node && node.getAttribute("data-anchor"))
	{
		team_goto(document.getElementById(node.getAttribute("data-anchor")
			+ "-src"));
		return;
	}
	/* 4. a run's 3D button */
	const sky = ev.target.closest("[data-sky]");
	if (sky && team.sky)
	{
		sky_show(team.sky, sky.dataset.sky);
		page_q("#hero").scrollIntoView({block: "start"});
		return;
	}
	/* 5. a card's "show how it works" preset demo button */
	const dbtn = ev.target.closest("[data-demo]");
	if (dbtn)
	{
		const id = dbtn.dataset.demo;
		demo_open_modal(team.catalog[id] || {id: id, part: id.split(".")[0],
			name: team.names[id] || id, explain: ""}, id);
	}
}

function team_main()
{
	page_theme();
	try
	{
		team.deck = localStorage.getItem("rush01.deck") || "defense";
	}
	catch (e)
	{
		team.deck = "defense";
	}
	document.addEventListener("keydown", function (ev)
	{
		const tag = (document.activeElement || {}).tagName;
		const i = "1234".indexOf(ev.key);

		if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA"
			|| i < 0 || ev.ctrlKey || ev.metaKey || ev.altKey
			|| page_q("#deck-tabs").hidden)
			return;
		team_deck(TEAM_DECKS[i]);
		/* far below: come back up to the tabs */
		const tabs = page_q("#deck-tabs");
		if (tabs.getBoundingClientRect().top < 0)
			tabs.scrollIntoView({block: "start"});
	});
	document.addEventListener("click", team_click);
	page_q("#rerun").onclick = async function ()
	{
		try
		{
			await page_api("/api/rerun", {team: team.name});
			team_banner("na", "queued…");
			setTimeout(team_load, 300);
		}
		catch (e)
		{
			page_toast(e.message);
		}
	};
	team_load();
}

team_main();
