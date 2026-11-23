/* demos_gen.js: pure deterministic step generators for every catalog entry
   (CONTRACT.md B7, PLAN.md §8). No DOM; exported for node tests. Every preset
   shows how an approach works in general — never a trace of student code. */

"use strict";

const DEMO_STEP_CAP = 320;
const DEMO_BRUTE_TRY_CAP = 120;
const DEMO_PERM_TRY_CAP = 40000;

/* Sample 4x4 puzzles from the bank (ok4-01, ok4-11, ok4-07, slow4-01). */
const DEMO_PUZZLES = [
	{
		id: "pdf",
		label: "PDF example (symmetric)",
		n: 4,
		argv: "4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2",
		clues: [4, 3, 2, 1, 1, 2, 2, 2, 4, 3, 2, 1, 1, 2, 2, 2],
		solution: [[1, 2, 3, 4], [2, 3, 4, 1], [3, 4, 1, 2], [4, 1, 2, 3]]
	},
	{
		id: "asym",
		label: "Asymmetric 4x4 (ok4-11)",
		n: 4,
		argv: "2 3 2 1 3 2 1 2 4 1 2 2 1 3 3 2",
		clues: [2, 3, 2, 1, 3, 2, 1, 2, 4, 1, 2, 2, 1, 3, 3, 2]
	},
	{
		id: "hard",
		label: "Asymmetric harder (ok4-07)",
		n: 4,
		argv: "2 1 2 2 1 4 3 2 2 3 4 1 2 2 1 2",
		clues: [2, 1, 2, 2, 1, 4, 3, 2, 2, 3, 4, 1, 2, 2, 1, 2]
	},
	{
		id: "slow",
		label: "Slow for backtracking (slow4-01)",
		n: 4,
		argv: "1 2 3 3 4 2 1 2 1 2 3 3 4 2 1 2",
		clues: [1, 2, 3, 3, 4, 2, 1, 2, 1, 2, 3, 3, 4, 2, 1, 2]
	}
];

/* ---- small pure helpers -------------------------------------------------- */

function demo_clone_grid(grid)
{
	return grid.map(function (row)
	{
		return row.slice();
	});
}

function demo_empty_grid(n)
{
	const g = [];

	for (let r = 0; r < n; r++)
		g.push(new Array(n).fill(0));
	return g;
}

function demo_seen(arr)
{
	let tallest = 0;
	let count = 0;

	for (const h of arr)
	{
		if (h > tallest)
		{
			tallest = h;
			count++;
		}
	}
	return count;
}

function demo_check_line(arr, left_clue, right_clue)
{
	if (demo_seen(arr) !== left_clue)
		return false;
	return demo_seen(arr.slice().reverse()) === right_clue;
}

function demo_check_row(grid, clues, r)
{
	const n = grid.length;

	return demo_check_line(grid[r], clues[2 * n + r], clues[3 * n + r]);
}

function demo_check_col(grid, clues, c)
{
	const n = grid.length;
	const col = [];

	for (let r = 0; r < n; r++)
		col.push(grid[r][c]);
	return demo_check_line(col, clues[c], clues[n + c]);
}

function demo_check_all(grid, clues)
{
	const n = grid.length;

	for (let i = 0; i < n; i++)
	{
		if (!demo_check_row(grid, clues, i))
			return false;
		if (!demo_check_col(grid, clues, i))
			return false;
	}
	return true;
}

function demo_is_unique(grid, r, c, v)
{
	const n = grid.length;

	for (let i = 0; i < n; i++)
	{
		if (grid[r][i] === v || grid[i][c] === v)
			return false;
	}
	return true;
}

function demo_is_latin(grid)
{
	const n = grid.length;

	for (let i = 0; i < n; i++)
	{
		const row_seen = new Set();
		const col_seen = new Set();

		for (let j = 0; j < n; j++)
		{
			const rv = grid[i][j];
			const cv = grid[j][i];

			if (rv < 1 || rv > n || cv < 1 || cv > n)
				return false;
			row_seen.add(rv);
			col_seen.add(cv);
		}
		if (row_seen.size !== n || col_seen.size !== n)
			return false;
	}
	return true;
}

function demo_perms4()
{
	const out = [];
	const a = [1, 2, 3, 4];

	function go(k)
	{
		if (k === 4)
		{
			out.push(a.slice());
			return;
		}
		for (let i = k; i < 4; i++)
		{
			const tmp = a[k];
			a[k] = a[i];
			a[i] = tmp;
			go(k + 1);
			a[i] = a[k];
			a[k] = tmp;
		}
	}
	go(0);
	out.sort(function (x, y)
	{
		return x.join("").localeCompare(y.join(""));
	});
	return out;
}

/* Exact 4x4 solution for any puzzle (used by data & print demos). */
function demo_solve_exact(clues)
{
	const perms = demo_perms4();
	const rows = [0, 1, 2, 3].map(function (r)
	{
		return perms.filter(function (p)
		{
			return demo_check_line(p, clues[8 + r], clues[12 + r]);
		});
	});
	const grid = demo_empty_grid(4);

	function go(r)
	{
		if (r === 4)
		{
			for (let c = 0; c < 4; c++)
			{
				if (!demo_check_col(grid, clues, c))
					return false;
			}
			return true;
		}
		for (const p of rows[r])
		{
			let ok = true;

			for (let c = 0; c < 4; c++)
			{
				for (let pr = 0; pr < r; pr++)
				{
					if (grid[pr][c] === p[c])
						ok = false;
				}
			}
			if (!ok)
				continue;
			grid[r] = p.slice();
			if (go(r + 1))
				return true;
		}
		grid[r] = [0, 0, 0, 0];
		return false;
	}
	return go(0) ? grid : null;
}

/* Recorder with a fixed step cap (FLOW-3): counts every real step truthfully,
   keeps the first DEMO_STEP_CAP steps plus the final summary step. */
function demo_make_rec(kind, puzzle)
{
	return {
		kind: kind,
		n: puzzle.n,
		clues: puzzle.clues.slice(),
		argv: puzzle.argv,
		steps: [],
		total: 0,
		stats: {place: 0, reject: 0, backtrack: 0, prune: 0, writes: 0},
		capped: false,
		solved: false,
		grid: null
	};
}

function demo_push(rec, step)
{
	rec.total++;
	if (step.op === "place" || step.op === "prefill")
		rec.stats.place++;
	else if (step.op === "reject")
		rec.stats.reject++;
	else if (step.op === "backtrack")
		rec.stats.backtrack++;
	else if (step.op === "prune")
		rec.stats.prune++;
	if (rec.steps.length < DEMO_STEP_CAP)
		rec.steps.push(step);
}

function demo_finish(rec, grid, text, is_cap)
{
	/* 1. if intermediate steps were trimmed, add an honest skip note */
	const hidden = rec.total - rec.steps.length;

	if (hidden > 0)
	{
		rec.steps.push({
			op: "skip",
			grid: grid ? demo_clone_grid(grid) : null,
			text: `… ${hidden} intermediate steps omitted (showing first `
				+ `${rec.steps.length} + result)`
		});
	}
	/* 2. final step */
	rec.capped = Boolean(is_cap);
	rec.solved = Boolean(!is_cap && grid && demo_is_latin(grid)
		&& demo_check_all(grid, rec.clues));
	rec.grid = grid ? demo_clone_grid(grid) : null;
	rec.steps.push({
		op: is_cap ? "cap" : (rec.solved ? "done" : "error"),
		grid: rec.grid,
		text: text
	});
	return rec;
}

