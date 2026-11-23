/* page.js: what both rush01 pages need: escaping, the JSON api, the toast,
   the paper / night toggle, the hearts, and the words that carry meaning
   (AGENTS.md rule 1). Plain script, no modules (decision 003). */

"use strict";

const PAGE_BUSY = ["queued", "running", "cloning"];
const PAGE_PARTS = ["parse", "data", "solve", "print"];
const PAGE_PART_LABEL = {parse: "Parse", data: "Data", solve: "Solve",
	print: "Print"};
/* the eval sheet's eliminatory tests are the bank group "evalsheet" */
const PAGE_GROUP_LABEL = {evalsheet: "eliminatory"};
const PAGE_HEART = "M0 14 C-34 -12 -18 -38 0 -18 C18 -38 34 -12 0 14 Z";

function page_q(sel, root)
{
	return (root || document).querySelector(sel);
}

function page_esc(s)
{
	const map = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;",
		"'": "&#39;"};

	return String(s === null || s === undefined ? "" : s)
		.replace(/[&<>"']/g, function (c)
		{
			return map[c];
		});
}

async function page_api(path, body)
{
	let opts = {};

	/* 1. GET without a body, POST json with one */
	if (body !== undefined)
	{
		opts = {method: "POST", headers: {"content-type": "application/json"},
			body: JSON.stringify(body)};
	}
	const res = await fetch(path, opts);
	/* 2. errors come back as {"error": text} */
	let data = null;
	try
	{
		data = await res.json();
	}
	catch (e)
	{
		data = {error: res.statusText};
	}
	if (!res.ok)
	{
		const err = new Error(data.error || res.statusText);
		err.status = res.status;
		throw err;
	}
	return data;
}

function page_toast(msg)
{
	const box = document.createElement("div");

	box.className = "toast";
	box.textContent = msg;
	document.body.appendChild(box);
	setTimeout(function ()
	{
		box.remove();
	}, 3500);
}

function page_theme()
{
	const root = document.documentElement;
	const btn = page_q(".themebtn");

	function apply(dark)
	{
		if (dark)
			root.setAttribute("data-theme", "dark");
		else
			root.removeAttribute("data-theme");
		if (btn)
		{
			btn.textContent = dark ? "\u2600" : "\u263E";
			btn.title = dark ? "switch to paper mode" : "switch to dark mode";
			btn.setAttribute("aria-label", btn.title);
			btn.setAttribute("aria-pressed", dark ? "true" : "false");
		}
	}

	let saved = null;
	try
	{
		saved = localStorage.getItem("rush-nb-theme");
	}
	catch (e)
	{
		/* private mode: follow system or paper */
	}
	const prefers_dark = Boolean(window.matchMedia
		&& window.matchMedia("(prefers-color-scheme: dark)").matches);
	apply(saved === "dark" || (!saved && prefers_dark));

	if (btn)
	{
		btn.onclick = function ()
		{
			const dark = root.getAttribute("data-theme") !== "dark";

			apply(dark);
			try
			{
				localStorage.setItem("rush-nb-theme", dark ? "dark" : "light");
			}
			catch (e)
			{
				/* not saved */
			}
		};
	}
	window.addEventListener("storage", function (ev)
	{
		if (ev.key === "rush-nb-theme")
			apply(ev.newValue === "dark");
	});
}

/* one heart per basic check: full = passed, broken = failed,
   faded = not checked (never drawn as a pass) */
function page_heart(kind, label, title)
{
	let body = `<path d="${PAGE_HEART}" stroke-dasharray="6 6" opacity="0.5"/>`;

	if (kind === "full")
		body = `<path d="${PAGE_HEART}" fill="#0B7A73"/>`;
	else if (kind === "broken")
	{
		body = `<path d="${PAGE_HEART}"/>`
			+ "<path d=\"M0 -18 L-6 -6 L4 0 L-2 12\" stroke=\"#E07A1F\"/>";
	}
	return `<div class="heart h-${kind}" title="${page_esc(title)}">`
		+ "<svg width=\"54\" height=\"46\" viewBox=\"-27 -26 54 46\">"
		+ "<g filter=\"url(#wob)\" fill=\"none\" stroke=\"#1E2A3A\" "
		+ "stroke-width=\"4\" stroke-linecap=\"round\" "
		+ `stroke-linejoin="round" transform="scale(.75)">${body}</g></svg>`
		+ `<span>${label}</span></div>`;
}

/* the three hearts: builds, forbidden-free, norm */
function page_hearts(built, forbidden, norm)
{
	let out = "";

	if (built)
		out += page_heart("full", "builds", "cc -Wall -Wextra -Werror builds");
	else
		out += page_heart("broken", "no build", "the build failed");
	if (forbidden.length === 0)
		out += page_heart("full", "allowed only", "only write, malloc, free");
	else
	{
		out += page_heart("broken", "&#10007; " + page_esc(forbidden.join(", ")),
			"forbidden functions used");
	}
	if (!norm.ran)
		out += page_heart("lost", "norm?", "norminette not run: skipped");
	else if (norm.ok)
		out += page_heart("full", "norm", "norminette passes");
	else
		out += page_heart("broken", "norm", "norminette errors");
	return out;
}

