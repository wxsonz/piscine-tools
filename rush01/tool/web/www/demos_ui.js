/* demos_ui.js: one shared step player and one shared pedagogical renderer per
   part (CONTRACT.md B7, B8). Reuses sky3d.js's 3D boxes and sightline rules
   for solving presets, with purposeful animations (growth, backtrack ghosts,
   clue beams, timeline scrubber, bit LEDs, syscall pipe) that show how each
   approach works — never a trace of a team's code (AGENTS.md rule 1). */

"use strict";

const DEMO_SPEEDS_MS = [650, 260, 90, 25];
const DEMO_PRESET_BANNER = "How this approach works (preset), not their code";
const DEMO_OP_LABEL = {
	place: "PLACE",
	prefill: "DEDUCE",
	prune: "PRUNE",
	reject: "REJECT",
	backtrack: "UNDO",
	check: "CHECK",
	store: "STORE",
	skip: "SKIP",
	buffer: "BUFFER",
	flush: "FLUSH",
	emit: "WRITE",
	done: "SOLVED",
	cap: "CAPPED",
	error: "ERROR"
};

/* Mount a self-contained preset demo player inside root.
   opts: {demo_id, entry, puzzle_id, show_puzzle_pick, compact}. */
function demo_mount(root, opts)
{
	const state = {
		root: root,
		demo_id: opts.demo_id,
		entry: opts.entry || null,
		puzzle_id: opts.puzzle_id || DEMO_PUZZLES[0].id,
		rec: null,
		idx: 0,
		prev_idx: -1,
		prev_step: null,
		timer: null,
		speed_i: 1,
		flat: false,
		rx: SKY_VIEWS.iso[0],
		rz: SKY_VIEWS.iso[1],
		lift: 0,
		size: 0,
		hover_clue: -1,
		pin_clue: -1,
		dragging: false,
		dragged: false,
		compact: Boolean(opts.compact)
	};

	/* 1. shell: truth banner, controls, color-coded timeline, stage, caption */
	let pick_html = "";
	if (opts.show_puzzle_pick !== false)
	{
		pick_html = "<label class=\"demo-picklab\">puzzle <select class=\"demo-pick\">"
			+ DEMO_PUZZLES.map(function (p)
			{
				const sel = p.id === state.puzzle_id ? " selected" : "";
				return `<option value="${page_esc(p.id)}"${sel}>`
					+ `${page_esc(p.label)}</option>`;
			}).join("") + "</select></label>";
	}
	root.innerHTML = `<div class="demo-wrap${state.compact ? " compact" : ""}">`
		+ `<p class="demo-preset-tag">${DEMO_PRESET_BANNER}</p>`
		+ "<div class=\"demo-bar\">"
		+ "<button class=\"btn small\" type=\"button\" data-act=\"reset\" title=\"reset\">&#8634;</button>"
		+ "<button class=\"btn small\" type=\"button\" data-act=\"prev\" title=\"step back\">&#9664;</button>"
		+ "<button class=\"btn small go\" type=\"button\" data-act=\"play\">&#9654; Play</button>"
		+ "<button class=\"btn small\" type=\"button\" data-act=\"next\" title=\"step forward\">&#9654;|</button>"
		+ "<button class=\"btn small\" type=\"button\" data-act=\"end\" title=\"jump to end\">&#9197;</button>"
		+ "<button class=\"btn small\" type=\"button\" data-act=\"speed\">1x</button>"
		+ "<span class=\"sp\"></span>"
		+ pick_html
		+ "<span class=\"demo-count\"></span></div>"
		+ "<div class=\"demo-scrub\" role=\"slider\" tabindex=\"0\" "
		+ "aria-label=\"step timeline\" title=\"click or drag to scrub steps\">"
		+ "<div class=\"demo-scrub-rail\"></div>"
		+ "<div class=\"demo-scrub-head\"></div></div>"
		+ "<div class=\"demo-stage\"></div>"
		+ "<p class=\"demo-caption\"></p>"
		+ "<div class=\"demo-stats\"></div></div>";
	/* 2. wire controls + interactive scrubber */
	root.querySelector(".demo-bar").addEventListener("click", function (ev)
	{
		const btn = ev.target.closest("[data-act]");
		if (!btn)
			return;
		demo_control(state, btn.dataset.act);
	});
	demo_wire_scrub(state, root.querySelector(".demo-scrub"));
	const pick = root.querySelector(".demo-pick");
	if (pick)
	{
		pick.onchange = function ()
		{
			demo_stop(state);
			state.puzzle_id = pick.value;
			demo_load(state);
		};
	}
	/* 3. generate steps and draw step 0 */
	demo_load(state);
	return state;
}

function demo_wire_scrub(state, scrub)
{
	function jump(client_x)
	{
		if (!state.rec || !state.rec.steps.length)
			return;
		const rect = scrub.getBoundingClientRect();
		const frac = Math.max(0, Math.min(1,
			(client_x - rect.left) / Math.max(1, rect.width)));
		const target = Math.round(frac * (state.rec.steps.length - 1));

		if (target !== state.idx)
		{
			state.prev_idx = state.idx;
			state.prev_step = state.rec.steps[state.idx] || null;
			state.idx = target;
			demo_draw(state);
		}
	}

	scrub.addEventListener("pointerdown", function (ev)
	{
		demo_stop(state);
		jump(ev.clientX);
		function move(e)
		{
			jump(e.clientX);
		}
		function up()
		{
			window.removeEventListener("pointermove", move);
			window.removeEventListener("pointerup", up);
			window.removeEventListener("pointercancel", up);
		}
		window.addEventListener("pointermove", move);
		window.addEventListener("pointerup", up);
		window.addEventListener("pointercancel", up);
	});
	scrub.addEventListener("keydown", function (ev)
	{
		if (ev.key === "ArrowRight")
		{
			ev.preventDefault();
			demo_control(state, "next");
		}
		else if (ev.key === "ArrowLeft")
		{
			ev.preventDefault();
			demo_control(state, "prev");
		}
	});
}