/* ---- PARSE generators (6) ------------------------------------------------ */

function demo_parse_fixed(puzzle)
{
	const rec = demo_make_rec("parse", puzzle);
	const s = puzzle.argv;
	const clues = [];

	/* 1. length check */
	demo_push(rec, {op: "check", pos: 0, clues: [],
		text: `check strlen(argv[1]) == ${s.length} (expected 31)`});
	/* 2. step by +2: even = digit, odd = space */
	for (let i = 0; i < s.length; i += 2)
	{
		const ch = s[i];
		const v = Number(ch);

		clues.push(v);
		demo_push(rec, {op: "store", pos: i, clues: clues.slice(),
			text: `str[${i}] = '${ch}' (even) → clues[${clues.length - 1}] = ${v}`});
		if (i + 1 < s.length)
		{
			demo_push(rec, {op: "skip", pos: i + 1, clues: clues.slice(),
				text: `str[${i + 1}] = '${s[i + 1]}' (odd) → must be ' '`});
		}
	}
	demo_push(rec, {op: "done", pos: s.length, clues: clues.slice(),
		text: `done: ${clues.length} clues read at fixed even indexes`});
	return rec;
}

function demo_parse_scan(puzzle)
{
	const rec = demo_make_rec("parse", puzzle);
	const s = puzzle.argv;
	const clues = [];

	/* 1. single left-to-right scan */
	for (let i = 0; i < s.length; i++)
	{
		const ch = s[i];

		if (ch >= "1" && ch <= "4")
		{
			clues.push(Number(ch));
			demo_push(rec, {op: "store", pos: i, clues: clues.slice(),
				text: `str[${i}] = '${ch}' in '1'..'4' → clues[${clues.length - 1}] = ${ch}`});
		}
		else if (ch === " ")
		{
			demo_push(rec, {op: "skip", pos: i, clues: clues.slice(),
				text: `str[${i}] = ' ' → skip space`});
		}
	}
	/* 2. final count check */
	demo_push(rec, {op: "done", pos: s.length, clues: clues.slice(),
		text: `end of string: count == ${clues.length} (expected 16)`});
	return rec;
}

function demo_parse_split(puzzle)
{
	const rec = demo_make_rec("parse", puzzle);
	const s = puzzle.argv;
	const words = s.split(" ");
	const clues = [];

	/* 1. split on spaces into malloc'd words */
	demo_push(rec, {op: "check", pos: 0, clues: [], words: words.slice(),
		word_idx: -1, text: `ft_split(argv[1], ' ') → ${words.length} malloc'd words`});
	/* 2. validate each word is len 1 and in '1'..'4' */
	for (let i = 0; i < words.length; i++)
	{
		const w = words[i];
		clues.push(Number(w));
		demo_push(rec, {op: "store", pos: i * 2, clues: clues.slice(),
			words: words.slice(), word_idx: i,
			text: `words[${i}] = "${w}" (len 1, '1'..'4') → clues[${i}] = ${w}`});
	}
	/* 3. free the words array */
	demo_push(rec, {op: "done", pos: s.length, clues: clues.slice(),
		words: words.slice(), word_idx: -1,
		text: `free_split(words): ${clues.length} clues kept`});
	return rec;
}

function demo_parse_atoi(puzzle)
{
	const rec = demo_make_rec("parse", puzzle);
	const s = puzzle.argv;
	const clues = [];

	/* 1. accumulate res = res * 10 + (c - '0') per token */
	let i = 0;
	while (i < s.length)
	{
		if (s[i] === " ")
		{
			demo_push(rec, {op: "skip", pos: i, clues: clues.slice(),
				text: `str[${i}] = ' ' → advance to next token`});
			i++;
			continue;
		}
		let res = 0;
		const start = i;
		while (i < s.length && s[i] >= "0" && s[i] <= "9")
		{
			res = res * 10 + (s.charCodeAt(i) - 48);
			i++;
		}
		clues.push(res);
		demo_push(rec, {op: "store", pos: start, clues: clues.slice(),
			text: `ft_atoi("${s.slice(start, i)}") = ${res} → check 1..4 → clues[${clues.length - 1}]`});
	}
	demo_push(rec, {op: "done", pos: s.length, clues: clues.slice(),
		text: `done: ${clues.length} numbers via atoi (watch out: atoi often accepts "04")`});
	return rec;
}

function demo_parse_fsm(puzzle)
{
	const rec = demo_make_rec("parse", puzzle);
	const s = puzzle.argv;
	const clues = [];
	let state = "EXPECT_DIGIT";

	/* 1. explicit state flips between EXPECT_DIGIT and EXPECT_SPACE */
	for (let i = 0; i < s.length; i++)
	{
		const ch = s[i];

		if (state === "EXPECT_DIGIT")
		{
			clues.push(Number(ch));
			state = "EXPECT_SPACE";
			demo_push(rec, {op: "store", pos: i, clues: clues.slice(),
				state: state,
				text: `state EXPECT_DIGIT: '${ch}' ok → clues[${clues.length - 1}], next: EXPECT_SPACE`});
		}
		else
		{
			state = "EXPECT_DIGIT";
			demo_push(rec, {op: "skip", pos: i, clues: clues.slice(),
				state: state,
				text: `state EXPECT_SPACE: '${ch}' ok → next: EXPECT_DIGIT`});
		}
	}
	demo_push(rec, {op: "done", pos: s.length, clues: clues.slice(),
		state: state,
		text: `ended in ${state} with ${clues.length} clues (valid end state)`});
	return rec;
}

function demo_parse_none(puzzle)
{
	const rec = demo_make_rec("parse", puzzle);
	const sample = "4 3 2 a 1";
	const clues = [];

	/* 1. show what happens on malformed input when nothing is checked */
	rec.argv = sample;
	demo_push(rec, {op: "check", pos: 0, clues: [],
		text: `no validation: reads "${sample}" without checking length or chars`});
	for (let i = 0; i < sample.length; i++)
	{
		const ch = sample[i];

		if (ch === " ")
		{
			demo_push(rec, {op: "skip", pos: i, clues: clues.slice(),
				text: `str[${i}] = ' ' → skip`});
		}
		else
		{
			const v = ch.charCodeAt(0) - 48;
			clues.push(v);
			demo_push(rec, {op: ch >= "1" && ch <= "4" ? "store" : "reject",
				pos: i, clues: clues.slice(),
				text: `str[${i}] = '${ch}' → blindly stores '${ch}' - '0' = ${v}`});
		}
	}
	demo_push(rec, {op: "error", pos: sample.length, clues: clues.slice(),
		text: `bug: bad char 'a' became ${"a".charCodeAt(0) - 48} and only ${clues.length} clues were read`});
	return rec;
}

/* ---- DATA generators (8) ------------------------------------------------- */

