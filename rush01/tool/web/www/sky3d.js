/* sky3d.js: a team's real output as skyscrapers (CONTRACT.md B4). CSS 3D
   transforms only, no WebGL, no libs; a 2D grid with the same sightlines is
   the fallback. The pure part (clues, lines, counts) is exported for node. */

"use strict";

const SKY_SIDES = ["top", "bottom", "left", "right"];
const SKY_LOOK = {top: "down", bottom: "up", left: "right", right: "left"};
const SKY_BOARD_PX = 440;
const SKY_VIEWS = {top: [0, 0], front: [74, 0], iso: [58, -34]};
const SKY_DRAW_CAP = 9;         /* a taller number is drawn 9 high, labelled true */
const SKY_DRAG_PX = 4;          /* moved less than this: a click, not a drag */

/* ---- the pure part ------------------------------------------------------ */

/* the subject's input (PLAN.md §3): one argument, 4N numbers 1..N, single
   spaces. Anything else is not a puzzle you can look at: null. */
function sky_clues_from_argv(argv)
{
	if (!Array.isArray(argv) || argv.length !== 1)
		return null;
	if (!/^[1-9]( [1-9])*$/.test(argv[0]))
		return null;
	const clues = argv[0].split(" ").map(Number);
	const n = clues.length / 4;
	if (clues.length % 4 !== 0 || n < 1 || n > 9)
		return null;
	if (clues.some(function (v)
	{
		return v > n;
	}))
		return null;
	return {n: n, clues: clues};
}

/* the cells a clue looks at, nearest first (SHAPES: top looks down col i,
   bottom looks up col i, left looks right along row i, right looks left) */
function sky_line(n, side, index)
{
	const cells = [];

	for (let k = 0; k < n; k++)
	{
		if (side === "top")
			cells.push([k, index]);
		else if (side === "bottom")
			cells.push([n - 1 - k, index]);
		else if (side === "left")
			cells.push([index, k]);
		else
			cells.push([index, n - 1 - k]);
	}
	return cells;
}

/* a building is seen when it is taller than every one before it */
function sky_seen(heights)
{
	const visible = [];
	let tallest = 0;
	let count = 0;

	for (const h of heights)
	{
		if (h > tallest)
		{
			tallest = h;
			count++;
			visible.push(true);
		}
		else
			visible.push(false);
	}
	return {count: count, visible: visible};
}

/* what each of the 4N clues sees on this grid, in clue order */
function sky_counts(grid)
{
	const n = grid.length;
	const out = [];

	for (const side of SKY_SIDES)
	{
		for (let i = 0; i < n; i++)
		{
			const heights = sky_line(n, side, i).map(function (rc)
			{
				return grid[rc[0]][rc[1]];
			});
			out.push(sky_seen(heights).count);
		}
	}
	return out;
}

/* ---- the view ------------------------------------------------------------ */