/* Paint one CSS linear-gradient representing every step's operation color. */
function demo_paint_scrub(state)
{
	const rail = state.root.querySelector(".demo-scrub-rail");
	const rec = state.rec;

	if (!rail || !rec || !rec.steps.length)
		return;
	const n = rec.steps.length;
	const stops = [];
	let run_col = null;
	let run_start = 0;

	function op_color(op)
	{
		if (op === "prefill" || op === "buffer")
			return "var(--gold-hi)";
		if (op === "prune" || op === "reject" || op === "error" || op === "cap")
			return "var(--orange)";
		if (op === "backtrack")
			return "color-mix(in srgb, var(--orange) 52%, var(--card))";
		if (op === "place" || op === "store" || op === "emit" || op === "flush"
			|| op === "done")
			return "var(--teal)";
		return "color-mix(in srgb, var(--body) 40%, transparent)";
	}
	for (let i = 0; i <= n; i++)
	{
		const col = i < n ? op_color(rec.steps[i].op) : null;
		if (col !== run_col)
		{
			if (run_col !== null)
			{
				const a = (100 * run_start / n).toFixed(2);
				const b = (100 * i / n).toFixed(2);
				stops.push(`${run_col} ${a}% ${b}%`);
			}
			run_col = col;
			run_start = i;
		}
	}
	rail.style.background = `linear-gradient(to right, ${stops.join(", ")})`;
}

function demo_load(state)
{
	demo_stop(state);
	state.rec = demo_run(state.demo_id, state.puzzle_id);
	state.idx = 0;
	state.prev_idx = -1;
	state.prev_step = null;
	state.hover_clue = -1;
	state.pin_clue = -1;
	if (!state.rec || !state.rec.steps.length)
	{
		state.root.querySelector(".demo-stage").innerHTML =
			"<p class=\"empty\">No preset demo for this entry.</p>";
		return;
	}
	demo_paint_scrub(state);
	demo_draw(state);
}

function demo_stop(state)
{
	if (state.timer)
	{
		clearInterval(state.timer);
		state.timer = null;
	}
	const btn = state.root.querySelector("[data-act=\"play\"]");
	if (btn)
		btn.innerHTML = "&#9654; Play";
}

function demo_step_to(state, next_idx)
{
	state.prev_idx = state.idx;
	state.prev_step = state.rec.steps[state.idx] || null;
	state.idx = next_idx;
	demo_draw(state);
}

function demo_control(state, act)
{
	if (!state.rec)
		return;
	const last = state.rec.steps.length - 1;

	if (act === "reset")
	{
		demo_stop(state);
		state.prev_idx = -1;
		state.prev_step = null;
		state.idx = 0;
		demo_draw(state);
	}
	else if (act === "prev")
	{
		demo_stop(state);
		if (state.idx > 0)
			demo_step_to(state, state.idx - 1);
	}
	else if (act === "next")
	{
		demo_stop(state);
		if (state.idx < last)
			demo_step_to(state, state.idx + 1);
	}
	else if (act === "end")
	{
		demo_stop(state);
		demo_step_to(state, last);
	}
	else if (act === "speed")
	{
		const labels = ["0.5x", "1x", "3x", "10x"];
		state.speed_i = (state.speed_i + 1) % DEMO_SPEEDS_MS.length;
		state.root.querySelector("[data-act=\"speed\"]").textContent =
			labels[state.speed_i];
		if (state.timer)
		{
			demo_stop(state);
			demo_control(state, "play");
		}
	}
	else if (act === "play")
	{
		if (state.timer)
		{
			demo_stop(state);
			return;
		}
		if (state.idx >= last)
		{
			state.prev_idx = -1;
			state.prev_step = null;
			state.idx = 0;
		}
		state.root.querySelector("[data-act=\"play\"]").innerHTML = "&#9646;&#9646; Pause";
		state.timer = setInterval(function ()
		{
			if (state.idx >= last)
			{
				demo_stop(state);
				return;
			}
			demo_step_to(state, state.idx + 1);
		}, DEMO_SPEEDS_MS[state.speed_i]);
	}
}

/* Draw the current step using the shared renderer for rec.kind. */
function demo_draw(state)
{
	const rec = state.rec;
	const step = rec.steps[state.idx];
	const stage = state.root.querySelector(".demo-stage");
	const cap = state.root.querySelector(".demo-caption");
	const stats = state.root.querySelector(".demo-stats");
	const scrub = state.root.querySelector(".demo-scrub");
	const head = state.root.querySelector(".demo-scrub-head");
	const total_note = rec.total > rec.steps.length
		? ` (${rec.total} total)` : "";
	const op = step.op || "check";
	const pill = DEMO_OP_LABEL[op] || op.toUpperCase();

	/* 1. step counter, scrubber playhead, and operation caption */
	state.root.querySelector(".demo-count").textContent =
		`step ${state.idx + 1}/${rec.steps.length}${total_note}`;
	if (head && scrub)
	{
		const pct = rec.steps.length > 1
			? (100 * state.idx / (rec.steps.length - 1)) : 100;
		head.style.left = pct.toFixed(2) + "%";
		scrub.setAttribute("aria-valuemin", "1");
		scrub.setAttribute("aria-valuemax", String(rec.steps.length));
		scrub.setAttribute("aria-valuenow", String(state.idx + 1));
	}
	cap.className = "demo-caption op-" + op;
	cap.innerHTML = `<span class="demo-op-pill op-${page_esc(op)}">`
		+ `${page_esc(pill)}</span> ${page_esc(step.text || "")}`;
	/* 2. part-specific stage */
	if (rec.kind === "solve")
		demo_draw_solve(state, stage, step);
	else if (rec.kind === "parse")
		demo_draw_parse(state, rec, stage, step);
	else if (rec.kind === "data")
		demo_draw_data(state, rec, stage, step);
	else if (rec.kind === "print")
		demo_draw_print(state, rec, stage, step);
	/* 3. truth stats strip */
	stats.innerHTML = demo_stats_html(rec);
}

function demo_stats_html(rec)
{
	const chips = [];

	if (rec.kind === "solve")
	{
		chips.push(`<span class="fact">total steps: <b>${rec.total}</b></span>`);
		chips.push(`<span class="fact">places: <b>${rec.stats.place}</b></span>`);
		chips.push(`<span class="fact">backtracks: <b>${rec.stats.backtrack}</b></span>`);
		if (rec.stats.prune)
			chips.push(`<span class="fact ok">prunes: <b>${rec.stats.prune}</b></span>`);
		if (rec.capped)
			chips.push("<span class=\"fact warn\">capped (too large to finish)</span>");
		else if (rec.solved)
			chips.push("<span class=\"fact ok\">solved</span>");
		else
			chips.push("<span class=\"fact warn\">no solution / Error</span>");
	}
	else if (rec.kind === "print")
		chips.push(`<span class="fact">write() calls: <b>${rec.stats.writes}</b></span>`);
	return chips.join("");
}