function demo_data_grid2d(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);

	/* 1. fill a few cells showing [r][c] and [pos / 4][pos % 4] */
	for (let pos = 0; pos < 16; pos++)
	{
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		g[r][c] = sol[r][c];
		demo_push(rec, {op: "place", layout: "grid2d", grid: demo_clone_grid(g),
			focus: [r, c], formula: `pos=${pos} → grid[${pos}/4][${pos}%4] = grid[${r}][${c}] = ${sol[r][c]}`,
			text: `int grid[4][4]: stack 2D array, cell (${r}, ${c}) ← ${sol[r][c]}`});
	}
	demo_push(rec, {op: "done", layout: "grid2d", grid: demo_clone_grid(g),
		formula: "int grid[4][4] (64 bytes on stack) + int clues[16]",
		text: "2D stack array: simple, fixed at 4x4 (or 9x9), no malloc/free needed"});
	return rec;
}

function demo_data_padded(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);

	/* 1. place clues on the border first (row 0, row 5, col 0, col 5) */
	demo_push(rec, {op: "check", layout: "padded", grid: demo_clone_grid(g),
		border: true,
		formula: "board[0][1..4]=top · board[5][1..4]=bot · board[1..4][0]=left · board[1..4][5]=right",
		text: "int board[6][6]: clues sit on the outer ring, puzzle inside [1..4][1..4]"});
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
		{
			g[r][c] = sol[r][c];
			demo_push(rec, {op: "place", layout: "padded", grid: demo_clone_grid(g),
				border: true, focus: [r, c],
				formula: `board[${r + 1}][${c + 1}] = ${sol[r][c]} (border clue left: board[${r + 1}][0]=${puzzle.clues[8 + r]})`,
				text: `inner cell (${r + 1}, ${c + 1}) ← ${sol[r][c]}`});
		}
	}
	demo_push(rec, {op: "done", layout: "padded", grid: demo_clone_grid(g),
		border: true,
		formula: "one [N+2][N+2] array matches Appendix 2 & 3 of the PDF",
		text: "padded border board complete: clues and cells share one array"});
	return rec;
}

function demo_data_malloc2d(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);

	/* 1. allocate pointer spine, then each row */
	demo_push(rec, {op: "check", layout: "malloc2d", grid: demo_clone_grid(g),
		rows_alloc: 0,
		formula: "int **grid = malloc(sizeof(int *) * N)",
		text: "step 1: allocate N = 4 row pointers on the heap"});
	for (let r = 0; r < 4; r++)
	{
		demo_push(rec, {op: "check", layout: "malloc2d", grid: demo_clone_grid(g),
			rows_alloc: r + 1,
			formula: `grid[${r}] = malloc(sizeof(int) * N)`,
			text: `step 2: allocate row ${r} on the heap (4 ints)`});
	}
	/* 2. fill rows */
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
			g[r][c] = sol[r][c];
		demo_push(rec, {op: "place", layout: "malloc2d", grid: demo_clone_grid(g),
			rows_alloc: 4, focus: [r, 0],
			formula: `grid[${r}][0..3] = [${sol[r].join(", ")}]`,
			text: `fill heap row ${r}; remember to free(grid[r]) then free(grid) on every exit`});
	}
	demo_push(rec, {op: "done", layout: "malloc2d", grid: demo_clone_grid(g),
		rows_alloc: 4,
		formula: "5 malloc calls → 5 free calls (rows first, then spine)",
		text: "malloc'd int ** scales to any N up to 9x9, needs careful freeing"});
	return rec;
}

function demo_data_flat(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);

	/* 1. show 2D (r, c) mapping to 1D slot r * 4 + c */
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
		{
			const idx = r * 4 + c;
			g[r][c] = sol[r][c];
			demo_push(rec, {op: "place", layout: "flat", grid: demo_clone_grid(g),
				focus: [r, c], flat_idx: idx,
				formula: `(${r}, ${c}) → grid[${r} * 4 + ${c}] = grid[${idx}] = ${sol[r][c]}`,
				text: `1D array slot ${idx} holds row ${r}, col ${c}`});
		}
	}
	demo_push(rec, {op: "done", layout: "flat", grid: demo_clone_grid(g),
		flat_idx: -1,
		formula: "int grid[16] (or malloc(N * N * sizeof(int))) — one allocation",
		text: "flat 1D array: contiguous memory, one malloc/free"});
	return rec;
}

function demo_data_char(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);

	/* 1. store ASCII '1'..'4' directly */
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
		{
			const v = sol[r][c];
			g[r][c] = v;
			demo_push(rec, {op: "place", layout: "char", grid: demo_clone_grid(g),
				focus: [r, c],
				formula: `grid[${r}][${c}] = '${v}' (ASCII ${48 + v})`,
				text: `char grid holds '${v}' directly — compares as chars, prints with write(1, &grid[r][c], 1)`});
		}
	}
	demo_push(rec, {op: "done", layout: "char", grid: demo_clone_grid(g),
		formula: "char grid[4][4] — no + '0' conversion when printing",
		text: "char grid complete: empty cells hold '0' or 0"});
	return rec;
}

function demo_data_struct(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);

	/* 1. introduce the struct fields, then populate grid */
	demo_push(rec, {op: "check", layout: "struct", grid: demo_clone_grid(g),
		formula: "typedef struct s_board { int n; int grid[4][4]; int clues[16]; } t_board;",
		text: "one pointer t_board *b carries n, grid and clues (stays under 42's 4-param limit)"});
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
			g[r][c] = sol[r][c];
		demo_push(rec, {op: "place", layout: "struct", grid: demo_clone_grid(g),
			focus: [r, 0],
			formula: `b->n = 4 · b->grid[${r}][0..3] = [${sol[r].join(", ")}]`,
			text: `functions take (t_board *b, int pos) instead of 4 separate pointers`});
	}
	demo_push(rec, {op: "done", layout: "struct", grid: demo_clone_grid(g),
		formula: "t_board passed by pointer across parse, solve and print",
		text: "struct board keeps all state together"});
	return rec;
}

function demo_data_bits(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);
	const row_m = [0, 0, 0, 0];
	const col_m = [0, 0, 0, 0];

	/* 1. show row_used[r] and col_used[c] bitmasks updating on each placement */
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
		{
			const v = sol[r][c];
			const bit = 1 << v;
			g[r][c] = v;
			row_m[r] |= bit;
			col_m[c] |= bit;
			demo_push(rec, {op: "place", layout: "bits", grid: demo_clone_grid(g),
				focus: [r, c], row_masks: row_m.slice(), col_masks: col_m.slice(),
				formula: `bit = 1 << ${v} (${bit.toString(2).padStart(5, "0")}) · row_used[${r}] |= bit · col_used[${c}] |= bit`,
				text: `O(1) duplicate test: (row_used[${r}] | col_used[${c}]) & (1 << ${v})`});
		}
	}
	demo_push(rec, {op: "done", layout: "bits", grid: demo_clone_grid(g),
		row_masks: row_m.slice(), col_masks: col_m.slice(),
		formula: "all rows and cols reach 0b11110 (bits 1..4 all set)",
		text: "bitmask used-sets replace the duplicate-check loop"});
	return rec;
}

