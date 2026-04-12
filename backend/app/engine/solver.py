from collections import Counter
from .board_layout import LETTER_SCORES


def board_is_empty(board, size):
    return all(board[r][c] is None for r in range(size) for c in range(size))


def board_has_letters(board, size):
    return not board_is_empty(board, size)


def board_letters_set(board, size):
    s = set()
    for r in range(size):
        for c in range(size):
            if board[r][c]:
                s.add(board[r][c])
    return s


def rack_counter(rack):
    return Counter(rack)


def can_make_letters(needed, rack_ctr):
    bag = rack_ctr.copy()
    joker_used = []
    for ch in needed:
        if bag[ch] > 0:
            bag[ch] -= 1
        elif bag["?"] > 0:
            bag["?"] -= 1
            joker_used.append(ch)
        else:
            return None
    return joker_used


def get_anchors(board, size, center):
    if board_is_empty(board, size):
        return {center}
    anchors = set()
    for r in range(size):
        for c in range(size):
            if board[r][c] is None:
                for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < size and 0 <= cc < size and board[rr][cc]:
                        anchors.add((r, c))
                        break
    return anchors


def candidate_start_positions(word_len, anchor_r, anchor_c, direction, size):
    if direction == "YATAY":
        for off in range(word_len):
            row = anchor_r
            col = anchor_c - off
            if 0 <= col and col + word_len <= size:
                yield row, col
    else:
        for off in range(word_len):
            row = anchor_r - off
            col = anchor_c
            if 0 <= row and row + word_len <= size:
                yield row, col


def build_pattern(board, row, col, length, direction):
    fixed_positions = {}
    empties = 0
    for i in range(length):
        rr = row + (i if direction == "DIKEY" else 0)
        cc = col + (i if direction == "YATAY" else 0)
        ch = board[rr][cc]
        if ch:
            fixed_positions[i] = ch
        else:
            empties += 1
    return fixed_positions, empties


def word_matches_pattern(word, fixed_positions):
    return all(word[i] == ch for i, ch in fixed_positions.items())


def estimate_needed_letters(word, fixed_positions):
    return [ch for i, ch in enumerate(word) if i not in fixed_positions]


def prefilter_entries_pattern(entries, fixed_positions, rack, board, size):
    rack_ctr = rack_counter(rack)
    rack_set = {k for k, v in rack_ctr.items() if v > 0 and k != "?"}
    board_set = board_letters_set(board, size)
    out = []
    for e in entries:
        word = e["word"]
        if not word_matches_pattern(word, fixed_positions):
            continue
        if board_has_letters(board, size) and not (e["uniq"] & (rack_set | board_set)):
            continue
        out.append(e)
    return out


def fits(board, word, row, col, direction, size, center):
    if direction == "YATAY" and col + len(word) > size:
        return None
    if direction == "DIKEY" and row + len(word) > size:
        return None

    placed, needed = [], []
    touch_count = 0
    adjacent_contacts = 0
    touched_existing = set()

    for i, ch in enumerate(word):
        rr = row + (i if direction == "DIKEY" else 0)
        cc = col + (i if direction == "YATAY" else 0)
        existing = board[rr][cc]
        if existing:
            if existing != ch:
                return None
            touch_count += 1
            touched_existing.add((rr, cc))
        else:
            placed.append((rr, cc, ch))
            needed.append(ch)
            for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                r2, c2 = rr + dr, cc + dc
                if 0 <= r2 < size and 0 <= c2 < size and board[r2][c2]:
                    adjacent_contacts += 1

    if not placed:
        return None

    if direction == "YATAY":
        if col > 0 and board[row][col-1]:
            return None
        endc = col + len(word) - 1
        if endc < size - 1 and board[row][endc+1]:
            return None
    else:
        if row > 0 and board[row-1][col]:
            return None
        endr = row + len(word) - 1
        if endr < size - 1 and board[endr+1][col]:
            return None

    if board_is_empty(board, size):
        if not any((row + (i if direction == "DIKEY" else 0), col + (i if direction == "YATAY" else 0)) == center for i in range(len(word))):
            return None
    elif touch_count == 0 and adjacent_contacts == 0:
        return None

    return placed, needed, touch_count + adjacent_contacts, len(touched_existing)


def cross_word_for_new_tile(board, r, c, ch, direction, size):
    if direction == "YATAY":
        start = r
        while start > 0 and board[start-1][c]:
            start -= 1
        end = r
        while end < size - 1 and board[end+1][c]:
            end += 1
        letters, coords = [], []
        for rr in range(start, end+1):
            letters.append(ch if rr == r else board[rr][c])
            coords.append((rr, c))
        return "".join(letters), coords
    start = c
    while start > 0 and board[r][start-1]:
        start -= 1
    end = c
    while end < size - 1 and board[r][end+1]:
        end += 1
    letters, coords = [], []
    for cc in range(start, end+1):
        letters.append(ch if cc == c else board[r][cc])
        coords.append((r, cc))
    return "".join(letters), coords


