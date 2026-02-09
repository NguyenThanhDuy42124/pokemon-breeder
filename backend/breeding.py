"""
breeding.py -- Pokemon Gen 9 IV breeding calculator (combinatorics-based).

=== WHAT ARE IVs? ===
Every Pokemon has 6 stats: HP, Atk, Def, SpA, SpD, Spe.
Each stat has a hidden "Individual Value" (IV) ranging from 0 to 31.
An IV of 31 is called "perfect" -- it maximizes that stat.

=== HOW BREEDING IVs WORK (Gen 9) ===
1. Normally, 3 out of parent's 6 IVs are randomly inherited by the baby.
2. The other 3 IVs are rolled randomly (0-31 each).
3. Items modify this:
   - Destiny Knot: 5 IVs inherited instead of 3. (HUGE boost!)
   - Power Items: Guarantees one specific stat is inherited from the holder.
   - Everstone: Passes the holder's nature to the offspring (100% guaranteed).

=== NATURE INHERITANCE (Gen 9) ===
- If a parent holds Everstone: offspring gets that parent's nature (100%).
- If BOTH parents hold Everstone: 50/50 which nature is passed.
- If neither holds Everstone: random nature from 25 (4% each).
- Everstone does NOT affect IVs — only nature.

=== ABILITY INHERITANCE (Gen 9) ===
- When NOT breeding with Ditto:
  - Female parent's ability has 80% chance to pass (normal ability).
  - Hidden Ability from female: 60% chance to pass.
- When breeding with Ditto:
  - Non-Ditto parent's ability has 60% chance to pass.
  - Hidden Ability from non-Ditto: 60% chance to pass.
- Male parent can only pass abilities when breeding with Ditto.

=== MATH APPROACH ===
We use combinatorics (exact probability), NOT Monte Carlo simulation.
"""

from itertools import combinations
from math import comb
from schemas import (
    BreedingResponse, BreedingResultEntry,
    NatureInheritance, AbilityInheritance,
    TargetIvResult,
)


# The 6 stat names (order matches the parent_ivs boolean lists)
STATS = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]

# Maps Power Item names -> the stat index they guarantee
POWER_ITEMS = {
    "power_hp":  0,   # Power Weight -> HP
    "power_atk": 1,   # Power Bracer -> Attack
    "power_def": 2,   # Power Belt   -> Defense
    "power_spa": 3,   # Power Lens   -> Sp. Attack
    "power_spd": 4,   # Power Band   -> Sp. Defense
    "power_spe": 5,   # Power Anklet -> Speed
}


# ================================================================
# NATURE INHERITANCE
# ================================================================