function demo_data_cand(puzzle)
{
	const rec = demo_make_rec("data", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	const g = demo_empty_grid(4);
	const cands = [];

	for (let r = 0; r < 4; r++)
		cands.push([0b11110, 0b11110, 0b11110, 0b11110]);
	/* 1. place cells and cross off values from the row and column */
	demo_push(rec, {op: "check", layout: "cand", grid: demo_clone_grid(g),
		cands: cands.map(function (row) { return row.slice(); }),
		formula: "each cell starts with candidates {1, 2, 3, 4}",
		text: "every empty cell stores which heights are still allowed"});
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
		{
			const v = sol[r][c];
			const bit = 1 << v;
			g[r][c] = v;
			cands[r][c] = bit;
			for (let i = 0; i < 4; i++)
			{
				if (i !== c)
					cands[r][i] &= ~bit;
				if (i !== r)
					cands[i][c] &= ~bit;
			}
			demo_push(rec, {op: "place", layout: "cand", grid: demo_clone_grid(g),
				focus: [r, c], cands: cands.map(function (row) { return row.slice(); }),
				formula: `place ${v} at (${r},${c}) → remove ${v} from row ${r} and col ${c}`,
				text: `candidates in row ${r} & col ${c} shrink immediately`});
		}
	}
	demo_push(rec, {op: "done", layout: "cand", grid: demo_clone_grid(g),
		cands: cands.map(function (row) { return row.slice(); }),
		formula: "every cell narrowed down to 1 candidate",
		text: "candidate sets let the solver skip impossible values and pick tight cells"});
	return rec;
}

/* ---- SOLVE generators (16, tiers 0..3) ----------------------------------- */

function demo_solve_hardcode(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const pdf_argv = DEMO_PUZZLES[0].argv;

	/* 1. compare argv[1] against a literal table */
	demo_push(rec, {op: "check", grid: demo_empty_grid(4),
		text: `ft_strcmp(argv[1], "${pdf_argv}")`});
	if (puzzle.argv === pdf_argv)
	{
		const g = demo_clone_grid(DEMO_PUZZLES[0].solution);
		demo_push(rec, {op: "place", grid: g,
			text: "matched hardcoded PDF string — prints the literal grid with no search"});
		return demo_finish(rec, g, "hardcoded match (fails on any puzzle not in the table)", false);
	}
	demo_push(rec, {op: "reject", grid: demo_empty_grid(4),
		text: "no match in the hardcoded table → prints Error even though a solution exists"});
	return demo_finish(rec, null, "no hardcoded match → prints Error (fails unseen puzzles)", false);
}

function demo_solve_brute16(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);
	const vals = new Array(16).fill(1);

	/* 1. count through 4^16 grids like a 16-digit base-4 odometer; cap cleanly */
	for (let step = 0; step < DEMO_BRUTE_TRY_CAP; step++)
	{
		for (let i = 0; i < 16; i++)
			g[Math.floor(i / 4)][i % 4] = vals[i];
		const ok = demo_is_latin(g) && demo_check_all(g, puzzle.clues);
		demo_push(rec, {
			op: ok ? "place" : "reject",
			grid: demo_clone_grid(g),
			focus: [3, 3],
			text: `grid #${step + 1} / 4,294,967,296: ${ok ? "matches!" : "duplicates / clues fail"}`
		});
		if (ok)
			return demo_finish(rec, g, `found on grid #${step + 1}`, false);
		let k = 15;
		while (k >= 0)
		{
			if (vals[k] < 4)
			{
				vals[k]++;
				break;
			}
			vals[k] = 1;
			k--;
		}
	}
	return demo_finish(rec, g,
		`capped at ${DEMO_BRUTE_TRY_CAP} steps (worst case: 4^16 = 4,294,967,296 grids — times out)`,
		true);
}

function demo_solve_brute_perm_loops(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const perms = demo_perms4();
	const g = demo_empty_grid(4);
	let tries = 0;

	/* 1. four nested loops over all 24 row orders, checking only when full */
	for (let a = 0; a < 24; a++)
	{
		g[0] = perms[a];
		for (let b = 0; b < 24; b++)
		{
			g[1] = perms[b];
			for (let c = 0; c < 24; c++)
			{
				g[2] = perms[c];
				for (let d = 0; d < 24; d++)
				{
					g[3] = perms[d];
					tries++;
					const ok = demo_is_latin(g) && demo_check_all(g, puzzle.clues);
					demo_push(rec, {
						op: ok ? "place" : "reject",
						grid: demo_clone_grid(g),
						focus: [3, 0],
						text: `combo #${tries} / 331,776 (rows ${a},${b},${c},${d}): `
							+ (ok ? "all columns and clues match!" : "column clash or clue mismatch")
					});
					if (ok)
						return demo_finish(rec, g, `solved after ${tries} full-grid checks`, false);
					if (tries >= DEMO_PERM_TRY_CAP)
					{
						return demo_finish(rec, g,
							`capped at ${DEMO_PERM_TRY_CAP} combos (worst case: 24^4 = 331,776 grids)`,
							true);
					}
				}
			}
		}
	}
	return demo_finish(rec, null, "no solution found", false);
}

function demo_solve_bt_end(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);
	let stopped = false;

	/* 1. recursive per cell, placing 1..4 without uniqueness checks until pos == 16 */
	function go(pos)
	{
		if (rec.total >= DEMO_BRUTE_TRY_CAP)
		{
			stopped = true;
			return false;
		}
		if (pos === 16)
		{
			const ok = demo_is_latin(g) && demo_check_all(g, puzzle.clues);
			demo_push(rec, {op: ok ? "place" : "reject", grid: demo_clone_grid(g),
				focus: [3, 3],
				text: ok ? "full grid checks out!" : "full grid fails Latin square / clues — backtrack"});
			return ok;
		}
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		for (let v = 1; v <= 4; v++)
		{
			g[r][c] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `pos ${pos} (${r},${c}) ← ${v} (no duplicate check yet)`});
			if (go(pos + 1))
				return true;
			if (stopped)
				return false;
			g[r][c] = 0;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `undo (${r},${c})`});
		}
		return false;
	}
	if (go(0))
		return demo_finish(rec, g, `solved in ${rec.total} steps`, false);
	return demo_finish(rec, g,
		`capped at ${DEMO_BRUTE_TRY_CAP} steps — checking only at pos == 16 still searches up to 4^16 grids`,
		true);
}

function demo_solve_bt_unique(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);

	/* 1. recursive per cell: check row/col uniqueness per placement, clues at pos == 16 */
	function go(pos)
	{
		if (pos === 16)
		{
			const ok = demo_check_all(g, puzzle.clues);
			demo_push(rec, {op: ok ? "place" : "reject", grid: demo_clone_grid(g),
				focus: [3, 3],
				text: ok ? "full Latin square matches all 16 clues!"
					: "valid Latin square, but clues fail — backtrack"});
			return ok;
		}
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		for (let v = 1; v <= 4; v++)
		{
			if (!demo_is_unique(g, r, c, v))
				continue;
			g[r][c] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `(${r},${c}) ← ${v} (unique in row & col)`});
			if (go(pos + 1))
				return true;
			g[r][c] = 0;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `backtrack (${r},${c})`});
		}
		return false;
	}
	go(0);
	return demo_finish(rec, g,
		`solved in ${rec.total} steps (${rec.stats.place} placements, ${rec.stats.reject} full-grid rejects)`,
		false);
}