/* root: an empty element. runs: the team's runs (SHAPES "run"). */
function sky_mount(root, runs)
{
	const view = {root: root, runs: [], run: null, n: 0, clues: [],
		grid: null, rx: SKY_VIEWS.iso[0], rz: SKY_VIEWS.iso[1], sel: -1,
		hover: -1, flat: false, dragged: false, dragging: false,
		boxes: [], cells: [], chips: []};

	/* 1. only runs with a well-formed puzzle can be drawn */
	for (const run of runs)
	{
		if (sky_clues_from_argv(run.argv))
			view.runs.push(run);
	}
	root.innerHTML = "<div class=\"sky-bar\">"
		+ "<label class=\"sky-picklab\">puzzle <select class=\"sky-pick\">"
		+ "</select></label><span class=\"sp\"></span>"
		+ "<span class=\"sky-views\">"
		+ "<button class=\"btn small\" type=\"button\" data-view=\"top\">top</button>"
		+ "<button class=\"btn small\" type=\"button\" data-view=\"front\">front</button>"
		+ "<button class=\"btn small\" type=\"button\" data-view=\"iso\">iso</button>"
		+ "</span><button class=\"btn small sky-mode\" type=\"button\" "
		+ "title=\"the same sightlines on a flat grid\">2D</button></div>"
		+ "<div class=\"sky-out\"></div>"
		+ "<div class=\"sky-stage\"><div class=\"sky-scene\">"
		+ "<div class=\"sky-board\"></div></div>"
		+ "<div class=\"sky-flat\" hidden></div></div>"
		+ "<p class=\"sky-line\"></p>"
		+ "<p class=\"sky-legend\">Heights are colour-coded 1..N. Hover or click "
		+ "any edge clue to see its sightline: <b class=\"k-seen\">teal</b> = "
		+ "seen, faded = hidden behind a taller one. Count badge is "
		+ "<b class=\"k-bad\">orange</b> on mismatch. Drag to turn.</p>";
	if (!view.runs.length)
	{
		root.innerHTML = "<p class=\"empty\">No run with a well-formed puzzle "
			+ "to draw (no build, or no runs).</p>";
		return view;
	}
	/* 2. the picker, grouped like the bank */
	const pick = root.querySelector(".sky-pick");
	let html = "";
	let group = null;
	for (const run of view.runs)
	{
		if (run.group !== group)
		{
			html += (group === null ? "" : "</optgroup>")
				+ `<optgroup label="${page_esc(run.group)}">`;
			group = run.group;
		}
		html += `<option value="${page_esc(run.id)}">${page_esc(run.id)} · `
			+ `${page_esc(run.verdict)} · ${page_esc(page_run_output(run))}`
			+ "</option>";
	}
	pick.innerHTML = html + "</optgroup>";
	pick.onchange = function ()
	{
		sky_show(view, pick.value);
	};
	/* 3. views, the 2D toggle, dragging */
	for (const btn of root.querySelectorAll("[data-view]"))
	{
		btn.onclick = function ()
		{
			view.rx = SKY_VIEWS[btn.dataset.view][0];
			view.rz = SKY_VIEWS[btn.dataset.view][1];
			sky_turn(view);
		};
	}
	root.querySelector(".sky-mode").onclick = function ()
	{
		view.flat = !view.flat;
		sky_mode(view);
	};
	sky_drag(view);
	/* 4. first run shown: a wrong grid if there is one, it says the most */
	let first = view.runs[0];
	for (const run of view.runs)
	{
		if (run.verdict === "fail" && run.grid)
		{
			first = run;
			break;
		}
	}
	sky_show(view, first.id);
	return view;
}

/* show one run: their real output on its puzzle */
function sky_show(view, run_id)
{
	const run = view.runs.find(function (r)
	{
		return r.id === run_id;
	});
	if (!run)
		return false;
	const puzzle = sky_clues_from_argv(run.argv);
	view.run = run;
	view.n = puzzle.n;
	view.clues = puzzle.clues;
	view.grid = null;
	view.sel = -1;
	view.hover = -1;
	if (run.grid && run.grid.length === puzzle.n)
		view.grid = run.grid;
	view.root.querySelector(".sky-pick").value = run.id;
	sky_out(view);
	sky_build(view);
	sky_build_flat(view);
	sky_mode(view);
	sky_apply(view);
	return true;
}

/* the run's stamp: what it printed and why it passed or failed */
function sky_out(view)
{
	const run = view.run;
	const cls = {pass: "ok", fail: "bad", info: "na"}[run.verdict] || "na";
	let why = run.reasons.concat(run.notes).join(" · ");

	if (!why && run.verdict === "pass")
		why = run.expect === "error" ? "Error was expected" : "every clue holds";
	view.root.querySelector(".sky-out").innerHTML =
		`<span class="st ${cls}">${page_esc(run.verdict)}</span> `
		+ `<b>${page_esc(run.id)}</b> · their output: `
		+ `<b>${page_esc(page_run_output(run))}</b>`
		+ (why ? ` <span class="why">${page_esc(why)}</span>` : "");
}