/* ---- Solve renderer: 3D skyscraper board (reusing sky3d.js) + 2D toggle --- */

function demo_turn(state)
{
	const board = state.root.querySelector(".demo-scene .sky-board");

	if (!board)
		return;
	board.style.transform = `rotateX(${state.rx}deg) rotateZ(${state.rz}deg)`;
	for (const chip of board.querySelectorAll(".sky-clue"))
	{
		chip.style.transform = `translateZ(${state.lift}px) `
			+ `rotateZ(${-state.rz}deg) rotateX(${-state.rx}deg)`;
	}
}

function demo_drag(state, scene)
{
	scene.addEventListener("pointerdown", function (ev)
	{
		const x0 = ev.clientX;
		const y0 = ev.clientY;
		const rx0 = state.rx;
		const rz0 = state.rz;

		state.dragged = false;
		function move(e)
		{
			const dx = e.clientX - x0;
			const dy = e.clientY - y0;

			if (Math.abs(dx) + Math.abs(dy) < 4 && !state.dragged)
				return;
			state.dragged = true;
			state.dragging = true;
			state.rz = rz0 - dx * 0.4;
			state.rx = Math.max(0, Math.min(88, rx0 - dy * 0.4));
			demo_turn(state);
		}
		function up()
		{
			state.dragging = false;
			window.removeEventListener("pointermove", move);
			window.removeEventListener("pointerup", up);
			window.removeEventListener("pointercancel", up);
		}
		window.addEventListener("pointermove", move);
		window.addEventListener("pointerup", up);
		window.addEventListener("pointercancel", up);
	});
}

/* Wire hover-to-preview & click-to-pin sightline on every edge clue chip. */
function demo_wire_clue_hover(state, container)
{
	container.addEventListener("mouseover", function (ev)
	{
		if (state.dragging)
			return;
		const chip = ev.target.closest(".sky-clue[data-dk]");
		const k = chip ? Number(chip.dataset.dk) : -1;
		if (k !== state.hover_clue)
		{
			state.hover_clue = k;
			demo_apply_clue_hover(state, k >= 0);
		}
	});
	container.addEventListener("mouseleave", function ()
	{
		if (state.hover_clue !== -1)
		{
			state.hover_clue = -1;
			demo_apply_clue_hover(state, false);
		}
	});
	container.addEventListener("click", function (ev)
	{
		if (state.dragged)
		{
			state.dragged = false;
			return;
		}
		const chip = ev.target.closest(".sky-clue[data-dk]");
		if (!chip)
			return;
		const k = Number(chip.dataset.dk);
		state.pin_clue = state.pin_clue === k ? -1 : k;
		demo_apply_clue_hover(state, state.pin_clue >= 0);
	});
}

/* Apply live edge sightline colouring when hovering or pinning a clue chip.
   animate=true plays the directional wave once (on hover/pin change);
   animate=false updates seen/hidden silently during step playback. */
function demo_apply_clue_hover(state, animate)
{
	const rec = state.rec;
	const step = rec && rec.steps[state.idx];
	const stage = state.root.querySelector(".demo-stage");

	if (!stage || !rec || !step)
		return;
	const n = rec.n;
	const grid = step.grid || null;
	const k = state.hover_clue >= 0 ? state.hover_clue : state.pin_clue;
	const info = stage.querySelector(".demo-sightline");
	const hbeam = stage.querySelector(".sky-beam.hover-beam");
	const els = Array.from(stage.querySelectorAll(".sky-box[data-r], .sky-cell[data-r]"));
	const chips = Array.from(stage.querySelectorAll(".sky-clue[data-dk]"));

	if (k < 0 || !grid)
	{
		for (const el of els)
			el.classList.remove("seen", "hidden", "off", "wave");
		for (const chip of chips)
		{
			chip.classList.remove("hover-on");
			const cnt = chip.querySelector(".cnt.hover-cnt");
			if (cnt)
				cnt.remove();
		}
		if (hbeam)
			hbeam.hidden = true;
		if (info)
			info.innerHTML = "Hover any edge clue to preview its sightline · heights colour-coded 1.." + n + ".";
		return;
	}
	const side = SKY_SIDES[Math.floor(k / n)];
	const idx = k % n;
	const line = sky_line(n, side, idx);
	const heights = line.map(function (rc) { return grid[rc[0]][rc[1]]; });
	const seen = sky_seen(heights);
	const full = heights.every(function (v) { return v > 0; });
	const want = rec.clues[k];
	const ok = full ? (seen.count === want) : (seen.count <= want);
	const role = {};
	const order = {};

	line.forEach(function (rc, i)
	{
		const key = rc[0] + "," + rc[1];
		if (heights[i] > 0)
		{
			role[key] = seen.visible[i] ? "seen" : "hidden";
			order[key] = i;
		}
	});
	for (const el of els)
	{
		const key = el.dataset.r + "," + el.dataset.c;
		const r = role[key];

		if (animate)
			el.classList.remove("anim-rise", "wave");
		el.classList.toggle("seen", r === "seen");
		el.classList.toggle("hidden", r === "hidden");
		el.classList.toggle("off", !r);
		if (animate && r)
		{
			el.style.setProperty("--d", String(order[key] || 0));
			void el.offsetWidth;
			el.classList.add("wave");
		}
	}
	for (const chip of chips)
	{
		const ck = Number(chip.dataset.dk);
		const old = chip.querySelector(".cnt.hover-cnt");
		chip.classList.toggle("hover-on", ck === k);
		if (ck === k)
		{
			const b = old || document.createElement("span");
			b.className = "cnt hover-cnt" + (ok ? "" : " bad");
			b.textContent = String(seen.count);
			if (!old)
				chip.appendChild(b);
		}
		else if (old)
			old.remove();
	}
	if (hbeam && state.size)
	{
		const sz = state.size;
		const is_col = side === "top" || side === "bottom";
		hbeam.hidden = false;
		hbeam.className = "sky-beam hover-beam " + (ok ? "ok" : "bad")
			+ (animate ? "" : " no-anim");
		hbeam.style.left = (is_col ? (idx + 1) * sz : sz) + "px";
		hbeam.style.top = (is_col ? sz : (idx + 1) * sz) + "px";
		hbeam.style.width = (is_col ? sz : n * sz) + "px";
		hbeam.style.height = (is_col ? n * sz : sz) + "px";
	}
	if (info)
	{
		const status = full
			? (seen.count === want ? "matches clue" : `mismatch (want ${want})`)
			: (seen.count <= want ? `partial (${seen.count} seen so far)`
				: `already exceeds clue ${want}!`);
		info.innerHTML = `<b>${side} clue ${idx + 1} = ${want}</b> (looking ${SKY_LOOK[side]}): `
			+ `sees <b>${seen.count}</b> — <span class="${ok ? "k-ok" : "k-bad"}">`
			+ `${status}</span>`;
	}
}