def all_words_valid(board, word, direction, placed, word_set, size):
    if word not in word_set:
        return False, []
    created = [word]
    for r, c, ch in placed:
        cw, _ = cross_word_for_new_tile(board, r, c, ch, direction, size)
        if len(cw) > 1:
            if cw not in word_set:
                return False, []
            created.append(cw)
    return True, created


def build_joker_cells(placed, joker_used):
    joker_pool = list(joker_used)
    joker_cells = set()
    for r, c, ch in placed:
        if ch in joker_pool:
            joker_cells.add((r, c))
            joker_pool.remove(ch)
    return joker_cells


def letter_score(ch, is_joker):
    return 0 if is_joker else LETTER_SCORES.get(ch, 0)


def apply_bonus(base_value, bonus):
    word_mult = 1
    letter_value = base_value
    if bonus == "H2":
        letter_value *= 2
    elif bonus == "H3":
        letter_value *= 3
    elif bonus in ("K2", "START"):
        word_mult = 2
    elif bonus == "K3":
        word_mult = 3
    return letter_value, word_mult


def score_word_with_coords(board, coords, placed_map, bonus_grid, joker_cells):
    total = 0
    word_mult = 1
    for r, c in coords:
        if (r, c) in placed_map:
            ch = placed_map[(r, c)]
            base = letter_score(ch, (r, c) in joker_cells)
            letter_val, wm = apply_bonus(base, bonus_grid[r][c])
            total += letter_val
            word_mult *= wm
        else:
            total += LETTER_SCORES.get(board[r][c], 0)
    return total * word_mult


def score_move(word, row, col, direction, placed, bonus_grid, joker_used, board, size):
    placed_map = {(r, c): ch for r, c, ch in placed}
    joker_cells = build_joker_cells(placed, joker_used)
    main_coords = [(row + (i if direction == "DIKEY" else 0), col + (i if direction == "YATAY" else 0)) for i in range(len(word))]
    main_score = score_word_with_coords(board, main_coords, placed_map, bonus_grid, joker_cells)
    cross_total = 0
    created_cross = []
    for r, c, ch in placed:
        cw, coords = cross_word_for_new_tile(board, r, c, ch, direction, size)
        if len(cw) > 1:
            cross_total += score_word_with_coords(board, coords, placed_map, bonus_grid, joker_cells)
            created_cross.append(cw)
    return main_score + cross_total, created_cross


def normalize_board(raw_board, size):
    board = []
    for r in range(size):
        row = []
        raw_row = raw_board[r] if r < len(raw_board) else []
        for c in range(size):
            cell = raw_row[c] if c < len(raw_row) else None
            cell = (cell or "").strip().upper()
            row.append(cell if cell else None)
        board.append(row)
    return board


def find_best_moves(board, bonus_grid, rack, words, by_length, size, center, limit=30):
    results = []
    word_set = set(words)
    max_len = min(size, len(rack) + size)
    rack_ctr = rack_counter(rack)
    anchors = get_anchors(board, size, center)
    lengths = [l for l in range(2, max_len + 1) if l in by_length]

    for length in lengths:
        raw_entries = by_length[length]
        for direction in ("YATAY", "DIKEY"):
            starts = set()
            if board_is_empty(board, size):
                starts.update(candidate_start_positions(length, center[0], center[1], direction, size))
            else:
                for ar, ac in anchors:
                    for row, col in candidate_start_positions(length, ar, ac, direction, size):
                        starts.add((row, col))

            pattern_cache = {}
            for row, col in starts:
                fixed_positions, empties = build_pattern(board, row, col, length, direction)
                if empties == 0:
                    continue
                cache_key = (length, tuple(sorted(fixed_positions.items())))
                if cache_key not in pattern_cache:
                    pattern_cache[cache_key] = prefilter_entries_pattern(raw_entries, fixed_positions, rack, board, size)
                entries = pattern_cache[cache_key]

                for e in entries:
                    word = e["word"]
                    needed_preview = estimate_needed_letters(word, fixed_positions)
                    if can_make_letters(needed_preview, rack_ctr) is None:
                        continue
                    fit = fits(board, word, row, col, direction, size, center)
                    if not fit:
                        continue
                    placed, needed, interaction_score, overlap_count = fit
                    joker_used = can_make_letters(needed, rack_ctr)
                    if joker_used is None:
                        continue
                    ok, created_words = all_words_valid(board, word, direction, placed, word_set, size)
                    if not ok:
                        continue
                    score, cross_words = score_move(word, row, col, direction, placed, bonus_grid, joker_used, board, size)
                    results.append({
                        "word": word,
                        "row": row,
                        "col": col,
                        "direction": direction,
                        "score": score,
                        "placed": [{"row": r, "col": c, "letter": ch} for r, c, ch in placed],
                        "createdWords": created_words,
                        "interaction": interaction_score,
                        "crossWords": cross_words,
                        "overlap": overlap_count,
                    })

    results.sort(key=lambda x: (-x["score"], x["word"], x["row"], x["col"]))
    uniq, seen = [], set()
    for m in results:
        key = (m["word"], m["row"], m["col"], m["direction"], m["score"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(m)
        if len(uniq) >= limit:
            break
    return uniq