/* the 3D board: ground, 4N clue chips standing up, one box per cell */
function sky_build(view)
{
	const n = view.n;
	const size = Math.floor(SKY_BOARD_PX / (n + 2));
	const unit = Math.round(size * 0.5);
	const foot = size - 6;
	const board = view.root.querySelector(".sky-board");
	let html = "";

	/* 1. the board and its ground */
	board.style.width = (n + 2) * size + "px";
	board.style.height = (n + 2) * size + "px";
	board.style.fontSize = Math.round(size * 0.42) + "px";
	html += `<div class="sky-ground" style="left:${size}px;top:${size}px;`
		+ `width:${n * size}px;height:${n * size}px;`
		+ `background-size:${size}px ${size}px"></div>`
		+ "<div class=\"sky-beam\" hidden></div>";
	/* 2. clue chips around the base */
	for (let k = 0; k < 4 * n; k++)
	{
		const rc = sky_clue_cell(n, k);
		html += `<button type="button" class="sky-clue" data-k="${k}" `
			+ `style="left:${(rc[1] + 1) * size}px;top:${(rc[0] + 1) * size}px;`
			+ `width:${size}px;height:${size}px">`
			+ `<span class="chip">${view.clues[k]}</span>`
			+ "<span class=\"cnt\"></span></button>";
	}
	/* 3. the buildings; with no grid, the output is written on the ground */
	if (view.grid)
	{
		for (let r = 0; r < n; r++)
		{
			for (let c = 0; c < n; c++)
			{
				let b = sky_box(view.grid[r][c], n, [r, c], [size, unit, foot]);
				if (view.grid[r][c] > 0)
				{
					b = b.replace("class=\"sky-box", "class=\"sky-box anim-rise")
						.replace("style=\"", `style="--d:${r + c};`);
				}
				html += b;
			}
		}
	}
	else
	{
		html += `<div class="sky-msg" style="left:${size}px;top:${size}px;`
			+ `width:${n * size}px;height:${n * size}px">`
			+ `${page_esc(page_run_output(view.run))}</div>`;
	}
	view.size = size;
	board.innerHTML = html;
	view.boxes = Array.from(board.querySelectorAll(".sky-box"));
	view.chips = Array.from(board.querySelectorAll(".sky-clue"));
	for (const chip of view.chips)
		sky_wire_chip(view, chip);
	sky_turn(view);
}

function sky_wire_chip(view, chip)
{
	const k = Number(chip.dataset.k);

	chip.onclick = function ()
	{
		sky_select(view, k);
	};
	chip.addEventListener("mouseenter", function ()
	{
		if (view.dragging || !view.grid)
			return;
		view.hover = k;
		sky_apply(view);
	});
	chip.addEventListener("mouseleave", function ()
	{
		if (view.hover === k)
		{
			view.hover = -1;
			sky_apply(view);
		}
	});
	chip.addEventListener("focus", function ()
	{
		if (!view.grid)
			return;
		view.hover = k;
		sky_apply(view);
	});
	chip.addEventListener("blur", function ()
	{
		if (view.hover === k)
		{
			view.hover = -1;
			sky_apply(view);
		}
	});
}

/* where clue k sits around the grid, as [row, col] with -1 and n outside */
function sky_clue_cell(n, k)
{
	const side = SKY_SIDES[Math.floor(k / n)];
	const i = k % n;

	if (side === "top")
		return [-1, i];
	if (side === "bottom")
		return [n, i];
	if (side === "left")
		return [i, -1];
	return [i, n];
}

/* one building: a single box h units high (5 faces), floors drawn as lines.
   A height outside 1..n is drawn as it is, with its number in orange. */
function sky_box(h, n, rc, dims)
{
	const size = dims[0];
	const unit = dims[1];
	const foot = dims[2];
	const odd = h < 1 || h > n ? " odd" : "";
	const tall = Math.min(Math.max(h, 0), SKY_DRAW_CAP) * unit;
	const pos = `left:${(rc[1] + 1) * size + 3}px;top:${(rc[0] + 1) * size + 3}px;`
		+ `width:${foot}px;height:${foot}px`;
	const floors = `--floor:${unit}px`;

	if (tall === 0)
	{
		return `<div class="sky-box flat${odd}" data-r="${rc[0]}" `
			+ `data-c="${rc[1]}" style="${pos}"><div class="f top" `
			+ `style="width:${foot}px;height:${foot}px;transform:translateZ(1px)">`
			+ `<span>${h}</span></div></div>`;
	}
	const half = tall / 2;
	const side_ns = `width:${foot}px;height:${tall}px;left:0;`
		+ `top:${(foot - tall) / 2}px;${floors}`;
	const side_ew = `width:${tall}px;height:${foot}px;top:0;`
		+ `left:${(foot - tall) / 2}px;${floors}`;
	const h_attr = h >= 1 && h <= SKY_DRAW_CAP ? ` data-h="${h}"` : "";

	return `<div class="sky-box${odd}" data-r="${rc[0]}" data-c="${rc[1]}"`
		+ `${h_attr} style="${pos}">`
		+ `<div class="f ns" style="${side_ns};transform:translateZ(${half}px) `
		+ `rotateX(90deg) translateZ(${foot / 2}px)"></div>`
		+ `<div class="f ns" style="${side_ns};transform:translateZ(${half}px) `
		+ `rotateX(-90deg) translateZ(${foot / 2}px)"></div>`
		+ `<div class="f ew" style="${side_ew};transform:translateZ(${half}px) `
		+ `rotateY(90deg) translateZ(${foot / 2}px)"></div>`
		+ `<div class="f ew" style="${side_ew};transform:translateZ(${half}px) `
		+ `rotateY(-90deg) translateZ(${foot / 2}px)"></div>`
		+ `<div class="f top" style="width:${foot}px;height:${foot}px;`
		+ `transform:translateZ(${tall}px)"><span>${h}</span></div></div>`;
}