/* confidence is about the detector, never about the code: ink tones only;
   "unrecognized" is dashed and grey so it can't pass for a verdict */
function page_conf_class(confidence)
{
	const known = ["clear", "likely", "mix", "unrecognized"];

	if (known.indexOf(confidence) < 0)
		return "c-unrecognized";
	return "c-" + confidence;
}

/* "8 of 9 failures fit: ..." (PLAN.md §5), or why there is no such line */
function page_diagnosis_line(diag)
{
	let failures = 0;

	if (!diag)
		return null;
	if (diag.best)
	{
		return {cls: "warn", text: `${diag.best.explains} of `
			+ `${diag.best.failures} failures fit: ${diag.best.text}`};
	}
	if (diag.all && diag.all.length)
		failures = diag.all[0].failures;
	if (failures === 0)
	{
		return {cls: "na", text: "nothing to explain: no wrong grid and no "
			+ "Error on a valid puzzle"};
	}
	return {cls: "na", text: `no known misreading fits the ${failures} `
		+ "failures"};
}

/* what a run printed, in a few words */
function page_run_output(run)
{
	if (run.timed_out)
		return "timeout";
	if (run.signal)
		return "crashed (" + run.signal + ")";
	if (run.stdout === "Error\n")
		return "Error";
	if (run.grid)
		return `grid ${run.grid.length}x${run.grid.length}`;
	if (run.stdout === "")
		return "nothing";
	return "unparsed output";
}

/* stdout with the invisible made visible: spaces at line ends, newlines */
function page_visible(text, cap)
{
	let s = text.length > cap ? text.slice(0, cap) + "…" : text;

	s = s.replace(/ +\n/g, function (m)
	{
		return "␣".repeat(m.length - 1) + "\n";
	});
	return s.replace(/\n/g, "⏎").replace(/\t/g, "⇥");
}

/* group names in display order: the sheet's eliminatory tests first */
function page_group_order(names)
{
	return names.slice().sort(function (a, b)
	{
		return (b === "evalsheet") - (a === "evalsheet");
	});
}

function page_group_label(group)
{
	return PAGE_GROUP_LABEL[group] || group;
}

/* the eval sheet's stops as lines: STOP (sheet ends it) or CHECK */
function page_stop_lines(stops)
{
	return (stops || []).map(function (s)
	{
		const head = s.level === "stop" ? "STOP" : "CHECK";

		return `<p class="diag stop ${s.level}" title="${page_esc(s.sheet)}">`
			+ `<b>${head}</b> ${page_esc(s.text)}</p>`;
	}).join("");
}

/* ---- the eval sheet's outcome: the headline of a team ------------------- */

/* short words for the stops, so a badge stays one line */
const PAGE_STOP_WORD = {no_ex_dir: "no ex00", no_sources: "no .c",
	norm: "norm", build: "build", eliminatory: "elim.",
	files: "extra files", forbidden: "forbidden"};

function page_stop_word(key)
{
	return PAGE_STOP_WORD[key] || key;
}

/* what the eval sheet makes of a team, from {built, stops, groups}: the
   first STOP, or "sheet OK" when nothing stops and the eliminatory tests
   pass. Our bank (the other groups) is not part of it: "extra checks". */
function page_sheet(s)
{
	const stops = (s.stops || []).filter(function (x)
	{
		return x.level === "stop";
	});
	const e = s.groups && s.groups.evalsheet;

	if (stops.length)
	{
		return {cls: "bad", text: "STOP " + page_stop_word(stops[0].key),
			small: stops.length > 1 ? `+ ${stops.length - 1} more stop(s)`
				: "the sheet stops here", key: stops[0].key};
	}
	if (!s.built)
		return {cls: "bad", text: "STOP build", small: "does not build", key: "build"};
	if (e && e.fail)
	{
		return {cls: "bad", text: "STOP eliminatory",
			small: `${e.pass}/${e.pass + e.fail} pass`, key: "eliminatory"};
	}
	if (!e || !(e.pass + e.fail))
		return {cls: "na", text: "no sheet runs", small: "old report: re-run", key: ""};
	return {cls: "ok", text: "sheet OK", small: `eliminatory ${e.pass}/${e.pass + e.fail}`,
		key: ""};
}

/* our own bank (every group but the sheet's): extra checks, not points */
function page_extra(groups)
{
	const out = {pass: 0, fail: 0};

	for (const [name, c] of Object.entries(groups || {}))
	{
		if (name === "evalsheet")
			continue;
		out.pass += c.pass;
		out.fail += c.fail;
	}
	return out;
}
