import re
from functools import lru_cache
from sqlalchemy import text
from sqlalchemy.orm import Session

from models import Pokemon, Move, PokemonMove, PokemonMoveLearn, pokemon_egg_group
from slugify_utils import slugify


STAT_LABELS = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
POWER_ITEM_BY_STAT = {
    0: "power_hp",
    1: "power_atk",
    2: "power_def",
    3: "power_spa",
    4: "power_spd",
    5: "power_spe",
}


@lru_cache(maxsize=1024)
def normalize_name(name: str) -> str:
    return slugify(name)


@lru_cache(maxsize=16)
def is_high_iv_target(target_count: int) -> bool:
    return target_count >= 4


@lru_cache(maxsize=16)
def power_item_for_stat(stat_idx: int) -> str:
    return POWER_ITEM_BY_STAT.get(stat_idx, "none")


def _t(lang: str, vi: str, en: str) -> str:
    return vi if lang == "vi" else en


@lru_cache(maxsize=16)
def supports_nature(generation: str | None) -> bool:
    if not generation:
        return True
    m = re.match(r"gen(\d+)", generation.lower())
    if not m:
        return True
    return int(m.group(1)) >= 3


@lru_cache(maxsize=16)
def supports_ability(generation: str | None) -> bool:
    if not generation:
        return True
    m = re.match(r"gen(\d+)", generation.lower())
    if not m:
        return True
    return int(m.group(1)) >= 3


def find_egg_move_parents(db: Session, target_pokemon_id: int, move_slug: str, generation: str | None = None) -> list[dict]:
    move = db.query(Move).filter(Move.normalized_name == normalize_name(move_slug)).first()
    if not move:
        return []

    egg_entry = (
        db.query(PokemonMove.id)
        .filter(
            PokemonMove.pokemon_id == target_pokemon_id,
            PokemonMove.move_id == move.id,
            PokemonMove.is_egg_move,
        )
        .first()
    )
    if not egg_entry:
        return []

    egg_group_ids = [
        row[0]
        for row in db.execute(
            text("SELECT egg_group_id FROM pokemon_egg_group WHERE pokemon_id = :pokemon_id"),
            {"pokemon_id": target_pokemon_id},
        ).fetchall()
    ]
    if not egg_group_ids:
        return []

    candidates = (
        db.query(Pokemon)
        .join(pokemon_egg_group, pokemon_egg_group.c.pokemon_id == Pokemon.id)
        .filter(
            pokemon_egg_group.c.egg_group_id.in_(egg_group_ids),
            Pokemon.id != target_pokemon_id,
            Pokemon.is_breedable,
        )
        .distinct()
        .all()
    )

    candidate_ids = [p.id for p in candidates]
    if not candidate_ids:
        return []

    learn_rows_query = (
        db.query(PokemonMoveLearn)
        .filter(
            PokemonMoveLearn.pokemon_id.in_(candidate_ids),
            PokemonMoveLearn.move_id == move.id,
            PokemonMoveLearn.learn_method.in_(["level-up", "machine"]),
        )
    )
    if generation:
        learn_rows_query = learn_rows_query.filter(PokemonMoveLearn.generation == generation)
    learn_rows = learn_rows_query.all()

    methods_by_pokemon = {}
    for row in learn_rows:
        methods_by_pokemon.setdefault(row.pokemon_id, set()).add(row.learn_method)

    if not methods_by_pokemon:
        return []

    out = []
    for p in candidates:
        methods = sorted(methods_by_pokemon.get(p.id, set()))
        if not methods:
            continue
        out.append(
            {
                "pokemon_id": p.id,
                "pokemon_name": p.name,
                "learn_methods": methods,
            }
        )
    return out