/* the 2D fallback: the same grid and clue chips, flat */
function sky_build_flat(view)
{
	const n = view.n;
	const flat = view.root.querySelector(".sky-flat");
	let html = "";

	flat.style.gridTemplateColumns = `repeat(${n + 2}, minmax(0, 1fr))`;
	flat.style.maxWidth = Math.min(SKY_BOARD_PX, (n + 2) * 56) + "px";
	for (let r = -1; r <= n; r++)
	{
		for (let c = -1; c <= n; c++)
		{
			const k = sky_flat_clue(n, r, c);

			if (k >= 0)
			{
				html += `<button type="button" class="sky-clue" data-k="${k}">`
					+ `<span class="chip">${view.clues[k]}</span>`
					+ "<span class=\"cnt\"></span></button>";
			}
			else if (r < 0 || c < 0 || r === n || c === n)
				html += "<span class=\"sky-corner\"></span>";
			else if (view.grid)
			{
				const h = view.grid[r][c];
				const odd = h < 1 || h > n ? " odd" : "";
				const shade = Math.min(Math.max(h, 0), n) / n;
				const h_attr = h >= 1 && h <= SKY_DRAW_CAP ? ` data-h="${h}"` : "";

				html += `<span class="sky-cell${odd}" data-r="${r}" data-c="${c}"`
					+ `${h_attr} style="--shade:${shade.toFixed(2)}">${h}</span>`;
			}
			else
				html += "<span class=\"sky-cell empty\"></span>";
		}
	}
	if (!view.grid)
	{
		html += `<p class="sky-flatmsg">${page_esc(page_run_output(view.run))}`
			+ "</p>";
	}
	flat.innerHTML = html;
	view.cells = Array.from(flat.querySelectorAll(".sky-cell[data-r]"));
	for (const chip of flat.querySelectorAll(".sky-clue"))
	{
		view.chips.push(chip);
		sky_wire_chip(view, chip);
	}
}

/* the clue index at [r, c] of the flat (n+2) x (n+2) layout, or -1 */
function sky_flat_clue(n, r, c)
{
	if (r === -1 && c >= 0 && c < n)
		return c;
	if (r === n && c >= 0 && c < n)
		return n + c;
	if (c === -1 && r >= 0 && r < n)
		return 2 * n + r;
	if (c === n && r >= 0 && r < n)
		return 3 * n + r;
	return -1;
}

function sky_mode(view)
{
	const root = view.root;

	root.querySelector(".sky-scene").hidden = view.flat;
	root.querySelector(".sky-flat").hidden = !view.flat;
	root.querySelector(".sky-views").hidden = view.flat;
	root.querySelector(".sky-mode").textContent = view.flat ? "3D" : "2D";
}

/* turn the board; clue chips counter-turn so they always face you */
function sky_turn(view)
{
	const board = view.root.querySelector(".sky-board");
	const lift = Math.round(SKY_BOARD_PX / (view.n + 2) * 0.36);

	board.style.transform = `rotateX(${view.rx}deg) rotateZ(${view.rz}deg)`;
	for (const chip of board.querySelectorAll(".sky-clue"))
	{
		chip.style.transform = `translateZ(${lift}px) rotateZ(${-view.rz}deg) `
			+ `rotateX(${-view.rx}deg)`;
	}
}

function sky_drag(view)
{
	const scene = view.root.querySelector(".sky-scene");

	scene.addEventListener("pointerdown", function (ev)
	{
		const x0 = ev.clientX;
		const y0 = ev.clientY;
		const rx0 = view.rx;
		const rz0 = view.rz;

		view.dragged = false;
		function move(e)
		{
			const dx = e.clientX - x0;
			const dy = e.clientY - y0;

			if (Math.abs(dx) + Math.abs(dy) < SKY_DRAG_PX && !view.dragged)
				return;
			view.dragged = true;
			view.dragging = true;
			view.rz = rz0 - dx * 0.4;
			view.rx = Math.max(0, Math.min(88, rx0 - dy * 0.4));
			sky_turn(view);
		}
		function up()
		{
			view.dragging = false;
			window.removeEventListener("pointermove", move);
			window.removeEventListener("pointerup", up);
		}
		window.addEventListener("pointermove", move);
		window.addEventListener("pointerup", up);
	});
	/* a drag that ends on a clue is not a click on it */
	scene.addEventListener("click", function (ev)
	{
		if (view.dragged)
		{
			ev.stopPropagation();
			view.dragged = false;
		}
	}, true);
}

