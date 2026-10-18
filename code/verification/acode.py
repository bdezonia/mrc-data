def amin(r: int, c: int, o: int) -> int:
    # 1D path graph (exact)
    if r == 1 or c == 1:
        n = max(r, c)
        alpha = (n + 1) // 2
        if o <= alpha:
            return 0
        return 2 * o - n - 1

    # 2D grids
    N = r * c
    alpha = (N + 1) // 2
    if o <= alpha:
        return 0

    t = o - alpha

    # boundary size
    B = 2 * r + 2 * c - 4

    # interior adjacency cost
    d_int = 3 if min(r, c) == 2 else 4

    both_odd = (r & 1) and (c & 1)

    # last t where boundary-growth formula applies
    t3 = (B // 2 - 1) if both_odd else (B // 2)

    # --- corrected boundary-phase base ---
    if both_odd:
        if t == 1:
            base = 3
        elif t == 2:
            base = 6
        else:
            base = 3 * t - 1
    else:
        if t == 1:
            base = 2
        else:
            base = 3 * t - 2

    if t <= t3:
        return base

    # --- continuity into the interior phase ---
    if both_odd:
        if t3 == 1:
            base_t3 = 3
        elif t3 == 2:
            base_t3 = 6
        else:
            base_t3 = 3 * t3 - 1
    else:
        if t3 == 1:
            base_t3 = 2
        else:
            base_t3 = 3 * t3 - 2

    return base_t3 + d_int * (t - t3)

def amax(r: int, c: int, o: int) -> int:

    if o == 0:
        return 0

    # 1D path
    if r == 1 or c == 1:
        return max(0, o - 1)

    # atomic small-o cases
    if o <= 1:
        return 0
    if o == 2:
        return 1
    if o == 3:
        return 2

    # symmetry
    if r > c:
        r, c = c, r

    best = 0
    for h in range(1, r + 1):
        q = o // h
        t = o - h * q
        w = q + (1 if t > 0 else 0)
        if w == 0 or w > c:
            continue

        if q == 0:
            # single column of height t
            val = t - 1
        else:
            rect = 2 * h * q - h - q
            extra = 0 if t == 0 else (2 * t - 1)
            val = rect + extra

        best = max(best, val)

    return best