def generate_roadmap(
    db: Session,
    pokemon_id: int,
    parent_a_id: int,
    parent_b_id: int,
    parent_a_ivs: list[bool] | None = None,
    parent_b_ivs: list[bool] | None = None,
    target_nature: str | None = None,
    target_ability: str | None = None,
    target_ivs: list[bool] | None = None,
    target_moves: list[str] | None = None,
    requires_hidden_ability: bool = False,
    generation: str | None = None,
    lang: str = "en",
):
    steps = []
    target_moves = target_moves or []

    target_pokemon = db.query(Pokemon).filter(Pokemon.id == pokemon_id).first()
    parent_a = db.query(Pokemon).filter(Pokemon.id == parent_a_id).first()
    parent_b = db.query(Pokemon).filter(Pokemon.id == parent_b_id).first()

    if not target_pokemon or not parent_a or not parent_b:
        return [
            {
                "step": 1,
                "title": _t(lang, "Du lieu khong hop le", "Invalid data"),
                "description": _t(
                    lang,
                    "Khong tim thay Pokemon muc tieu hoac bo me de lap lo trinh.",
                    "Target Pokemon or parents were not found for roadmap generation.",
                ),
                "tags": ["warning"],
            }
        ]

    # Step 1: Nature (Gen 3+)
    if target_nature and supports_nature(generation):
        steps.append(
            {
                "step": len(steps) + 1,
                "title": _t(lang, "Buoc 1: Nature", "Step 1: Nature"),
                "description": _t(
                    lang,
                    f"Muc tieu Nature la {target_nature}. Neu bo/me hien tai chua dung Nature nay, hay cho bo/me phu hop cam Everstone de truyen 100%.",
                    f"Target nature is {target_nature}. If current parents do not have it, let the matching parent hold Everstone for guaranteed inheritance.",
                ),
                "tags": ["nature", "everstone"],
            }
        )

    if target_nature and not supports_nature(generation):
        steps.append(
            {
                "step": len(steps) + 1,
                "title": _t(lang, "Buoc 1: Gioi han the he", "Step 1: Generation limits"),
                "description": _t(
                    lang,
                    f"{generation or 'The he nay'} khong ho tro Nature/Ability inheritance, bo qua buoc Everstone.",
                    f"{generation or 'This generation'} does not support Nature/Ability inheritance, skipping Everstone planning.",
                ),
                "tags": ["generation-rule"],
            }
        )

    # Step 2: Egg Moves
    egg_move_suggestions = []
    for move_name in target_moves:
        parent_candidates = find_egg_move_parents(
            db=db,
            target_pokemon_id=pokemon_id,
            move_slug=move_name,
            generation=generation,
        )

        if not parent_candidates:
            continue

        top = parent_candidates[:5]
        top_text = ", ".join([f"{x['pokemon_name']} ({'/'.join(x['learn_methods'])})" for x in top])
        egg_move_suggestions.append(
            _t(
                lang,
                f"{move_name} la Egg Move. Bo me tiem nang trong cung Egg Group: {top_text}.",
                f"{move_name} is an Egg Move. Potential parents in shared Egg Groups: {top_text}.",
            )
        )

    if egg_move_suggestions:
        steps.append(
            {
                "step": len(steps) + 1,
                "title": _t(lang, "Buoc 2: Egg Moves", "Step 2: Egg Moves"),
                "description": "\n".join(egg_move_suggestions),
                "tags": ["egg-move", "breeding-path"],
            }
        )

    # Step 3: IVs + Items
    iv_tags = []
    iv_lines = []
    resolved_target_ivs = target_ivs if target_ivs and len(target_ivs) == 6 else [True] * 6
    target_count = sum(1 for v in resolved_target_ivs if v)

    if is_high_iv_target(target_count):
        iv_tags.append("destiny-knot")
        iv_lines.append(
            _t(
                lang,
                "Muc tieu IV cao (>=4). Goi y dung Destiny Knot de tang so IV di truyen len 5/6.",
                "High IV target (>=4). Use Destiny Knot to increase inherited IVs to 5/6.",
            )
        )

    if parent_a_ivs and parent_b_ivs and len(parent_a_ivs) == 6 and len(parent_b_ivs) == 6:
        missing_target_stats = []
        for idx in range(6):
            if not resolved_target_ivs[idx]:
                continue
            if parent_a_ivs[idx] or parent_b_ivs[idx]:
                continue
            missing_target_stats.append(idx)

        if len(missing_target_stats) == 1:
            stat_idx = missing_target_stats[0]
            item = power_item_for_stat(stat_idx)
            iv_tags.append("power-item")
            iv_lines.append(
                _t(
                    lang,
                    f"Dang thieu ro ri mot chi so muc tieu ({STAT_LABELS[stat_idx]}). Goi y uu tien {item} de khoa chi so nay khi breed.",
                    f"One target stat is clearly missing ({STAT_LABELS[stat_idx]}). Prioritize {item} to force inheritance for that stat.",
                )
            )

    if iv_lines:
        steps.append(
            {
                "step": len(steps) + 1,
                "title": _t(lang, "Buoc 3: IVs va Item", "Step 3: IVs and Items"),
                "description": "\n".join(iv_lines),
                "tags": iv_tags or ["ivs"],
            }
        )

    # Step 4: Warnings and HA (Gen 3+)
    warnings = []
    warning_tags = ["warning"]

    if target_pokemon.is_baby:
        warnings.append(
            _t(lang, "Pokemon muc tieu la Baby: khong the breed truc tiep.", "Target Pokemon is a Baby: cannot breed directly.")
        )
    if target_pokemon.is_legendary:
        warnings.append(
            _t(lang, "Pokemon muc tieu la Legendary: thuong khong breed duoc.", "Target Pokemon is Legendary: usually not breedable.")
        )
    if target_pokemon.is_mythical:
        warnings.append(
            _t(lang, "Pokemon muc tieu la Mythical: thuong khong breed duoc.", "Target Pokemon is Mythical: usually not breedable.")
        )

    if requires_hidden_ability and supports_ability(generation):
        warning_tags.append("hidden-ability")
        warnings.append(
            _t(
                lang,
                f"Build muc tieu can Hidden Ability ({target_ability or 'HA'}). Hay dam bao bo/me truyen co HA.",
                f"Target build requires Hidden Ability ({target_ability or 'HA'}). Ensure passing parent has HA.",
            )
        )

    if requires_hidden_ability and not supports_ability(generation):
        warnings.append(
            _t(
                lang,
                f"{generation or 'The he nay'} khong co co che Hidden Ability inheritance.",
                f"{generation or 'This generation'} does not have Hidden Ability inheritance.",
            )
        )

    if warnings:
        steps.append(
            {
                "step": len(steps) + 1,
                "title": _t(lang, "Buoc 4: Canh bao", "Step 4: Warnings"),
                "description": "\n".join(warnings),
                "tags": warning_tags,
            }
        )

    if not steps:
        steps.append(
            {
                "step": 1,
                "title": _t(lang, "Lo trinh co ban", "Basic roadmap"),
                "description": _t(
                    lang,
                    "Khong co dieu kien dac biet. Ban co the bat dau breeding voi cau hinh hien tai.",
                    "No special constraints detected. You can start breeding with the current setup.",
                ),
                "tags": ["ok"],
            }
        )

    return steps


def build_breeding_plan(*args, **kwargs):
    # Backward-compatible alias used by existing endpoints.
    return generate_roadmap(*args, **kwargs)