def calculate_nature_inheritance(
    held_item_a: str,
    held_item_b: str,
    parent_a_nature: str | None,
    parent_b_nature: str | None,
    lang: str = "en",
) -> NatureInheritance:
    """
    Calculate how nature is passed to offspring.

    Gen 9 Rules:
    - Everstone on one parent: 100% that parent's nature.
    - Everstone on BOTH: 50% chance of either parent's nature.
    - No Everstone: random from 25 natures (4% each).
    """
    vi = lang == "vi"
    a_everstone = held_item_a == "everstone"
    b_everstone = held_item_b == "everstone"

    if a_everstone and b_everstone:
        # Both hold Everstone: 50/50 random pick
        if vi:
            expl = (
                f"Cả hai bố mẹ đều giữ Đá Bất Biến. "
                f"50% cơ hội tính cách của Bố/Mẹ A ({parent_a_nature or '?'}), "
                f"50% cơ hội tính cách của Bố/Mẹ B ({parent_b_nature or '?'})."
            )
        else:
            expl = (
                f"Both parents hold Everstone. "
                f"50% chance of Parent A's nature ({parent_a_nature or '?'}), "
                f"50% chance of Parent B's nature ({parent_b_nature or '?'})."
            )
        return NatureInheritance(
            inherited_nature=f"{parent_a_nature or '?'} or {parent_b_nature or '?'}",
            from_parent="A or B (50/50)",
            probability=0.5,
            method="everstone_both",
            explanation=expl,
        )
    elif a_everstone:
        if vi:
            expl = (
                f"Bố/Mẹ A giữ Đá Bất Biến. "
                f"Con chắc chắn có tính cách {parent_a_nature or '?'}."
            )
        else:
            expl = (
                f"Parent A holds Everstone. "
                f"Offspring is guaranteed to have {parent_a_nature or '?'} nature."
            )
        return NatureInheritance(
            inherited_nature=parent_a_nature,
            from_parent="A",
            probability=1.0,
            method="everstone",
            explanation=expl,
        )
    elif b_everstone:
        if vi:
            expl = (
                f"Bố/Mẹ B giữ Đá Bất Biến. "
                f"Con chắc chắn có tính cách {parent_b_nature or '?'}."
            )
        else:
            expl = (
                f"Parent B holds Everstone. "
                f"Offspring is guaranteed to have {parent_b_nature or '?'} nature."
            )
        return NatureInheritance(
            inherited_nature=parent_b_nature,
            from_parent="B",
            probability=1.0,
            method="everstone",
            explanation=expl,
        )
    else:
        if vi:
            expl = (
                "Không có Đá Bất Biến. "
                "Tính cách được chọn ngẫu nhiên từ 25 loại (mỗi loại 4%)."
            )
        else:
            expl = (
                "No Everstone held. "
                "Nature is randomly chosen from 25 natures (4% each)."
            )
        return NatureInheritance(
            inherited_nature=None,
            from_parent=None,
            probability=1.0 / 25.0,
            method="random",
            explanation=expl,
        )


# ================================================================
# ABILITY INHERITANCE
# ================================================================

def calculate_ability_inheritance(
    parent_a_ability: str | None,
    parent_b_ability: str | None,
    parent_a_ability_hidden: bool,
    parent_b_ability_hidden: bool,
    breeding_with_ditto: bool,
    lang: str = "en",
) -> AbilityInheritance:
    """
    Calculate how ability is inherited by offspring.

    Gen 9 Rules:
    - Breeding with Ditto: non-Ditto parent passes ability (60% normal, 60% HA).
    - NOT breeding with Ditto: female parent passes ability (80% normal, 60% HA).
    - If the passing parent has a Hidden Ability: 60% HA, 20% normal slot 1, 20% normal slot 2.
    - If the passing parent has a normal ability: 80% same ability, 20% other slot.
    """
    vi = lang == "vi"
    if breeding_with_ditto:
        ability = parent_a_ability
        is_hidden = parent_a_ability_hidden

        if is_hidden:
            if vi:
                expl = (
                    f"Lai với Ditto. Bố/Mẹ không phải Ditto có Đặc tính ẩn ({ability or '?'}). "
                    f"60% cơ hội con nhận Đặc tính ẩn, "
                    f"40% cơ hội con nhận đặc tính thường."
                )
            else:
                expl = (
                    f"Breeding with Ditto. Non-Ditto parent has Hidden Ability ({ability or '?'}). "
                    f"60% chance offspring gets Hidden Ability, "
                    f"40% chance offspring gets a regular ability."
                )
            return AbilityInheritance(
                ability_name=ability,
                is_hidden=True,
                probability=0.6,
                explanation=expl,
            )
        else:
            if vi:
                expl = (
                    f"Lai với Ditto. Bố/Mẹ không phải Ditto có đặc tính thường ({ability or '?'}). "
                    f"60% cơ hội con nhận cùng đặc tính, "
                    f"40% cơ hội con nhận đặc tính thường còn lại."
                )
            else:
                expl = (
                    f"Breeding with Ditto. Non-Ditto parent has regular ability ({ability or '?'}). "
                    f"60% chance offspring gets the same ability, "
                    f"40% chance offspring gets the other regular ability slot."
                )
            return AbilityInheritance(
                ability_name=ability,
                is_hidden=False,
                probability=0.6,
                explanation=expl,
            )
    else:
        ability = parent_a_ability
        is_hidden = parent_a_ability_hidden

        if is_hidden:
            if vi:
                expl = (
                    f"Bố/Mẹ cái có Đặc tính ẩn ({ability or '?'}). "
                    f"60% cơ hội con nhận Đặc tính ẩn. "
                    f"20% cơ hội cho mỗi đặc tính thường."
                )
            else:
                expl = (
                    f"Female parent has Hidden Ability ({ability or '?'}). "
                    f"60% chance offspring gets Hidden Ability. "
                    f"20% chance for each regular ability slot."
                )
            return AbilityInheritance(
                ability_name=ability,
                is_hidden=True,
                probability=0.6,
                explanation=expl,
            )
        else:
            if vi:
                expl = (
                    f"Bố/Mẹ cái có đặc tính thường ({ability or '?'}). "
                    f"80% cơ hội con nhận cùng đặc tính. "
                    f"20% cơ hội con nhận đặc tính thường còn lại."
                )
            else:
                expl = (
                    f"Female parent has regular ability ({ability or '?'}). "
                    f"80% chance offspring gets the same ability. "
                    f"20% chance offspring gets the other regular ability."
                )
            return AbilityInheritance(
                ability_name=ability,
                is_hidden=False,
                probability=0.8,
                explanation=expl,
            )