function demo_solve_bt_clue_line(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);

	/* 1. check row clues as soon as col == 3, column clues as soon as row == 3 */
	function go(pos)
	{
		if (pos === 16)
			return true;
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		for (let v = 1; v <= 4; v++)
		{
			if (!demo_is_unique(g, r, c, v))
				continue;
			g[r][c] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `(${r},${c}) ← ${v}`});
			let ok = true;
			if (c === 3 && !demo_check_row(g, puzzle.clues, r))
			{
				ok = false;
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `row ${r} full: fails left/right clues (${puzzle.clues[8 + r]}, ${puzzle.clues[12 + r]}) → prune`});
			}
			else if (r === 3 && !demo_check_col(g, puzzle.clues, c))
			{
				ok = false;
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `col ${c} full: fails top/bottom clues (${puzzle.clues[c]}, ${puzzle.clues[4 + c]}) → prune`});
			}
			if (ok && go(pos + 1))
				return true;
			g[r][c] = 0;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `backtrack (${r},${c})`});
		}
		return false;
	}
	go(0);
	return demo_finish(rec, g,
		`solved in ${rec.total} steps (${rec.stats.prune} early line prunes)`,
		false);
}

function demo_solve_bt_iter(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);
	let pos = 0;

	/* 1. explicit position counter moving forward and stepping back on failure */
	while (pos >= 0 && pos < 16)
	{
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		let placed = false;

		for (let v = g[r][c] + 1; v <= 4; v++)
		{
			g[r][c] = 0;
			if (!demo_is_unique(g, r, c, v))
				continue;
			g[r][c] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `pos=${pos}: try ${v} at (${r},${c})`});
			if (c === 3 && !demo_check_row(g, puzzle.clues, r))
			{
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `pos=${pos}: row ${r} clues fail`});
				continue;
			}
			if (r === 3 && !demo_check_col(g, puzzle.clues, c))
			{
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `pos=${pos}: col ${c} clues fail`});
				continue;
			}
			placed = true;
			pos++;
			break;
		}
		if (!placed)
		{
			g[r][c] = 0;
			pos--;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `nothing fits (${r},${c}) → step back to pos=${pos}`});
		}
	}
	return demo_finish(rec, g,
		`solved iteratively in ${rec.total} steps (no recursion)`, false);
}

function demo_solve_row_perm(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const perms = demo_perms4();
	const row_opts = [0, 1, 2, 3].map(function (r)
	{
		return perms.filter(function (p)
		{
			return demo_check_line(p, puzzle.clues[8 + r], puzzle.clues[12 + r]);
		});
	});
	const g = demo_empty_grid(4);

	/* 1. filter 24 permutations per row first */
	demo_push(rec, {op: "check", grid: demo_clone_grid(g),
		text: `filtered 24 perms by row clues: [${row_opts.map(function (o) { return o.length; }).join(", ")}] choices per row`});
	/* 2. place one row at a time, rejecting column clashes immediately */
	function go(r)
	{
		if (r === 4)
		{
			for (let c = 0; c < 4; c++)
			{
				if (!demo_check_col(g, puzzle.clues, c))
				{
					demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [3, c],
						text: `col ${c} clues fail → reject row 3`});
					return false;
				}
			}
			return true;
		}
		for (const p of row_opts[r])
		{
			let clash = false;
			for (let c = 0; c < 4; c++)
			{
				for (let pr = 0; pr < r; pr++)
				{
					if (g[pr][c] === p[c])
						clash = true;
				}
			}
			if (clash)
			{
				demo_push(rec, {op: "reject", grid: demo_clone_grid(g), focus: [r, 0],
					text: `row ${r} [${p.join(" ")}] clashes with an earlier column`});
				continue;
			}
			g[r] = p.slice();
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, 0],
				text: `place row ${r} = [${p.join(" ")}]`});
			if (go(r + 1))
				return true;
			g[r] = [0, 0, 0, 0];
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, 0],
				text: `undo row ${r}`});
		}
		return false;
	}
	go(0);
	return demo_finish(rec, g,
		`solved by row permutations in ${rec.total} steps`, false);
}

function demo_apply_prefill(g, clues, rec)
{
	const fixed = demo_empty_grid(4);

	function put(r, c, v, why)
	{
		if (g[r][c] === v)
			return;
		g[r][c] = v;
		fixed[r][c] = 1;
		demo_push(rec, {op: "prefill", grid: demo_clone_grid(g), focus: [r, c],
			text: `prefill (${r},${c}) = ${v}: ${why}`});
	}
	for (let i = 0; i < 4; i++)
	{
		if (clues[i] === 1)
			put(0, i, 4, `top[${i}] == 1 forces 4 at top`);
		if (clues[i] === 4)
		{
			for (let r = 0; r < 4; r++)
				put(r, i, r + 1, `top[${i}] == 4 forces 1..4 down`);
		}
		if (clues[4 + i] === 1)
			put(3, i, 4, `bottom[${i}] == 1 forces 4 at bottom`);
		if (clues[4 + i] === 4)
		{
			for (let r = 0; r < 4; r++)
				put(3 - r, i, r + 1, `bottom[${i}] == 4 forces 1..4 up`);
		}
		if (clues[8 + i] === 1)
			put(i, 0, 4, `left[${i}] == 1 forces 4 at left`);
		if (clues[8 + i] === 4)
		{
			for (let c = 0; c < 4; c++)
				put(i, c, c + 1, `left[${i}] == 4 forces 1..4 right`);
		}
		if (clues[12 + i] === 1)
			put(i, 3, 4, `right[${i}] == 1 forces 4 at right`);
		if (clues[12 + i] === 4)
		{
			for (let c = 0; c < 4; c++)
				put(i, 3 - c, c + 1, `right[${i}] == 4 forces 1..4 left`);
		}
	}
	return fixed;
}

function demo_solve_prefill(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);

	/* 1. deterministic pre-fill from clues 1 and 4 */
	const fixed = demo_apply_prefill(g, puzzle.clues, rec);
	/* 2. fill the remaining cells with line-pruned backtracking */
	function go(pos)
	{
		if (pos === 16)
			return true;
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		if (fixed[r][c])
		{
			if (c === 3 && !demo_check_row(g, puzzle.clues, r))
				return false;
			if (r === 3 && !demo_check_col(g, puzzle.clues, c))
				return false;
			return go(pos + 1);
		}
		for (let v = 1; v <= 4; v++)
		{
			if (!demo_is_unique(g, r, c, v))
				continue;
			g[r][c] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `search (${r},${c}) ← ${v}`});
			let ok = true;
			if (c === 3 && !demo_check_row(g, puzzle.clues, r))
				ok = false;
			if (ok && r === 3 && !demo_check_col(g, puzzle.clues, c))
				ok = false;
			if (ok && go(pos + 1))
				return true;
			g[r][c] = 0;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `backtrack (${r},${c})`});
		}
		return false;
	}
	go(0);
	return demo_finish(rec, g,
		`solved with pre-fill + backtracking in ${rec.total} steps`, false);
}

