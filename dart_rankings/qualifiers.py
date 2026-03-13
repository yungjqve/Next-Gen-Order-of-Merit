from __future__ import annotations

from .models import Player
from .utils import normalize_name


def pick_qualifiers(
    main: list[Player],
    youth: list[Player],
    main_n: int,
    youth_n: int,
) -> tuple[list[Player], list[Player], list[Player]]:
    # Build set of all youth player names
    all_youth_names = {normalize_name(p.name) for p in youth}

    # Mark all youth players in the main list
    for p in main:
        if normalize_name(p.name) in all_youth_names:
            p.is_youth = True

    # Top N from main are main qualifiers
    main_qualified = main[:main_n]
    main_set = {normalize_name(p.name) for p in main_qualified}

    for p in main_qualified:
        p.qual_main = True

    # Top M youth not already in main qualifiers
    youth_qualified: list[Player] = []
    for p in youth:
        if normalize_name(p.name) in main_set:
            continue
        p.qual_youth = True
        youth_qualified.append(p)
        if len(youth_qualified) >= youth_n:
            break

    # Mirror youth-qualifier highlight in the full main table
    youth_qual_set = {normalize_name(p.name) for p in youth_qualified}
    for p in main:
        if normalize_name(p.name) in youth_qual_set and not p.qual_main:
            p.qual_youth = True

    all_qualified = main_qualified + youth_qualified
    return main_qualified, youth_qualified, all_qualified
