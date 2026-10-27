def _lcs(a, b):
    if len(a) < len(b):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ca == cb else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def ratio(s1, s2):
    total = len(s1) + len(s2)
    if total == 0:
        return 100.0
    return 100.0 * (2.0 * _lcs(s1, s2)) / total


def token_sort_ratio(s1, s2):
    return ratio(" ".join(sorted(s1.split())), " ".join(sorted(s2.split())))