function demo_solve_cands(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);

	/* 1. search over each cell's shrinking candidate set */
	function cell_cands(r, c)
	{
		const out = [];
		for (let v = 1; v <= 4; v++)
		{
			if (demo_is_unique(g, r, c, v))
				out.push(v);
		}
		return out;
	}
	function go(pos)
	{
		if (pos === 16)
			return true;
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		const opts = cell_cands(r, c);
		for (const v of opts)
		{
			g[r][c] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `(${r},${c}) candidates {${opts.join(",")}} → try ${v}`});
			let ok = true;
			if (c === 3 && !demo_check_row(g, puzzle.clues, r))
			{
				ok = false;
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `row ${r} clue mismatch → drop ${v}`});
			}
			else if (r === 3 && !demo_check_col(g, puzzle.clues, c))
			{
				ok = false;
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `col ${c} clue mismatch → drop ${v}`});
			}
			if (ok && go(pos + 1))
				return true;
			g[r][c] = 0;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `restore candidates around (${r},${c})`});
		}
		return false;
	}
	go(0);
	return demo_finish(rec, g, `solved with candidate lists in ${rec.total} steps`, false);
}

function demo_solve_bits(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);
	const row_m = [0, 0, 0, 0];
	const col_m = [0, 0, 0, 0];

	/* 1. bitmask used-sets: one bitwise OR/AND per candidate */
	function go(pos)
	{
		if (pos === 16)
			return true;
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		const used = row_m[r] | col_m[c];
		for (let v = 1; v <= 4; v++)
		{
			const bit = 1 << v;
			if (used & bit)
				continue;
			g[r][c] = v;
			row_m[r] |= bit;
			col_m[c] |= bit;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `(${r},${c}) ← ${v} (row_m[${r}]=${row_m[r].toString(2)}, col_m[${c}]=${col_m[c].toString(2)})`});
			let ok = true;
			if (c === 3 && !demo_check_row(g, puzzle.clues, r))
				ok = false;
			if (ok && r === 3 && !demo_check_col(g, puzzle.clues, c))
				ok = false;
			if (ok && go(pos + 1))
				return true;
			g[r][c] = 0;
			row_m[r] ^= bit;
			col_m[c] ^= bit;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `clear bit 1<<${v} at (${r},${c})`});
		}
		return false;
	}
	go(0);
	return demo_finish(rec, g, `solved with bitmasks in ${rec.total} steps`, false);
}

function demo_partial_ok(arr, filled, clue)
{
	let tallest = 0;
	let seen = 0;
	let taller_left = 0;

	for (let i = 0; i < filled; i++)
	{
		if (arr[i] > tallest)
		{
			tallest = arr[i];
			seen++;
		}
	}
	if (seen > clue)
		return false;
	taller_left = 4 - tallest;
	if (seen + taller_left < clue)
		return false;
	return true;
}

function demo_solve_partial_prune(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);

	/* 1. prune on partial lines: too many seen already, or can't reach clue */
	function go(pos)
	{
		if (pos === 16)
			return true;
		const r = Math.floor(pos / 4);
		const c = pos % 4;
		for (let v = 1; v <= 4; v++)
		{
			if (!demo_is_unique(g, r, c, v))
				continue;
			g[r][c] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, c],
				text: `(${r},${c}) ← ${v}`});
			let ok = demo_partial_ok(g[r], c + 1, puzzle.clues[8 + r]);
			if (!ok)
			{
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `partial row ${r} can't satisfy left clue ${puzzle.clues[8 + r]} → prune early`});
			}
			const col = [g[0][c], g[1][c], g[2][c], g[3][c]];
			if (ok && !demo_partial_ok(col, r + 1, puzzle.clues[c]))
			{
				ok = false;
				demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
					text: `partial col ${c} can't satisfy top clue ${puzzle.clues[c]} → prune early`});
			}
			if (ok && c === 3 && !demo_check_row(g, puzzle.clues, r))
				ok = false;
			if (ok && r === 3 && !demo_check_col(g, puzzle.clues, c))
				ok = false;
			if (ok && go(pos + 1))
				return true;
			g[r][c] = 0;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [r, c],
				text: `backtrack (${r},${c})`});
		}
		return false;
	}
	go(0);
	return demo_finish(rec, g,
		`solved with partial-line pruning in ${rec.total} steps (${rec.stats.prune} prunes)`,
		false);
}

function demo_line_mask_filter(g, clues, r, c)
{
	const opts = [];

	for (let v = 1; v <= 4; v++)
	{
		if (!demo_is_unique(g, r, c, v))
			continue;
		g[r][c] = v;
		const row_full = g[r].every(function (x) { return x > 0; });
		const col = [g[0][c], g[1][c], g[2][c], g[3][c]];
		const col_full = col.every(function (x) { return x > 0; });
		let ok = true;
		if (row_full && !demo_check_row(g, clues, r))
			ok = false;
		if (ok && col_full && !demo_check_col(g, clues, c))
			ok = false;
		g[r][c] = 0;
		if (ok)
			opts.push(v);
	}
	return opts;
}

function demo_solve_mrv(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const g = demo_empty_grid(4);

	/* 1. always pick the empty cell with the fewest legal candidates */
	function go(left)
	{
		if (left === 0)
			return demo_check_all(g, puzzle.clues);
		let best = null;
		let best_opts = null;
		for (let r = 0; r < 4; r++)
		{
			for (let c = 0; c < 4; c++)
			{
				if (g[r][c] !== 0)
					continue;
				const opts = demo_line_mask_filter(g, puzzle.clues, r, c);
				if (opts.length === 0)
				{
					demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [r, c],
						text: `MRV dead end: (${r},${c}) has 0 candidates`});
					return false;
				}
				if (!best_opts || opts.length < best_opts.length)
				{
					best = [r, c];
					best_opts = opts;
				}
			}
		}
		for (const v of best_opts)
		{
			g[best[0]][best[1]] = v;
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: best,
				text: `MRV picks (${best[0]},${best[1]}) [${best_opts.length} choice(s): ${best_opts.join(",")}] → ${v}`});
			if (go(left - 1))
				return true;
			g[best[0]][best[1]] = 0;
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: best,
				text: `undo (${best[0]},${best[1]})`});
		}
		return false;
	}
	demo_apply_prefill(g, puzzle.clues, rec);
	let rem = 0;
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
		{
			if (g[r][c] === 0)
				rem++;
		}
	}
	go(rem);
	return demo_finish(rec, g, `solved with MRV in ${rec.total} steps`, false);
}

function demo_line_candidates(g, clues, perms)
{
	/* Intersect permutations compatible with current grid for every row & col. */
	const cell_bits = [];

	for (let r = 0; r < 4; r++)
		cell_bits.push([0b11110, 0b11110, 0b11110, 0b11110]);
	for (let r = 0; r < 4; r++)
	{
		const row_bits = [0, 0, 0, 0];
		for (const p of perms)
		{
			if (!demo_check_line(p, clues[8 + r], clues[12 + r]))
				continue;
			let ok = true;
			for (let c = 0; c < 4; c++)
			{
				if (g[r][c] && g[r][c] !== p[c])
					ok = false;
			}
			if (!ok)
				continue;
			for (let c = 0; c < 4; c++)
				row_bits[c] |= (1 << p[c]);
		}
		for (let c = 0; c < 4; c++)
			cell_bits[r][c] &= row_bits[c];
	}
	for (let c = 0; c < 4; c++)
	{
		const col_bits = [0, 0, 0, 0];
		for (const p of perms)
		{
			if (!demo_check_line(p, clues[c], clues[4 + c]))
				continue;
			let ok = true;
			for (let r = 0; r < 4; r++)
			{
				if (g[r][c] && g[r][c] !== p[r])
					ok = false;
			}
			if (!ok)
				continue;
			for (let r = 0; r < 4; r++)
				col_bits[r] |= (1 << p[r]);
		}
		for (let r = 0; r < 4; r++)
			cell_bits[r][c] &= col_bits[r];
	}
	return cell_bits;
}

