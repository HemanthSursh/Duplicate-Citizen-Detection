"""Pure-Python stand-in for the one rapidfuzz function this app uses (browser build only).
token_sort_ratio = 100 * (1 - Indel distance / (len(a) + len(b))) on whitespace-sorted tokens,
which equals 200 * LCS(a, b) / (len(a) + len(b)). Verified against rapidfuzz 3.14.5 in tests."""
from . import fuzz
