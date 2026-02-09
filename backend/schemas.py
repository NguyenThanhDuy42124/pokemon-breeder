"""
schemas.py – Pydantic models (data shapes for the API).

WHY DO WE NEED THIS?
- SQLAlchemy models define how data is stored in MySQL.
- Pydantic schemas define how data is sent/received via the API.
- They validate data automatically (wrong types → error).
"""

from pydantic import BaseModel
from typing import Optional


# ── Egg Group ───────────────────────────────────────────────
class EggGroupSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}  # allows conversion from SQLAlchemy model


# ── Ability ─────────────────────────────────────────────────
class AbilitySchema(BaseModel):
    id: int
    name: str
    is_hidden: bool = False

    model_config = {"from_attributes": True}


# ── Nature ──────────────────────────────────────────────────
class NatureSchema(BaseModel):
    id: int
    name: str
    increased_stat: Optional[str] = None
    decreased_stat: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Pokémon (response from API) ─────────────────────────────
class PokemonSchema(BaseModel):
    id: int
    name: str
    sprite_url: Optional[str] = None
    hp: int = 0
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0
    gender_rate: float = 50.0
    is_breedable: bool = True
    is_ditto: bool = False
    egg_groups: list[EggGroupSchema] = []
    abilities: list[AbilitySchema] = []

    model_config = {"from_attributes": True}


# ── Pokémon Search Result (lightweight, for autocomplete) ───
class PokemonSearchResult(BaseModel):
    id: int
    name: str
    sprite_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Breeding Request (what the frontend sends) ──────────────
class BreedingRequest(BaseModel):
    """
    The frontend sends this when the user clicks 'Calculate'.

    parent_a_ivs / parent_b_ivs: list of 6 booleans
        [True, True, False, True, False, False]
        means HP=31, Atk=31, Def=random, SpA=31, SpD=random, Spe=random

    held_item: one of "destiny_knot", "power_hp", "power_atk",
               "power_def", "power_spa", "power_spd", "power_spe",
               "everstone", or "none"
    """
    parent_a_id: int
    parent_b_id: int
    parent_a_ivs: list[bool]       # length 6: [hp, atk, def, spa, spd, spe]
    parent_b_ivs: list[bool]       # length 6
    held_item_a: str = "none"      # item held by Parent A
    held_item_b: str = "none"      # item held by Parent B
    parent_a_nature: Optional[str] = None    # e.g. "adamant"
    parent_b_nature: Optional[str] = None
    parent_a_ability: Optional[str] = None   # e.g. "static"
    parent_b_ability: Optional[str] = None
    parent_a_ability_hidden: bool = False     # is Parent A's ability a Hidden Ability?
    parent_b_ability_hidden: bool = False
    breeding_with_ditto: bool = False         # is one parent a Ditto?
    target_ivs: Optional[list[bool]] = None   # desired IV spread, e.g. [T,T,T,T,T,F] = 5IV -Spe
    lang: str = "en"                          # language for explanations: "en" or "vi"


# ── Breeding Result (what the API returns) ───────────────────
class BreedingResultEntry(BaseModel):
    perfect_iv_count: int          # e.g. 5
    probability: float             # e.g. 0.03125
    percentage: str                # e.g. "3.13%"
    explanation: str               # human-readable breakdown


class NatureInheritance(BaseModel):
    """How nature is passed to offspring."""
    inherited_nature: Optional[str] = None     # the nature passed (if Everstone)
    from_parent: Optional[str] = None          # "A" or "B"
    probability: float = 1.0                   # 100% with Everstone, 4% random
    method: str = "random"                     # "everstone" or "random"
    explanation: str = ""


class AbilityInheritance(BaseModel):
    """How ability is passed to offspring."""
    ability_name: Optional[str] = None
    is_hidden: bool = False
    probability: float = 0.0
    explanation: str = ""


class TargetIvResult(BaseModel):
    """Probability of offspring getting the EXACT desired IV spread."""
    target_ivs: list[bool]                    # the desired spread
    target_stats: list[str]                   # human-readable: ["HP","Atk",...]
    target_count: int                         # how many perfect in target
    probability: float
    percentage: str
    eggs_estimate: int                        # ~1/probability
    explanation: str


class BreedingResponse(BaseModel):
    parent_a: str                  # name
    parent_b: str
    held_item_a: str
    held_item_b: str
    inherited_count: int           # how many IVs are inherited (3 or 5)
    results: list[BreedingResultEntry]
    nature_info: Optional[NatureInheritance] = None
    ability_info: Optional[AbilityInheritance] = None
    target_iv_result: Optional[TargetIvResult] = None