function demo_wire_skybar(state, stage)
{
	for (const btn of stage.querySelectorAll("[data-dview]"))
	{
		btn.onclick = function ()
		{
			const was_flat = state.flat;

			state.flat = false;
			state.rx = SKY_VIEWS[btn.dataset.dview][0];
			state.rz = SKY_VIEWS[btn.dataset.dview][1];
			if (was_flat)
				demo_draw(state);
			else
				demo_turn(state);
		};
	}
	const fbtn = stage.querySelector("[data-dflat]");
	if (fbtn)
	{
		fbtn.onclick = function ()
		{
			state.flat = !state.flat;
			demo_draw(state);
		};
	}
}

/* Derive which clues/lines are actively involved in this step so the board
   visually highlights the exact clue or row/col causing a deduce or prune. */
function demo_solve_cues(rec, step, counts)
{
	const n = rec.n;
	const text = step.text || "";
	const out = {bad_clues: {}, gold_clues: {}, seen_badge: {},
		beam_row: -1, beam_col: -1, beam_bad: false};
	const is_bad = step.op === "prune" || step.op === "reject";

	/* 1. prefill: highlight the exact clue (top/bottom/left/right[i]) */
	if (step.op === "prefill")
	{
		const m = text.match(/\b(top|bottom|left|right)\[(\d+)\]/);
		if (m)
		{
			const side_i = SKY_SIDES.indexOf(m[1]);
			const idx = Number(m[2]);
			out.gold_clues[side_i * n + idx] = true;
			if (side_i < 2)
				out.beam_col = idx;
			else
				out.beam_row = idx;
		}
	}
	/* 2. prune / reject: spotlight the offending row, column, or clues */
	if (is_bad)
	{
		out.beam_bad = true;
		const rm = text.match(/\brow (\d+)/);
		const cm = text.match(/\bcol (\d+)/);
		if (rm)
		{
			const r = Number(rm[1]);
			out.beam_row = r;
			out.bad_clues[2 * n + r] = true;
			out.bad_clues[3 * n + r] = true;
			if (step.grid && step.grid[r])
			{
				const row = step.grid[r];
				out.seen_badge[2 * n + r] = sky_seen(row).count;
				out.seen_badge[3 * n + r] = sky_seen(row.slice().reverse()).count;
			}
		}
		else if (cm)
		{
			const c = Number(cm[1]);
			out.beam_col = c;
			out.bad_clues[c] = true;
			out.bad_clues[n + c] = true;
			if (step.grid)
			{
				const col = step.grid.map(function (row) { return row[c]; });
				out.seen_badge[c] = sky_seen(col).count;
				out.seen_badge[n + c] = sky_seen(col.slice().reverse()).count;
			}
		}
		else if (counts)
		{
			for (let k = 0; k < 4 * n; k++)
			{
				if (counts[k] !== rec.clues[k])
				{
					out.bad_clues[k] = true;
					out.seen_badge[k] = counts[k];
				}
			}
		}
		else if (step.focus)
		{
			out.beam_row = step.focus[0];
			out.beam_col = step.focus[1];
		}
	}
	else if (step.focus && (step.op === "place" || step.op === "prefill"))
	{
		if (out.beam_row < 0 && out.beam_col < 0)
		{
			out.beam_row = step.focus[0];
			out.beam_col = step.focus[1];
		}
	}
	return out;
}