# ================================================================
# IV PROBABILITY CALCULATION (CORE MATH)
# ================================================================

def calculate_breeding(
    parent_a_name: str,
    parent_b_name: str,
    parent_a_ivs: list[bool],
    parent_b_ivs: list[bool],
    held_item_a: str,
    held_item_b: str,
    parent_a_nature: str | None = None,
    parent_b_nature: str | None = None,
    parent_a_ability: str | None = None,
    parent_b_ability: str | None = None,
    parent_a_ability_hidden: bool = False,
    parent_b_ability_hidden: bool = False,
    breeding_with_ditto: bool = False,
    target_ivs: list[bool] | None = None,
    lang: str = "en",
) -> BreedingResponse:
    """
    Main entry point called by the API.

    Parameters:
        parent_a_ivs: [True, True, False, True, True, True]
                       HP=31, Atk=31, Def=random, SpA=31, SpD=31, Spe=31
        held_item_a:   "destiny_knot", "power_atk", "everstone", or "none"
        (same for parent B)

    Returns:
        BreedingResponse with probability for each perfect IV count (0-6),
        plus nature and ability inheritance info.
    """

    # ── Step 1: Determine how many IVs are inherited ──
    # Default: 3 IVs inherited randomly from parents.
    # Destiny Knot (on EITHER parent): bumps this to 5.
    # Note: Everstone does NOT affect IV inheritance.
    has_destiny_knot = held_item_a == "destiny_knot" or held_item_b == "destiny_knot"
    base_inherited = 5 if has_destiny_knot else 3

    # ── Step 2: Determine forced (guaranteed) stats from Power Items ──
    forced_stats = set()
    forced_perfect = set()

    if held_item_a in POWER_ITEMS:
        stat_idx = POWER_ITEMS[held_item_a]
        forced_stats.add(stat_idx)
        if parent_a_ivs[stat_idx]:
            forced_perfect.add(stat_idx)

    if held_item_b in POWER_ITEMS:
        stat_idx = POWER_ITEMS[held_item_b]
        if stat_idx in forced_stats:
            pass  # same stat conflict — handled below
        else:
            forced_stats.add(stat_idx)
            if parent_b_ivs[stat_idx]:
                forced_perfect.add(stat_idx)

    # ── Step 3: Handle same-stat Power Item conflict ──
    same_power_stat = None
    same_power_prob = 1.0

    if held_item_a in POWER_ITEMS and held_item_b in POWER_ITEMS:
        idx_a = POWER_ITEMS[held_item_a]
        idx_b = POWER_ITEMS[held_item_b]
        if idx_a == idx_b:
            same_power_stat = idx_a
            a_perfect = parent_a_ivs[idx_a]
            b_perfect = parent_b_ivs[idx_b]
            if a_perfect and b_perfect:
                same_power_prob = 1.0
            elif a_perfect or b_perfect:
                same_power_prob = 0.5
            else:
                same_power_prob = 0.0
            forced_stats = {idx_a}
            forced_perfect = set()

    # ── Step 4: Calculate remaining inherited count ──
    remaining_inherited = max(base_inherited - len(forced_stats), 0)

    # ── Step 5: Per-stat perfect probability when inherited ──
    stat_inherit_prob = []
    for i in range(6):
        a_perf = parent_a_ivs[i]
        b_perf = parent_b_ivs[i]
        if a_perf and b_perf:
            stat_inherit_prob.append(1.0)
        elif a_perf or b_perf:
            stat_inherit_prob.append(0.5)
        else:
            stat_inherit_prob.append(0.0)

    free_indices = [i for i in range(6) if i not in forced_stats]

    # ── Step 6: Compute probabilities using combinatorics ──
    results = {k: 0.0 for k in range(7)}

    total_combos = comb(len(free_indices), remaining_inherited)
    if total_combos == 0:
        total_combos = 1

    for chosen in combinations(free_indices, remaining_inherited):
        inherited_set = forced_stats | set(chosen)

        stat_probs = []
        for i in range(6):
            if i in forced_stats and same_power_stat is not None and i == same_power_stat:
                stat_probs.append(same_power_prob)
            elif i in inherited_set:
                stat_probs.append(stat_inherit_prob[i])
            else:
                stat_probs.append(1.0 / 32.0)

        # DP: P(exactly k perfect) over 6 stats
        dp = [0.0] * 7
        dp[0] = 1.0

        for i in range(6):
            p = stat_probs[i]
            new_dp = [0.0] * 7
            for j in range(7):
                if dp[j] == 0:
                    continue
                if j < 7:
                    new_dp[j] += dp[j] * (1.0 - p)
                if j + 1 < 7:
                    new_dp[j + 1] += dp[j] * p
            dp = new_dp

        for k in range(7):
            results[k] += dp[k] / total_combos

    # ── Step 7: Build IV result entries ──
    result_entries = []
    for k in range(7):
        prob = results[k]
        pct = prob * 100

        if prob < 1e-10:
            continue

        explanation = _build_explanation(
            k, prob, parent_a_ivs, parent_b_ivs,
            has_destiny_knot, forced_stats, base_inherited, lang,
        )

        result_entries.append(BreedingResultEntry(
            perfect_iv_count=k,
            probability=round(prob, 8),
            percentage=f"{pct:.4f}%",
            explanation=explanation,
        ))

    # ── Step 8: Nature inheritance ──
    nature_info = calculate_nature_inheritance(
        held_item_a, held_item_b,
        parent_a_nature, parent_b_nature, lang,
    )

    # ── Step 9: Ability inheritance ──
    ability_info = calculate_ability_inheritance(
        parent_a_ability, parent_b_ability,
        parent_a_ability_hidden, parent_b_ability_hidden,
        breeding_with_ditto, lang,
    )

    # ── Step 10: Target IV probability (exact spread) ──
    target_iv_result = None
    if target_ivs and len(target_ivs) == 6:
        target_iv_result = _calculate_target_ivs(
            target_ivs=target_ivs,
            parent_a_ivs=parent_a_ivs,
            parent_b_ivs=parent_b_ivs,
            stat_inherit_prob=stat_inherit_prob,
            forced_stats=forced_stats,
            same_power_stat=same_power_stat,
            same_power_prob=same_power_prob,
            free_indices=free_indices,
            remaining_inherited=remaining_inherited,
            total_combos=total_combos,
            has_destiny_knot=has_destiny_knot,
            base_inherited=base_inherited,
            lang=lang,
        )

    return BreedingResponse(
        parent_a=parent_a_name,
        parent_b=parent_b_name,
        held_item_a=held_item_a,
        held_item_b=held_item_b,
        inherited_count=base_inherited,
        results=result_entries,
        nature_info=nature_info,
        ability_info=ability_info,
        target_iv_result=target_iv_result,
    )


