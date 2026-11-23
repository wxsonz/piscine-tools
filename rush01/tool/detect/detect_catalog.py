"""The catalog of approaches (PLAN.md §7.3): every id with its name, a plain
2-3 line explanation, 1-3 defense questions and a demo id. Text only; the
rules that recognise each id live in detect_rules.py.
"""

# (id, tier, name, explain, questions); part is the id's prefix
ENTRIES = [
    # parse
    ("parse.fixed", None, "Fixed positions",
     "Reads the input at fixed places: digits at even indexes, spaces at "
     "odd ones, and the length must be 31 (16 digits + 15 spaces).",
     ["Why is the length 31, and how would it change for a 5x5?",
      "What does your program do with two spaces in a row?",
      "Which index holds the left clue of row 3?"]),
    ("parse.scan", None, "Scan and count",
     "Walks the string once: a digit is stored and counted, a space is "
     "skipped, anything else is an error. At the end the count must be 16.",
     ["What happens with \"12\" (two digits stuck together)?",
      "Where do you reject a leading or trailing space?",
      "How do you know there were exactly 16 numbers?"]),
    ("parse.split", None, "Split into words",
     "Cuts the string into words at the spaces (an ft_split with malloc), "
     "then checks each word is one char long and a digit in range.",
     ["Who frees the words, and when?",
      "What does your split do with two spaces in a row?",
      "Why malloc here instead of reading the string in place?"]),
    ("parse.atoi", None, "atoi per token",
     "Builds each number digit by digit (res = res * 10 + c - '0'), then "
     "checks its range. It often accepts \"04\" as 4.",
     ["Does your program accept \"04\"? Should it?",
      "What happens with a number like 12?",
      "Why an atoi when every clue is a single digit?"]),
    ("parse.fsm", None, "State machine",
     "A state variable says what is expected next (a digit or a space); each "
     "char moves the state or makes it an error.",
     ["Name your states and what moves from one to the other.",
      "Which state must the string end in?"]),
    ("parse.none", None, "No real validation",
     "Copies the digits into the clues but never rejects bad input: wrong "
     "chars, wrong length or wrong count go through (the fmt runs show it).",
     ["What does your program print for \"4 3 2\"?",
      "What should happen with \"1 2 3 a ...\"?",
      "Where would you add the check?"]),
    # data
    ("data.grid2d", None, "2D array",
     "The grid is an int array [4][4] (or [9][9]), read and written as "
     "[row][col], sometimes from a cell number as [pos / n][pos % n].",
     ["How do you go from cell number pos to its row and column?",
      "Why a fixed size, and what changes for the bonus?"]),
    ("data.padded", None, "Board with a clue border",
     "A [6][6] board (n + 2): the clues sit in row 0, row n+1, col 0 and "
     "col n+1, the puzzle in [1..n][1..n], like the drawing in the subject.",
     ["Which cell holds the clue for the top of column 2?",
      "Why put the clues in the same array as the grid?"]),
    ("data.malloc2d", None, "malloc'd int **",
     "The grid is malloc'd: first N row pointers, then one malloc per row.",
     ["Where do you free each row, and on the Error path too?",
      "What happens if one of the mallocs fails?"]),
    ("data.flat", None, "Flat 1D array",
     "The grid is one array of 16 ints (or N * N), indexed [r * n + c] or "
     "directly by the cell number.",
     ["Which index is row 2, column 3?",
      "Why one array instead of a 2D one?"]),
    ("data.char", None, "char grid",
     "The grid holds the chars '1'..'4' instead of numbers, so it can be "
     "printed without converting.",
     ["How do you compare heights when the cells are chars?",
      "What does an empty cell hold?"]),
    ("data.struct", None, "Struct board",
     "A typedef struct (often in a .h) carries the size, the grid and the "
     "clues together, passed around as one pointer.",
     ["Why a struct, and what is in it?",
      "Who allocates the struct, and who frees it?"]),
    ("data.bits", None, "Bitmask used-sets",
     "Each row and column keeps its used values as bits (row_used[r] with "
     "1 << v), so a duplicate test is one AND.",
     ["What does row_used[r] & (1 << v) mean?",
      "Where do you clear the bit again when backtracking?"]),
    ("data.cand", None, "Candidates per cell",
     "Each cell keeps the list (or bit mask) of the values still possible, "
     "crossed out as the neighbours get placed.",
     ["When a value is placed, which candidates do you remove?",
      "How do you put them back when you backtrack?"]),
    # solve
    ("solve.hardcode", 0, "Hardcoded answers",
     "Compares the input with fixed puzzle strings, or prints a grid written "
     "in the code. There is no search.",
     ["What does your program print for a puzzle that is not in your list?",
      "How would you solve a puzzle you have never seen?"]),
    ("solve.brute16", 0, "Every combination of all cells",
     "Fills all 16 cells with every combination (4^16 = 4 billion) and "
     "checks each full grid at the end.",
     ["How many grids does your program try in the worst case?",
      "How long does that take, and why?"]),
    ("solve.brute_perm_loops", 0, "Every combination of row orders",
     "Picks one of the 24 orders of 1..4 for each row with nested loops "
     "(24^4 grids) and checks the whole grid only at the end.",
     ["How many grids do your loops try?",
      "Could you stop earlier when two rows clash in a column?"]),
    ("solve.bt_end", 1, "Backtracking, check at the end",
     "Recursion fills cell after cell with 1..4 and only checks the rows, "
     "columns and clues once the grid is full.",
     ["When does your program find out a choice was wrong?",
      "How many grids can it build before the first check?"]),
    ("solve.bt_unique", 1, "Backtracking + row/col check per placement",
     "Recursion tries 1..4 in each cell, checks the row and column for that "
     "value before placing it, and checks the clues when the grid is full.",
     ["What happens when no value fits a cell?",
      "Why check the row and column before the clues?",
      "Where do you undo a placement?"]),
    ("solve.bt_clue_line", 1, "Backtracking + clue check when a line is full",
     "Like the row/col check, but a row's (or column's) clues are checked as "
     "soon as that line is full, so wrong branches die earlier.",
     ["When exactly do you check the clues of a row?",
      "Why not check the clues of a half-filled line?",
      "What changes in speed compared to checking at the end?"]),
    ("solve.bt_iter", 1, "Iterative backtracking",
     "No recursion: a position counter moves forward when a value fits and "
     "steps back to the previous cell when nothing fits.",
     ["How does your loop know it must go back?",
      "What does a cell hold when you step back past it?"]),
    ("solve.row_perm", 2, "Row permutations",
     "Each row is one of the 24 orders of 1..4 (a table or generated); rows "
     "are placed one by one and the columns are checked as they grow.",
     ["Where do the 24 orders come from?",
      "Which checks happen after each row?"]),
    ("solve.prefill", 2, "Pre-fill rules, then search",
     "Before searching, fills what the clues force: a 4 means 1..4 in order, "
     "a 1 puts the 4 next to it, two clues summing to 5 fix where the 4 is. "
     "Then a search fills the rest.",
     ["Which rules do you apply before the search, and why are they true?",
      "What does the search do with the pre-filled cells?"]),
    ("solve.cands", 2, "Candidate lists",
     "Each cell keeps the values still possible; placing a value removes it "
     "from the row and column, and the search only tries what is left.",
     ["How do you restore the candidates when you backtrack?",
      "Which cell do you fill first?"]),
    ("solve.bits", 3, "Bitmask used-sets in the search",
     "The search tests and sets bits (1 << v) per row and column instead of "
     "scanning the line for duplicates.",
     ["Show the line that tests if v is used in the row."]),
    ("solve.partial_prune", 3, "Clue check on partial lines",
     "Clues are checked on every placement, with the line still partly "
     "empty: too many visible buildings already means stop.",
     ["How do you check a clue when the line is not full yet?",
      "Can a partial check ever reject a correct grid?"]),
    ("solve.mrv", 3, "Most constrained cell first",
     "Picks the empty cell with the fewest possible values next, instead of "
     "going in reading order.",
     ["How do you find the cell with the fewest values?"]),
    ("solve.propagate", 3, "Constraint propagation",
     "After each placement, repeats simple deductions (single candidates, "
     "clue rules) until nothing changes, then searches.",
     ["Which deductions do you repeat, and when do you stop?"]),
    ("solve.line_solver", 3, "Line solver",
     "Works on whole lines: for each row or column, keeps only the orders "
     "that fit its two clues and the cells already set.",
     ["How many orders fit a line with clues 2 and 2?"]),
    ("solve.dlx", 3, "Exact cover (dancing links)",
     "Turns the puzzle into an exact cover problem and solves it with "
     "Knuth's Algorithm X / dancing links.",
     ["What are the rows and columns of your cover matrix?"]),
    # print
    ("print.char", None, "One write per char",
     "Writes each digit and space with write(1, &c, 1), turning a value into "
     "its char with v + '0', often through ft_putchar / ft_putnbr.",
     ["How many write calls does printing one grid make?",
      "How do you avoid a space at the end of a line?"]),
    ("print.line", None, "Line buffer",
     "Builds one line (8 chars for 4x4: digits, spaces, newline) and writes "
     "it with one write per row.",
     ["How big is your line buffer for a 9x9?",
      "Where does the newline go?"]),
    ("print.board", None, "Whole-board buffer",
     "Builds the whole output in one buffer and writes it with a single "
     "write.",
     ["How did you compute the buffer size?",
      "What is in the buffer if solving fails?"]),
    ("print.putstr", None, "putstr of a built string",
     "Builds the output as a string and hands it to an ft_putstr.",
     ["Who allocates the string and who frees it?",
      "How does ft_putstr know where the string ends?"]),
]

PART_QUESTIONS = {
    "parse": ["Walk me through how argv[1] becomes your clues.",
              "What does your program print for \"4 3 2\"?"],
    "data": ["Where is the grid stored, and who can change it?",
             "How are the clues stored, and which index is the left of row "
             "2?"],
    "solve": ["How does your program fill the grid?",
              "What happens when there is no solution?"],
    "print": ["Show me where the grid is written to the screen.",
              "Where is \"Error\" written, and to which fd?"],
}


def catalog_entries():
    """Every catalog entry (SHAPES "catalog entry")."""
    out = []
    for rule_id, tier, name, explain, questions in ENTRIES:
        out.append({"id": rule_id, "part": rule_id.split(".")[0],
                    "tier": tier, "name": name, "explain": explain,
                    "questions": list(questions),
                    "demo": rule_id.replace(".", "_")})
    return out


def catalog_by_id():
    return {e["id"]: e for e in catalog_entries()}


def catalog_part_questions(part):
    return list(PART_QUESTIONS[part])