function demo_draw_solve(state, stage, step)
{
	const rec = state.rec;
	const n = rec.n;
	const grid = step.grid || null;
	const prev_grid = state.prev_step && state.prev_step.grid
		&& state.prev_idx === state.idx - 1 ? state.prev_step.grid : null;
	const focus = step.focus || null;
	const counts = grid && grid.every(function (row)
	{
		return row.every(function (v) { return v > 0; });
	}) ? sky_counts(grid) : null;
	const cues = demo_solve_cues(rec, step, counts);
	const is_win = step.op === "done" && rec.solved;
	const is_bad = step.op === "reject" || step.op === "prune";
	const bar_html = "<div class=\"demo-skybar\">"
		+ (state.flat ? "" : "<span class=\"demo-drag-hint\">Drag to turn</span>")
		+ "<button class=\"btn small\" type=\"button\" data-dview=\"top\">top</button>"
		+ "<button class=\"btn small\" type=\"button\" data-dview=\"front\">front</button>"
		+ "<button class=\"btn small\" type=\"button\" data-dview=\"iso\">iso</button>"
		+ "<button class=\"btn small\" type=\"button\" data-dflat=\"1\">"
		+ (state.flat ? "3D" : "2D") + "</button></div>";

	/* count how many cells changed per row to stagger whole-row placements */
	const row_changes = [0, 0, 0, 0];
	if (grid && prev_grid)
	{
		for (let r = 0; r < n; r++)
		{
			for (let c = 0; c < n; c++)
			{
				if (grid[r][c] > 0 && grid[r][c] !== prev_grid[r][c])
					row_changes[r]++;
			}
		}
	}

	/* 1. 3D skyscraper boxes: reuse scene + clue nodes so hover & drag stay smooth */
	if (!state.flat)
	{
		const board_px = state.compact ? 260 : 340;
		const size = Math.floor(board_px / (n + 2));
		const unit = Math.round(size * 0.46);
		const foot = size - 6;
		state.lift = Math.round(size * 0.36);
		state.size = size;

		let scene = stage.querySelector(".demo-scene");
		let board = scene ? scene.querySelector(".sky-board") : null;
		let clues_layer = board ? board.querySelector(".sky-clues-layer") : null;
		let dyn_layer = board ? board.querySelector(".sky-dyn-layer") : null;
		if (!scene || !clues_layer || Number(board.dataset.n) !== n)
		{
			let chtml = "";
			for (let k = 0; k < 4 * n; k++)
			{
				const rc = sky_clue_cell(n, k);
				chtml += `<button type="button" class="sky-clue" data-dk="${k}" `
					+ `style="left:${(rc[1] + 1) * size}px;top:${(rc[0] + 1) * size}px;`
					+ `width:${size}px;height:${size}px;--d:${k % n}">`
					+ `<span class="chip">${rec.clues[k]}</span></button>`;
			}
			stage.innerHTML = bar_html
				+ "<div class=\"sky-scene demo-scene\" title=\"drag to rotate\">"
				+ `<div class="sky-board" data-n="${n}" style="width:${(n + 2) * size}px;`
				+ `height:${(n + 2) * size}px;font-size:${Math.round(size * 0.4)}px">`
				+ `<div class="sky-ground" style="left:${size}px;top:${size}px;`
				+ `width:${n * size}px;height:${n * size}px;`
				+ `background-size:${size}px ${size}px"></div>`
				+ "<div class=\"sky-beam hover-beam\" hidden></div>"
				+ `<div class="sky-clues-layer">${chtml}</div>`
				+ "<div class=\"sky-dyn-layer\"></div></div></div>"
				+ "<p class=\"demo-sightline\"></p>";
			scene = stage.querySelector(".demo-scene");
			board = scene.querySelector(".sky-board");
			clues_layer = board.querySelector(".sky-clues-layer");
			dyn_layer = board.querySelector(".sky-dyn-layer");
			demo_wire_skybar(state, stage);
			demo_drag(state, scene);
			demo_wire_clue_hover(state, scene);
		}

		/* update existing clue chips in place (never destroys hovered button) */
		const chip_nodes = clues_layer.querySelectorAll(".sky-clue[data-dk]");
		for (const chip of chip_nodes)
		{
			const k = Number(chip.dataset.dk);
			const want = rec.clues[k];
			const chip_el = chip.querySelector(".chip");
			if (chip_el.textContent !== String(want))
				chip_el.textContent = String(want);
			const is_ok = Boolean(counts && counts[k] === want) || is_win;
			const is_cbad = Boolean((counts && counts[k] !== want) || cues.bad_clues[k]);
			chip.classList.toggle("ok", is_ok && !is_cbad);
			chip.classList.toggle("bad", is_cbad);
			chip.classList.toggle("pulse-bad", Boolean(cues.bad_clues[k]));
			chip.classList.toggle("on", Boolean(cues.gold_clues[k]));
			chip.classList.toggle("pulse-gold", Boolean(cues.gold_clues[k]));
			chip.classList.toggle("anim-win-chip", is_win);
			const old_sb = chip.querySelector(".cnt.step-cnt");
			if (cues.seen_badge[k] !== undefined)
			{
				const sb = old_sb || document.createElement("span");
				sb.className = "cnt step-cnt";
				sb.textContent = String(cues.seen_badge[k]);
				if (!old_sb)
					chip.appendChild(sb);
			}
			else if (old_sb)
				old_sb.remove();
		}

		/* rebuild only dynamic step beams + skyscraper boxes */
		let bhtml = "";
		if (cues.beam_row >= 0)
		{
			bhtml += `<div class="sky-beam ${cues.beam_bad ? "bad" : (step.op === "prefill" ? "gold" : "guide")}" `
				+ `style="left:${size}px;top:${(cues.beam_row + 1) * size}px;`
				+ `width:${n * size}px;height:${size}px"></div>`;
		}
		if (cues.beam_col >= 0)
		{
			bhtml += `<div class="sky-beam ${cues.beam_bad ? "bad" : (step.op === "prefill" ? "gold" : "guide")}" `
				+ `style="left:${(cues.beam_col + 1) * size}px;top:${size}px;`
				+ `width:${size}px;height:${n * size}px"></div>`;
		}
		if (grid)
		{
			for (let r = 0; r < n; r++)
			{
				for (let c = 0; c < n; c++)
				{
					const h = grid[r][c];
					const ph = prev_grid ? prev_grid[r][c] : 0;
					const is_focus = focus && focus[0] === r && focus[1] === c;
					let extra = "";
					let delay = 0;
					let draw_h = h;

					if (is_win)
					{
						extra = " anim-win";
						delay = r + c;
					}
					else if (step.op === "backtrack" && ph > 0 && h === 0)
					{
						/* collapsing orange ghost tower at previous height */
						draw_h = ph;
						extra = " demo-bad anim-undo";
					}
					else if (h > 0)
					{
						if (is_focus && is_bad)
							extra = " demo-bad anim-shake";
						else if (is_bad && (r === cues.beam_row || c === cues.beam_col))
							extra = " demo-bad anim-shake";
						else if (is_focus && step.op === "prefill")
							extra = " demo-cur anim-lock";
						else if (is_focus)
							extra = " demo-cur";
						if (h !== ph && !is_bad)
						{
							extra += " anim-rise";
							if (row_changes[r] >= 2)
								delay = c;
						}
					}
					else if (is_focus && step.op === "backtrack")
						extra = " demo-bad";

					let box = sky_box(draw_h, n, [r, c], [size, unit, foot]);
					if (extra)
						box = box.replace("class=\"sky-box", "class=\"sky-box" + extra);
					if (delay)
						box = box.replace("style=\"", `style="--d:${delay};`);
					bhtml += box;
				}
			}
		}
		else
		{
			bhtml += `<div class="sky-msg" style="left:${size}px;top:${size}px;`
				+ `width:${n * size}px;height:${n * size}px">Error</div>`;
		}
		dyn_layer.innerHTML = bhtml;
		demo_turn(state);
		demo_apply_clue_hover(state, false);
		return;
	}
	/* 2. 2D grid with matching height colours & hover sightline */
	let html = bar_html
		+ `<div class="sky-flat demo-flat" style="grid-template-columns:repeat(${n + 2},minmax(0,1fr));max-width:${(n + 2) * 48}px">`;
	for (let r = -1; r <= n; r++)
	{
		for (let c = -1; c <= n; c++)
		{
			const k = sky_flat_clue(n, r, c);
			if (k >= 0)
			{
				let cls = counts ? (counts[k] === rec.clues[k] ? " ok" : " bad") : "";
				if (cues.bad_clues[k])
					cls += " bad pulse-bad";
				else if (cues.gold_clues[k])
					cls += " on pulse-gold";
				const badge = cues.seen_badge[k] !== undefined
					? `<span class="cnt">${cues.seen_badge[k]}</span>` : "";
				html += `<button type="button" class="sky-clue${cls}" data-dk="${k}">`
					+ `<span class="chip">${rec.clues[k]}</span>${badge}</button>`;
			}
			else if (r < 0 || c < 0 || r === n || c === n)
				html += "<span class=\"sky-corner\"></span>";
			else if (grid && grid[r][c] > 0)
			{
				const h = grid[r][c];
				const ph = prev_grid ? prev_grid[r][c] : 0;
				const shade = h / n;
				const is_focus = focus && focus[0] === r && focus[1] === c;
				let fcls = "";
				if (is_win)
					fcls = " anim-win-2d";
				else if ((is_focus && is_bad) || (is_bad && (r === cues.beam_row || c === cues.beam_col)))
					fcls = " demo-bad anim-shake";
				else if (is_focus && step.op === "prefill")
					fcls = " demo-cur anim-lock-2d";
				else if (is_focus)
					fcls = " demo-cur";
				if (h !== ph && !is_bad && !is_win)
					fcls += " anim-pop";
				html += `<span class="sky-cell${fcls}" data-r="${r}" data-c="${c}" `
					+ `data-h="${h}" style="--shade:${shade.toFixed(2)};--d:${r + c}">${h}</span>`;
			}
			else
			{
				const ph = prev_grid ? prev_grid[r][c] : 0;
				const undo = step.op === "backtrack" && ph > 0 ? " anim-undo-2d" : "";
				html += `<span class="sky-cell empty${undo}" data-r="${r}" data-c="${c}">${undo ? ph : ""}</span>`;
			}
		}
	}
	stage.innerHTML = html + "</div><p class=\"demo-sightline\"></p>";
	demo_wire_skybar(state, stage);
	demo_wire_clue_hover(state, stage.querySelector(".demo-flat"));
	demo_apply_clue_hover(state, false);
}