/* click a clue: show its line; click it again: show everything */
function sky_select(view, k)
{
	if (!view.grid)
	{
		view.root.querySelector(".sky-line").textContent = "Nothing to look "
			+ "at: their output for this puzzle is not a grid.";
		return;
	}
	view.sel = view.sel === k ? -1 : k;
	sky_apply(view);
}

/* colour every box, cell and chip from the grid and the active (hovered or
   clicked) clue; when none is active, towers keep their height colours */
function sky_apply(view)
{
	const n = view.n;
	const active = view.hover >= 0 ? view.hover : view.sel;
	const role = {};
	const order = {};
	const counts = view.grid ? sky_counts(view.grid) : null;
	const text = view.root.querySelector(".sky-line");
	const beam = view.root.querySelector(".sky-board .sky-beam");

	/* 1. the active line: which cells are seen, which are hidden */
	if (active >= 0 && view.grid)
	{
		const side = SKY_SIDES[Math.floor(active / n)];
		const index = active % n;
		const line = sky_line(n, side, index);
		const seen = sky_seen(line.map(function (rc)
		{
			return view.grid[rc[0]][rc[1]];
		}));
		const want = view.clues[active];
		const ok = seen.count === want;
		const what = ok ? "matches the clue"
			: `does not match: the clue says ${want}`;

		line.forEach(function (rc, i)
		{
			const key = rc[0] + "," + rc[1];
			role[key] = seen.visible[i] ? "seen" : "hidden";
			order[key] = i;
		});
		if (beam && view.size)
		{
			const sz = view.size;
			const is_col = side === "top" || side === "bottom";
			beam.hidden = false;
			beam.className = "sky-beam " + (ok ? "ok" : "bad") + " dir-" + side;
			beam.style.left = (is_col ? (index + 1) * sz : sz) + "px";
			beam.style.top = (is_col ? sz : (index + 1) * sz) + "px";
			beam.style.width = (is_col ? sz : n * sz) + "px";
			beam.style.height = (is_col ? n * sz : sz) + "px";
		}
		text.innerHTML = `${side} clue ${index + 1} = <b>${want}</b>, looking `
			+ `${SKY_LOOK[side]}: their grid shows <b>${seen.count}</b> `
			+ `building${seen.count === 1 ? "" : "s"}, which `
			+ `<span class="${ok ? "k-ok" : "k-bad"}">`
			+ `${what}</span>.`;
	}
	else
	{
		text.textContent = "";
		if (beam)
			beam.hidden = true;
	}
	/* 2. boxes and flat cells: stagger wave along the clue's look direction */
	for (const el of view.boxes.concat(view.cells))
	{
		const key = el.dataset.r + "," + el.dataset.c;
		const r = role[key];

		el.classList.remove("anim-rise", "wave");
		el.classList.toggle("seen", r === "seen");
		el.classList.toggle("hidden", r === "hidden");
		el.classList.toggle("off", active >= 0 && !r);
		if (r)
		{
			el.style.setProperty("--d", String(order[key] || 0));
			void el.offsetWidth;
			el.classList.add("wave");
		}
	}
	/* 3. chips: every clue shows if it holds on their grid; the active
	      one shows its count */
	for (const chip of view.chips)
	{
		const k = Number(chip.dataset.k);
		const holds = counts && counts[k] === view.clues[k];

		chip.classList.toggle("on", k === active);
		chip.classList.toggle("ok", Boolean(counts) && holds);
		chip.classList.toggle("bad", Boolean(counts) && !holds);
		chip.querySelector(".cnt").textContent =
			k === active && counts ? String(counts[k]) : "";
	}
}

if (typeof module === "object" && module.exports)
{
	module.exports = {sky_clues_from_argv: sky_clues_from_argv,
		sky_line: sky_line, sky_seen: sky_seen, sky_counts: sky_counts,
		sky_clue_cell: sky_clue_cell, sky_flat_clue: sky_flat_clue};
}