function demo_bits_to_vals(mask)
{
	const out = [];

	for (let v = 1; v <= 4; v++)
	{
		if (mask & (1 << v))
			out.push(v);
	}
	return out;
}

function demo_solve_propagate(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const perms = demo_perms4();

	/* 1. repeat forced singletons until fixed point, then branch on smallest */
	function go(g)
	{
		for (;;)
		{
			const bits = demo_line_candidates(g, puzzle.clues, perms);
			let changed = false;
			let best = null;
			let best_vals = null;

			for (let r = 0; r < 4; r++)
			{
				for (let c = 0; c < 4; c++)
				{
					const vals = demo_bits_to_vals(bits[r][c]);
					if (vals.length === 0)
						return null;
					if (g[r][c] === 0 && vals.length === 1)
					{
						g[r][c] = vals[0];
						changed = true;
						demo_push(rec, {op: "prefill", grid: demo_clone_grid(g),
							focus: [r, c],
							text: `propagate single: (${r},${c}) can only be ${vals[0]}`});
					}
					else if (g[r][c] === 0 && (!best_vals || vals.length < best_vals.length))
					{
						best = [r, c];
						best_vals = vals;
					}
				}
			}
			if (changed)
				continue;
			if (!best)
				return demo_check_all(g, puzzle.clues) ? g : null;
			for (const v of best_vals)
			{
				const next = demo_clone_grid(g);
				next[best[0]][best[1]] = v;
				demo_push(rec, {op: "place", grid: demo_clone_grid(next), focus: best,
					text: `branch (${best[0]},${best[1]}) ← ${v} (from {${best_vals.join(",")}})`});
				const sol = go(next);
				if (sol)
					return sol;
				demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: best,
					text: `contradiction after (${best[0]},${best[1]}) = ${v}`});
			}
			return null;
		}
	}
	const sol = go(demo_empty_grid(4));
	return demo_finish(rec, sol,
		`solved with constraint propagation in ${rec.total} steps`, false);
}

function demo_solve_line_solver(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const perms = demo_perms4();
	const row_sets = [0, 1, 2, 3].map(function (r)
	{
		return perms.filter(function (p)
		{
			return demo_check_line(p, puzzle.clues[8 + r], puzzle.clues[12 + r]);
		});
	});
	const col_sets = [0, 1, 2, 3].map(function (c)
	{
		return perms.filter(function (p)
		{
			return demo_check_line(p, puzzle.clues[c], puzzle.clues[4 + c]);
		});
	});
	const g = demo_empty_grid(4);

	/* 1. show line counts, then intersect row sets with column sets */
	demo_push(rec, {op: "check", grid: demo_clone_grid(g),
		text: `valid perms per row: [${row_sets.map(function (s) { return s.length; }).join(", ")}]; per col: [${col_sets.map(function (s) { return s.length; }).join(", ")}]`});
	/* 2. iteratively prune row/col sets by intersecting cell values */
	let rsets = row_sets.map(function (s) { return s.slice(); });
	let csets = col_sets.map(function (s) { return s.slice(); });
	for (let round = 1; round <= 6; round++)
	{
		let shrunk = false;
		const cell_mask = [];
		for (let r = 0; r < 4; r++)
		{
			cell_mask.push([0, 0, 0, 0]);
			for (const p of rsets[r])
			{
				for (let c = 0; c < 4; c++)
					cell_mask[r][c] |= (1 << p[c]);
			}
		}
		for (let c = 0; c < 4; c++)
		{
			const before = csets[c].length;
			csets[c] = csets[c].filter(function (p)
			{
				return [0, 1, 2, 3].every(function (r)
				{
					return (cell_mask[r][c] & (1 << p[r])) !== 0;
				});
			});
			if (csets[c].length < before)
				shrunk = true;
		}
		const col_mask = [];
		for (let r = 0; r < 4; r++)
			col_mask.push([0, 0, 0, 0]);
		for (let c = 0; c < 4; c++)
		{
			for (const p of csets[c])
			{
				for (let r = 0; r < 4; r++)
					col_mask[r][c] |= (1 << p[r]);
			}
		}
		for (let r = 0; r < 4; r++)
		{
			const before = rsets[r].length;
			rsets[r] = rsets[r].filter(function (p)
			{
				return [0, 1, 2, 3].every(function (c)
				{
					return (col_mask[r][c] & (1 << p[c])) !== 0;
				});
			});
			if (rsets[r].length < before)
				shrunk = true;
		}
		for (let r = 0; r < 4; r++)
		{
			for (let c = 0; c < 4; c++)
			{
				const vals = demo_bits_to_vals(cell_mask[r][c] & col_mask[r][c]);
				if (vals.length === 1)
					g[r][c] = vals[0];
			}
		}
		demo_push(rec, {op: "prefill", grid: demo_clone_grid(g),
			text: `intersect round ${round}: rows [${rsets.map(function (s) { return s.length; }).join(",")}], cols [${csets.map(function (s) { return s.length; }).join(",")}]`});
		if (!shrunk)
			break;
	}
	/* 3. pick remaining rows from the tiny pruned sets */
	function pick_row(r)
	{
		if (r === 4)
			return demo_check_all(g, puzzle.clues);
		for (const p of rsets[r])
		{
			g[r] = p.slice();
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [r, 0],
				text: `commit row ${r} = [${p.join(" ")}]`});
			if (pick_row(r + 1))
				return true;
		}
		return false;
	}
	if (!demo_is_latin(g) || !demo_check_all(g, puzzle.clues))
		pick_row(0);
	return demo_finish(rec, g, `solved by line intersection in ${rec.total} steps`, false);
}

function demo_solve_dlx(puzzle)
{
	const rec = demo_make_rec("solve", puzzle);
	const perms = demo_perms4();
	const rows = [];

	/* 1. exact-cover matrix: 1 row per valid (r, perm), covering 4 row slots +
	      16 (col, val) constraints (Latin square + row clues) */
	for (let r = 0; r < 4; r++)
	{
		for (const p of perms)
		{
			if (!demo_check_line(p, puzzle.clues[8 + r], puzzle.clues[12 + r]))
				continue;
			const cols = [r];
			for (let c = 0; c < 4; c++)
				cols.push(4 + c * 4 + (p[c] - 1));
			rows.push({r: r, p: p, cols: cols});
		}
	}
	demo_push(rec, {op: "check", grid: demo_empty_grid(4),
		text: `exact-cover matrix: ${rows.length} row-options covering 20 constraints (4 rows + 16 col-values)`});
	/* 2. Algorithm X: pick constraint column with fewest covering rows */
	const covered = new Array(20).fill(false);
	const g = demo_empty_grid(4);

	function search(depth)
	{
		if (depth === 4)
		{
			for (let c = 0; c < 4; c++)
			{
				if (!demo_check_col(g, puzzle.clues, c))
				{
					demo_push(rec, {op: "prune", grid: demo_clone_grid(g), focus: [3, c],
						text: `exact cover fails col ${c} clue → uncover`});
					return false;
				}
			}
			return true;
		}
		let best_col = -1;
		let best_rows = null;
		for (let col = 0; col < 20; col++)
		{
			if (covered[col])
				continue;
			const opts = rows.filter(function (row)
			{
				return row.cols.indexOf(col) >= 0 && row.cols.every(function (k)
				{
					return !covered[k];
				});
			});
			if (opts.length === 0)
				return false;
			if (!best_rows || opts.length < best_rows.length)
			{
				best_col = col;
				best_rows = opts;
			}
		}
		for (const row of best_rows)
		{
			for (const k of row.cols)
				covered[k] = true;
			g[row.r] = row.p.slice();
			demo_push(rec, {op: "place", grid: demo_clone_grid(g), focus: [row.r, 0],
				text: `cover col #${best_col} (${best_rows.length} opt) → row ${row.r} = [${row.p.join(" ")}]`});
			if (search(depth + 1))
				return true;
			for (const k of row.cols)
				covered[k] = false;
			g[row.r] = [0, 0, 0, 0];
			demo_push(rec, {op: "backtrack", grid: demo_clone_grid(g), focus: [row.r, 0],
				text: `uncover row ${row.r}`});
		}
		return false;
	}
	search(0);
	return demo_finish(rec, g, `solved with Algorithm X / DLX in ${rec.total} steps`, false);
}