/* ---- Parse renderer: read-head cursor + FSM diagram + clues drop-in ------ */

function demo_draw_parse(state, rec, stage, step)
{
	const s = rec.argv;
	const pos = step.pos;
	const prev_len = state.prev_step && state.prev_step.clues
		? state.prev_step.clues.length : 0;
	const is_fixed = state.demo_id === "parse_fixed";
	let tape = "";

	/* 1. character tape with floating read-head pointer */
	for (let i = 0; i < s.length; i++)
	{
		let cls = "ptok";
		let head = "";
		if (i === pos)
		{
			cls += step.op === "reject" ? " cur bad anim-shake" : " cur anim-pop";
			head = "<i class=\"phead\">▼</i>";
		}
		else if (i < pos)
			cls += " past";
		const ch = s[i] === " " ? "␣" : page_esc(s[i]);
		const stride = is_fixed
			? `<em class="pstride">${i % 2 === 0 ? "d" : "sp"}</em>` : "";
		tape += `<span class="${cls}">${head}<small>${i}</small><b>${ch}</b>${stride}</span>`;
	}
	/* 2. FSM state diagram OR split words ribbon */
	let extra = "";
	if (step.state)
	{
		const on_d = step.state === "EXPECT_DIGIT";
		extra += "<div class=\"parse-fsm\">"
			+ `<span class="fsm-node${on_d ? " on anim-pop" : ""}">EXPECT_DIGIT</span>`
			+ `<span class="fsm-arr${on_d ? " rev" : ""}">⇄</span>`
			+ `<span class="fsm-node${!on_d ? " on anim-pop" : ""}">EXPECT_SPACE</span>`
			+ "</div>";
	}
	if (step.words)
	{
		extra += "<div class=\"demo-words\">" + step.words.map(function (w, i)
		{
			const cls = i === step.word_idx ? " on anim-pop"
				: (i < step.word_idx ? " past" : "");
			return `<span class="dword${cls}">"${page_esc(w)}"</span>`;
		}).join("") + "</div>";
	}
	const clues = step.clues || [];
	const edge_names = ["TOP (0..3)", "BOTTOM (4..7)", "LEFT (8..11)", "RIGHT (12..15)"];
	let edges = "<div class=\"parse-edges\">";
	for (let e = 0; e < 4; e++)
	{
		let grp = `<div class="parse-edge"><span class="pe-lbl">${edge_names[e]}</span><div class="demo-slots">`;
		for (let j = 0; j < 4; j++)
		{
			const k = e * 4 + j;
			const has = k < clues.length;
			const fresh = has && k >= prev_len && step.op === "store";
			const bad = has && (clues[k] < 1 || clues[k] > 4);
			const h_attr = has && !bad ? ` data-h="${clues[k]}"` : "";
			let cls = "";
			if (bad)
				cls = " bad anim-shake";
			else if (fresh)
				cls = " on anim-pop";
			else if (has)
				cls = " ok";
			grp += `<span class="dslot${cls}"${h_attr}><small>${k}</small><b>${has ? clues[k] : "·"}</b></span>`;
		}
		edges += grp + "</div></div>";
	}
	edges += "</div>";
	stage.innerHTML = `<div class="demo-tape">${tape}</div>${extra}`
		+ `<p class="lab">CLUES ARRAY BY EDGE (${clues.length}/16)</p>${edges}`;
}

/* ---- Data renderer: memory diagrams + live bit LEDs + candidate pips ----- */