def _calculate_target_ivs(
    target_ivs: list[bool],
    parent_a_ivs: list[bool],
    parent_b_ivs: list[bool],
    stat_inherit_prob: list[float],
    forced_stats: set,
    same_power_stat,
    same_power_prob: float,
    free_indices: list[int],
    remaining_inherited: int,
    total_combos: int,
    has_destiny_knot: bool,
    base_inherited: int,
    lang: str = "en",
) -> TargetIvResult:
    """
    Calculate the probability of getting the EXACT target IV spread.

    Unlike the general calculation (which computes P(exactly N perfect)),
    this computes P(all stats in target_ivs are 31), regardless of other stats.

    Example: target_ivs = [T,T,T,T,T,F] means we want HP,Atk,Def,SpA,SpD = 31
    and we don't care about Spe.
    """
    vi = lang == "vi"
    target_indices = [i for i in range(6) if target_ivs[i]]
    target_count = len(target_indices)
    target_stat_names = [STATS[i] for i in target_indices]

    prob_total = 0.0

    for chosen in combinations(free_indices, remaining_inherited):
        inherited_set = forced_stats | set(chosen)

        # For each target stat: compute probability it's 31
        # For non-target stats: we don't care, so probability = 1.0
        combo_prob = 1.0
        for i in range(6):
            if not target_ivs[i]:
                # Don't care about this stat
                continue

            if i in forced_stats and same_power_stat is not None and i == same_power_stat:
                combo_prob *= same_power_prob
            elif i in inherited_set:
                combo_prob *= stat_inherit_prob[i]
            else:
                # Not inherited — must roll 31 randomly (1/32)
                combo_prob *= 1.0 / 32.0

        prob_total += combo_prob / total_combos

    # Build explanation
    pct = prob_total * 100
    eggs = max(1, round(1.0 / prob_total)) if prob_total > 0 else 0

    lines = []
    if vi:
        lines.append(f"Mục tiêu: {', '.join(target_stat_names)} = 31 ({target_count} chỉ số).")
    else:
        lines.append(f"Target: {', '.join(target_stat_names)} = 31 ({target_count} stats).")

    a_match = sum(1 for i in target_indices if parent_a_ivs[i])
    b_match = sum(1 for i in target_indices if parent_b_ivs[i])
    both_match = sum(1 for i in target_indices if parent_a_ivs[i] and parent_b_ivs[i])

    if vi:
        lines.append(f"Bố/Mẹ A đáp ứng {a_match}/{target_count} chỉ số mục tiêu.")
        lines.append(f"Bố/Mẹ B đáp ứng {b_match}/{target_count} chỉ số mục tiêu.")
        lines.append(f"Cả hai bố mẹ đáp ứng {both_match}/{target_count} chỉ số (100% nếu được di truyền).")
    else:
        lines.append(f"Parent A covers {a_match}/{target_count} target stats.")
        lines.append(f"Parent B covers {b_match}/{target_count} target stats.")
        lines.append(f"Both parents cover {both_match}/{target_count} target stats (100% if inherited).")

    if has_destiny_knot:
        if vi:
            lines.append(f"Dây Chỉ Đỏ: 5 trong 6 IVs được di truyền.")
        else:
            lines.append(f"Destiny Knot: 5 of 6 IVs inherited.")
    else:
        if vi:
            lines.append(f"Không có Dây Chỉ Đỏ: chỉ 3 trong 6 IVs được di truyền.")
        else:
            lines.append(f"No Destiny Knot: only 3 of 6 IVs inherited.")

    if forced_stats:
        forced_names = [STATS[i] for i in sorted(forced_stats)]
        if vi:
            lines.append(f"Vật phẩm Sức Mạnh ép: {', '.join(forced_names)}.")
        else:
            lines.append(f"Power Item forces: {', '.join(forced_names)}.")

    non_target = [STATS[i] for i in range(6) if not target_ivs[i]]
    if non_target:
        if vi:
            lines.append(f"Không quan tâm: {', '.join(non_target)}.")
        else:
            lines.append(f"Don't care about: {', '.join(non_target)}.")

    lines.append("")
    if prob_total > 0:
        if vi:
            lines.append(f"Xác suất: {pct:.4f}% (khoảng 1 trong {eggs} trứng).")
        else:
            lines.append(f"Probability: {pct:.4f}% (about 1 in {eggs} eggs).")
    else:
        if vi:
            lines.append(f"Xác suất: 0% -- không thể với bố mẹ và vật phẩm hiện tại.")
        else:
            lines.append(f"Probability: 0% -- impossible with these parents and items.")

    return TargetIvResult(
        target_ivs=target_ivs,
        target_stats=target_stat_names,
        target_count=target_count,
        probability=round(prob_total, 8),
        percentage=f"{pct:.4f}%",
        eggs_estimate=eggs,
        explanation="\n".join(lines),
    )