/* ---- PRINT generators (4) ------------------------------------------------ */

function demo_print_char(puzzle)
{
	const rec = demo_make_rec("print", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	let out = "";
	let writes = 0;

	/* 1. one write(1, &c, 1) per digit, space or newline */
	for (let r = 0; r < 4; r++)
	{
		for (let c = 0; c < 4; c++)
		{
			const ch = String(sol[r][c]);
			out += ch;
			writes++;
			demo_push(rec, {op: "emit", out: out, buf: ch, writes: writes,
				text: `write(1, "${ch}", 1)  (write #${writes})`});
			const sep = c < 3 ? " " : "\n";
			out += sep;
			writes++;
			demo_push(rec, {op: "emit", out: out, buf: sep, writes: writes,
				text: `write(1, "${sep === "\n" ? "\\n" : " "}", 1)  (write #${writes})`});
		}
	}
	rec.stats.writes = writes;
	demo_push(rec, {op: "done", out: out, buf: "", writes: writes,
		text: `done: ${writes} write() syscalls (1 byte each)`});
	return rec;
}

function demo_print_line(puzzle)
{
	const rec = demo_make_rec("print", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	let out = "";
	let writes = 0;

	/* 1. fill a 8-byte line buffer, flush once per row */
	for (let r = 0; r < 4; r++)
	{
		let line = "";
		for (let c = 0; c < 4; c++)
			line += String(sol[r][c]) + (c < 3 ? " " : "\n");
		demo_push(rec, {op: "buffer", out: out, buf: line, writes: writes,
			text: `fill char line[8] = "${line.replace("\n", "\\n")}"`});
		out += line;
		writes++;
		demo_push(rec, {op: "flush", out: out, buf: "", writes: writes,
			text: `write(1, line, 8) → flush row ${r} (write #${writes})`});
	}
	rec.stats.writes = writes;
	demo_push(rec, {op: "done", out: out, buf: "", writes: writes,
		text: `done: ${writes} write() syscalls (1 per row)`});
	return rec;
}

function demo_print_board(puzzle)
{
	const rec = demo_make_rec("print", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	let buf = "";

	/* 1. fill one 32-byte buffer for all 4 rows, flush once */
	for (let r = 0; r < 4; r++)
	{
		buf += sol[r].join(" ") + "\n";
		demo_push(rec, {op: "buffer", out: "", buf: buf, writes: 0,
			text: `append row ${r} into char buf[32] (${buf.length} bytes ready)`});
	}
	rec.stats.writes = 1;
	demo_push(rec, {op: "flush", out: buf, buf: "", writes: 1,
		text: `write(1, buf, ${buf.length}) → whole board in 1 syscall!`});
	demo_push(rec, {op: "done", out: buf, buf: "", writes: 1,
		text: "done: 1 write() syscall total"});
	return rec;
}

function demo_print_putstr(puzzle)
{
	const rec = demo_make_rec("print", puzzle);
	const sol = demo_solve_exact(puzzle.clues);
	let buf = "";

	/* 1. build a NUL-terminated string, then hand to ft_putstr */
	for (let r = 0; r < 4; r++)
	{
		buf += sol[r].join(" ") + "\n";
		demo_push(rec, {op: "buffer", out: "", buf: buf + "\\0", writes: 0,
			text: `build string: added row ${r} (${buf.length} chars + '\\0')`});
	}
	rec.stats.writes = 1;
	demo_push(rec, {op: "flush", out: buf, buf: "", writes: 1,
		text: `ft_putstr(str): scans to '\\0' (len ${buf.length}) and writes it out`});
	demo_push(rec, {op: "done", out: buf, buf: "", writes: 1,
		text: "done: string written via ft_putstr"});
	return rec;
}

/* ---- registry: one generator per catalog demo id ------------------------- */

const DEMO_GENERATORS = {
	parse_fixed: demo_parse_fixed,
	parse_scan: demo_parse_scan,
	parse_split: demo_parse_split,
	parse_atoi: demo_parse_atoi,
	parse_fsm: demo_parse_fsm,
	parse_none: demo_parse_none,
	data_grid2d: demo_data_grid2d,
	data_padded: demo_data_padded,
	data_malloc2d: demo_data_malloc2d,
	data_flat: demo_data_flat,
	data_char: demo_data_char,
	data_struct: demo_data_struct,
	data_bits: demo_data_bits,
	data_cand: demo_data_cand,
	solve_hardcode: demo_solve_hardcode,
	solve_brute16: demo_solve_brute16,
	solve_brute_perm_loops: demo_solve_brute_perm_loops,
	solve_bt_end: demo_solve_bt_end,
	solve_bt_unique: demo_solve_bt_unique,
	solve_bt_clue_line: demo_solve_bt_clue_line,
	solve_bt_iter: demo_solve_bt_iter,
	solve_row_perm: demo_solve_row_perm,
	solve_prefill: demo_solve_prefill,
	solve_cands: demo_solve_cands,
	solve_bits: demo_solve_bits,
	solve_partial_prune: demo_solve_partial_prune,
	solve_mrv: demo_solve_mrv,
	solve_propagate: demo_solve_propagate,
	solve_line_solver: demo_solve_line_solver,
	solve_dlx: demo_solve_dlx,
	print_char: demo_print_char,
	print_line: demo_print_line,
	print_board: demo_print_board,
	print_putstr: demo_print_putstr
};

function demo_run(demo_id, puzzle_id)
{
	const key = String(demo_id || "").replace(".", "_");
	const fn = DEMO_GENERATORS[key];
	let puzzle = DEMO_PUZZLES[0];

	if (!fn)
		return null;
	if (puzzle_id)
	{
		const found = DEMO_PUZZLES.find(function (p)
		{
			return p.id === puzzle_id;
		});
		if (found)
			puzzle = found;
	}
	return fn(puzzle);
}

if (typeof module === "object" && module.exports)
{
	module.exports = {
		DEMO_PUZZLES: DEMO_PUZZLES,
		DEMO_GENERATORS: DEMO_GENERATORS,
		demo_run: demo_run,
		demo_solve_exact: demo_solve_exact
	};
}