function demo_draw_data(state, rec, stage, step)
{
	const g = step.grid || demo_empty_grid(4);
	const prev = state.prev_step;
	const focus = step.focus || null;
	const layout = step.layout || "grid2d";
	let body = "";

	/* 1. formula bar */
	if (step.formula)
		body += `<p class="demo-formula"><code>${page_esc(step.formula)}</code></p>`;
	/* 2. memory representation by layout */
	if (layout === "flat")
	{
		/* dual synchronized 2D (r,c) grid ↔ 1D [0..15] contiguous RAM strip */
		body += "<div class=\"data-dual\"><div><p class=\"lab\">2D VIEW (r, c)</p>"
			+ demo_mini_grid_html(g, focus, false, false, rec.clues) + "</div>"
			+ "<div class=\"data-arrow\">r × 4 + c<br>───▶</div>"
			+ "<div><p class=\"lab\">1D RAM [0..15]</p><div class=\"demo-slots flat-ram\">";
		for (let i = 0; i < 16; i++)
		{
			const r = Math.floor(i / 4);
			const v = g[r][i % 4];
			const cls = i === step.flat_idx ? " on anim-pop" : (v ? " ok" : "");
			body += `<span class="dslot rband-${r}${cls}"><small>[${i}]</small><b>${v || "·"}</b></span>`;
		}
		body += "</div></div></div>";
	}
	else if (layout === "malloc2d")
	{
		const alloc = step.rows_alloc || 0;
		const prev_alloc = prev && prev.rows_alloc !== undefined ? prev.rows_alloc : 0;
		body += "<div class=\"demo-malloc\"><p class=\"lab\">STACK POINTER → HEAP SPINE → HEAP ROWS</p>";
		for (let r = 0; r < 4; r++)
		{
			const active = r < alloc;
			const fresh_row = active && r >= prev_alloc;
			const row_focus = focus && focus[0] === r;
			body += `<div class="dm-row">`
				+ `<span class="dm-spine${active ? " live" : ""}">grid[${r}]</span>`
				+ `<span class="dm-arrow${active ? " live" : ""}${fresh_row ? " anim-slide" : ""}">`
				+ `${active ? "───▶" : "→ NULL"}</span>`;
			if (active)
			{
				body += `<span class="dm-heap${fresh_row ? " anim-slide" : ""}">`
					+ g[r].map(function (v, c)
					{
						const cls = row_focus && v ? " on anim-pop" : (v ? " ok" : "");
						return `<span class="dm-cell${cls}">${v || "0"}</span>`;
					}).join("") + "</span>";
			}
			body += "</div>";
		}
		body += "</div>";
	}
	else if (layout === "bits")
	{
		const rm = step.row_masks || [0, 0, 0, 0];
		const cm = step.col_masks || [0, 0, 0, 0];
		const prm = prev && prev.row_masks ? prev.row_masks : [0, 0, 0, 0];
		const pcm = prev && prev.col_masks ? prev.col_masks : [0, 0, 0, 0];
		body += "<div class=\"data-dual two\"><div><p class=\"lab\">BOARD</p>"
			+ demo_mini_grid_html(g, focus, false, false, rec.clues) + "</div>"
			+ "<div class=\"demo-masks\">"
			+ demo_bit_bank_html("ROW_USED[r] (bits 4..0)", "r", rm, prm)
			+ demo_bit_bank_html("COL_USED[c] (bits 4..0)", "c", cm, pcm)
			+ "</div></div>";
	}
	else if (layout === "cand")
	{
		const cands = step.cands || [];
		const pcands = prev && prev.cands ? prev.cands : null;
		body += "<div class=\"demo-candgrid\">";
		for (let r = 0; r < 4; r++)
		{
			for (let c = 0; c < 4; c++)
			{
				const v = g[r][c];
				const is_f = focus && focus[0] === r && focus[1] === c;
				if (v)
				{
					body += `<span class="dc-cell set${is_f ? " on anim-pop" : ""}">${v}</span>`;
				}
				else
				{
					const mask = cands[r] ? cands[r][c] : 0b11110;
					const pmask = pcands && pcands[r] ? pcands[r][c] : mask;
					const live_cnt = [1, 2, 3, 4].filter(function (k)
					{
						return (mask & (1 << k)) !== 0;
					}).length;
					let pips = "";
					for (let k = 1; k <= 4; k++)
					{
						const bit = 1 << k;
						const on = (mask & bit) !== 0;
						const elim = !on && (pmask & bit) !== 0;
						const pcls = on ? (live_cnt === 1 ? " single" : " on")
							: (elim ? " elim" : " off");
						pips += `<i class="dc-pip${pcls}">${k}</i>`;
					}
					const line_hit = focus && (focus[0] === r || focus[1] === c);
					body += `<span class="dc-cell${live_cnt === 1 ? " dc-single" : ""}`
						+ `${line_hit ? " dc-hit" : ""}">`
						+ `<span class="dc-pips">${pips}</span></span>`;
				}
			}
		}
		body += "</div>";
	}
	else if (layout === "struct")
	{
		body += "<div class=\"dm-struct\"><div class=\"dm-struct-head\">"
			+ "<span>t_board *b</span><code>n = 4</code><code>clues[16]</code></div>"
			+ demo_mini_grid_html(g, focus, false, false, rec.clues) + "</div>";
	}
	else if (layout === "char")
	{
		const fv = focus ? g[focus[0]][focus[1]] : 0;
		body += demo_mini_grid_html(g, focus, true, false, rec.clues);
		if (fv)
		{
			body += `<p class="demo-ascii anim-pop"><code>'${fv}'</code> = `
				+ `decimal <b>${48 + fv}</b> · hex <b>0x${(48 + fv).toString(16)}</b>`
				+ " (ready for <code>write(1, &amp;cell, 1)</code>)</p>";
		}
	}
	else
	{
		body += demo_mini_grid_html(g, focus, false,
			Boolean(step.border), rec.clues);
	}
	stage.innerHTML = body;
}

function demo_bit_bank_html(title, prefix, masks, prev_masks)
{
	let html = `<p class="lab">${title}</p><div class="bit-bank">`;

	for (let i = 0; i < masks.length; i++)
	{
		const m = masks[i];
		const pm = prev_masks[i] || 0;
		let bits = "";
		for (let b = 4; b >= 0; b--)
		{
			const on = (m & (1 << b)) !== 0;
			const fresh = on && ((pm & (1 << b)) === 0);
			bits += `<i class="bit-led${on ? " on" : ""}${fresh ? " fresh" : ""}" `
				+ `title="bit ${b}">${on ? "1" : "0"}</i>`;
		}
		html += `<div class="bit-row"><code>${prefix}[${i}]</code>${bits}</div>`;
	}
	return html + "</div>";
}