def _build_explanation(
    perfect_count: int,
    probability: float,
    parent_a_ivs: list[bool],
    parent_b_ivs: list[bool],
    has_destiny_knot: bool,
    forced_stats: set,
    inherited_count: int,
    lang: str = "en",
) -> str:
    """
    Build a human-readable explanation of how this probability was calculated.
    This is shown in the modal when the user clicks a percentage.
    """
    vi = lang == "vi"
    a_perfect = sum(parent_a_ivs)
    b_perfect = sum(parent_b_ivs)
    both_perfect = sum(1 for i in range(6) if parent_a_ivs[i] and parent_b_ivs[i])

    lines = []
    if vi:
        lines.append(f"Mục tiêu: {perfect_count} IVs hoàn hảo trong 6.")
        lines.append(f"Bố/Mẹ A có {a_perfect} IVs hoàn hảo, Bố/Mẹ B có {b_perfect} IVs hoàn hảo.")
        lines.append(f"Chỉ số mà CẢ HAI bố mẹ đều hoàn hảo: {both_perfect} (100% nếu được di truyền).")
    else:
        lines.append(f"Target: {perfect_count} perfect IVs out of 6.")
        lines.append(f"Parent A has {a_perfect} perfect IVs, Parent B has {b_perfect} perfect IVs.")
        lines.append(f"Stats where BOTH parents are perfect: {both_perfect} (100% if inherited).")

    if has_destiny_knot:
        if vi:
            lines.append(f"Dây Chỉ Đỏ: 5 trong 6 IVs được di truyền (thay vì 3).")
        else:
            lines.append(f"Destiny Knot: 5 of 6 IVs inherited (instead of 3).")
    else:
        if vi:
            lines.append(f"Không có Dây Chỉ Đỏ: chỉ 3 trong 6 IVs được di truyền.")
        else:
            lines.append(f"No Destiny Knot: only 3 of 6 IVs inherited.")

    if forced_stats:
        forced_names = [STATS[i] for i in sorted(forced_stats)]
        if vi:
            lines.append(f"Vật phẩm Sức Mạnh ép: {', '.join(forced_names)} luôn được di truyền.")
        else:
            lines.append(f"Power Item forces: {', '.join(forced_names)} always inherited.")

    if vi:
        lines.append(f"Chỉ số không di truyền: mỗi chỉ số có 1/32 (3.125%) cơ hội đạt 31.")
    else:
        lines.append(f"Non-inherited stats: each has 1/32 (3.125%) chance of being 31.")
    lines.append(f"")

    if probability > 0:
        odds = 1.0 / probability if probability > 0 else float("inf")
        if vi:
            lines.append(f"Xác suất: {probability*100:.4f}% (khoảng 1 trong {odds:.0f} trứng).")
        else:
            lines.append(f"Probability: {probability*100:.4f}% (about 1 in {odds:.0f} eggs).")
    else:
        if vi:
            lines.append(f"Xác suất: 0% -- không thể với bố mẹ và vật phẩm hiện tại.")
        else:
            lines.append(f"Probability: 0% -- impossible with these parents and items.")

    return "\n".join(lines)