function demo_mini_grid_html(g, focus, as_char, with_border, clues)
{
	const n = g.length;
	let html = `<div class="sky-flat demo-flat" style="grid-template-columns:repeat(${with_border ? n + 2 : n},minmax(0,1fr));max-width:${(with_border ? n + 2 : n) * 52}px">`;
	const lo = with_border ? -1 : 0;
	const hi = with_border ? n : n - 1;

	for (let r = lo; r <= hi; r++)
	{
		for (let c = lo; c <= hi; c++)
		{
			if (with_border)
			{
				const k = sky_flat_clue(n, r, c);
				if (k >= 0)
				{
					const hit = focus && ((k === focus[1]) || (k === n + focus[1])
						|| (k === 2 * n + focus[0]) || (k === 3 * n + focus[0]));
					html += `<span class="sky-clue ok${hit ? " on pulse-gold" : ""}">`
						+ `<span class="chip">${clues[k]}</span></span>`;
					continue;
				}
				if (r < 0 || c < 0 || r === n || c === n)
				{
					html += "<span class=\"sky-corner\"></span>";
					continue;
				}
			}
			const v = g[r][c];
			const cls = focus && focus[0] === r && focus[1] === c ? " seen anim-pop" : "";
			const lbl = v ? (as_char ? `'${v}'` : String(v)) : (as_char ? "'0'" : "0");
			html += `<span class="sky-cell${v ? cls : " empty"}" style="--shade:${(v / n).toFixed(2)}">${lbl}</span>`;
		}
	}
	return html + "</div>";
}

/* ---- Print renderer: animated BUFFER ── write() ──▶ STDOUT pipeline ------ */

function demo_draw_print(state, rec, stage, step)
{
	const buf = step.buf || "";
	const out = step.out || "";
	const writes = step.writes || 0;
	const prev_out = state.prev_step && state.prev_step.out ? state.prev_step.out : "";
	const flushing = step.op === "emit" || step.op === "flush";
	const buffering = step.op === "buffer";
	let out_html = "(nothing yet)";

	if (out)
	{
		if (flushing && out.startsWith(prev_out) && out.length > prev_out.length)
		{
			out_html = page_esc(prev_out)
				+ `<mark class="dp-fresh">${page_esc(out.slice(prev_out.length))}</mark>`;
		}
		else
			out_html = page_esc(out);
	}
	const bytes_sent = flushing ? Math.max(1, out.length - prev_out.length) : 0;
	const pipe_lbl = flushing ? `write(1, …, ${bytes_sent})` : "write()";

	stage.innerHTML = "<div class=\"demo-print\">"
		+ `<div class="dp-box${buffering ? " dp-buf-on" : ""}">`
		+ "<p class=\"lab\">BUFFER</p>"
		+ `<pre>${buf ? `<mark class="dp-buf-mark">${page_esc(page_visible(buf, 200))}</mark>` : "(empty)"}</pre></div>`
		+ `<div class="dp-pipe${flushing ? " active" : ""}">`
		+ `<span class="dp-call">${pipe_lbl}</span>`
		+ "<span class=\"dp-track\"><i class=\"dp-pkt\"></i></span>"
		+ `<span class="dp-cnt${flushing ? " anim-pop" : ""}">#${writes}</span></div>`
		+ `<div class="dp-box${flushing ? " dp-out-on" : ""}">`
		+ `<p class="lab">STDOUT (${writes} write call${writes === 1 ? "" : "s"})</p>`
		+ `<pre>${out_html}</pre></div></div>`;
}

/* ---- Modal helper for /team/<name> "show how it works" button ------------ */

function demo_open_modal(entry, demo_id)
{
	let dlg = document.getElementById("demo-modal");

	/* 1. create modal overlay once */
	if (!dlg)
	{
		dlg = document.createElement("div");
		dlg.id = "demo-modal";
		dlg.className = "demo-modal";
		dlg.innerHTML = "<div class=\"card demo-modal-card\">"
			+ "<span class=\"tape c\"></span>"
			+ "<div class=\"demo-modal-head\"><div>"
			+ "<p class=\"lab\" id=\"dm-part\"></p>"
			+ "<h3 id=\"dm-title\"></h3>"
			+ "<p class=\"explain\" id=\"dm-explain\"></p></div>"
			+ "<div class=\"tools\">"
			+ "<a class=\"btn small\" id=\"dm-lib\" href=\"/library\">library</a>"
			+ "<button class=\"btn small\" id=\"dm-close\" type=\"button\">close</button>"
			+ "</div></div><div id=\"dm-body\"></div></div>";
		document.body.appendChild(dlg);
		dlg.addEventListener("click", function (ev)
		{
			if (ev.target === dlg || ev.target.id === "dm-close")
				demo_close_modal();
		});
		document.addEventListener("keydown", function (ev)
		{
			if (ev.key === "Escape" && !dlg.hidden)
				demo_close_modal();
		});
	}
	/* 2. stop any previous playback and mount the requested preset */
	if (dlg._state)
		demo_stop(dlg._state);
	const key = String(demo_id || (entry && entry.demo) || "").replace(".", "_");
	dlg.querySelector("#dm-part").textContent = entry
		? (entry.part.toUpperCase() + (entry.tier !== null && entry.tier !== undefined
			? ` · TIER ${entry.tier}` : "")) : "PRESET DEMO";
	dlg.querySelector("#dm-title").textContent = entry ? entry.name : key;
	dlg.querySelector("#dm-explain").textContent = entry ? entry.explain : "";
	dlg.querySelector("#dm-lib").href = "/library#" + encodeURIComponent(key);
	dlg.hidden = false;
	dlg._state = demo_mount(dlg.querySelector("#dm-body"), {
		demo_id: key,
		entry: entry,
		show_puzzle_pick: true
	});
}

function demo_close_modal()
{
	const dlg = document.getElementById("demo-modal");

	if (!dlg)
		return;
	if (dlg._state)
		demo_stop(dlg._state);
	dlg.hidden = true;
}
