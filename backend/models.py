from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, Text, UniqueConstraint, DateTime, Index
from sqlalchemy.orm import relationship
from database import Base
import datetime

# ============================================================
# ASSOCIATION TABLES (Many-to-Many relationships)
# ============================================================

# Links a Pokémon to its Egg Groups (a Pokémon can have 1–2 Egg Groups)
pokemon_egg_group = Table(
    "pokemon_egg_group",
    Base.metadata,
    Column("pokemon_id", Integer, ForeignKey("pokemon.id"), primary_key=True),
    Column("egg_group_id", Integer, ForeignKey("egg_group.id"), primary_key=True),
)

# Links a Pokémon to its Abilities (normal + hidden)
pokemon_ability = Table(
    "pokemon_ability",
    Base.metadata,
    Column("pokemon_id", Integer, ForeignKey("pokemon.id"), primary_key=True),
    Column("ability_id", Integer, ForeignKey("ability.id"), primary_key=True),
    Column("is_hidden", Boolean, default=False),
)


# ============================================================
# MAIN TABLES
# ============================================================

class Pokemon(Base):
    """
    A Pokémon species (e.g. Pikachu, Charizard).
    Stores everything needed for breeding calculations.
    Regional forms (Alolan, Galarian, etc.) are separate rows
    linked to their base species via base_species_id.
    """
    __tablename__ = "pokemon"

    id = Column(Integer, primary_key=True, autoincrement=False)   # National Dex number (or 10001+ for forms)
    name = Column(String(100), nullable=False, unique=True)       # e.g. "pikachu", "vulpix-alola"
    sprite_url = Column(String(255), nullable=True)               # Image URL
    form_name = Column(String(50), nullable=True)                 # e.g. "alola", "galar", "hisui", "paldea" (NULL = base form)
    base_species_id = Column(Integer, nullable=True)              # Links to base species id (NULL = is the base form)

    # Base Stats (used for display, not directly for breeding math)
    hp = Column(Integer, default=0)
    attack = Column(Integer, default=0)
    defense = Column(Integer, default=0)
    sp_attack = Column(Integer, default=0)
    sp_defense = Column(Integer, default=0)
    speed = Column(Integer, default=0)

    # Gender ratio: percentage chance of being female (e.g. 50.0)
    # -1.0 means genderless, 0.0 means male-only, 100.0 means female-only
    gender_rate = Column(Float, default=50.0)

    # Can this Pokémon breed at all? (Legendaries / baby Pokémon can't)
    is_breedable = Column(Boolean, default=True)

    # Is this Ditto? (Ditto can breed with anything)
    is_ditto = Column(Boolean, default=False)

    # Species classification flags (for warning messages)
    is_baby = Column(Boolean, default=False)        # e.g. Pichu, Cleffa, Togepi
    is_legendary = Column(Boolean, default=False)   # e.g. Articuno, Mewtwo, Lugia
    is_mythical = Column(Boolean, default=False)     # e.g. Mew, Celebi, Jirachi

    # --- Relationships ---
    egg_groups = relationship(
        "EggGroup",
        secondary=pokemon_egg_group,
        back_populates="pokemon",
    )
    abilities = relationship(
        "Ability",
        secondary=pokemon_ability,
        back_populates="pokemon",
    )


class EggGroup(Base):
    """
    Egg Groups determine which Pokémon can breed together.
    Examples: Monster, Water 1, Field, Fairy, Ditto, Undiscovered.
    """
    __tablename__ = "egg_group"

    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(50), nullable=False, unique=True)  # e.g. "monster"

    pokemon = relationship(
        "Pokemon",
        secondary=pokemon_egg_group,
        back_populates="egg_groups",
    )


class Ability(Base):
    """
    A Pokémon ability (e.g. Static, Overgrow).
    Relevant for breeding because abilities can be passed down.
    """
    __tablename__ = "ability"

    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(100), nullable=False, unique=True)  # e.g. "static"

    pokemon = relationship(
        "Pokemon",
        secondary=pokemon_ability,
        back_populates="abilities",
    )


class Nature(Base):
    """
    25 Pokémon Natures (Adamant, Jolly, etc.).
    Each boosts one stat +10% and lowers another -10%.
    Everstone passes the holder's nature to offspring.
    """
    __tablename__ = "nature"

    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(50), nullable=False, unique=True)       # e.g. "adamant"
    increased_stat = Column(String(20), nullable=True)            # e.g. "attack" (None = neutral)
    decreased_stat = Column(String(20), nullable=True)            # e.g. "defense" (None = neutral)


class Move(Base):
    """
    Pokemon move reference.
    Stored locally so Smogon set move strings can be mapped to stable IDs.
    """
    __tablename__ = "move"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    normalized_name = Column(String(120), nullable=False, unique=True, index=True)


class PokemonMove(Base):
    """
    Links Pokemon to moves and marks whether the move is an Egg Move.
    Optional source_pokemon_id can store a known breeding source parent.
    """
    __tablename__ = "pokemon_moves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pokemon_id = Column(Integer, ForeignKey("pokemon.id"), nullable=False, index=True)
    move_id = Column(Integer, ForeignKey("move.id"), nullable=False, index=True)
    is_egg_move = Column(Boolean, default=False, nullable=False)
    source_pokemon_id = Column(Integer, ForeignKey("pokemon.id"), nullable=True)

    pokemon = relationship("Pokemon", foreign_keys=[pokemon_id])
    move = relationship("Move", foreign_keys=[move_id])
    source_pokemon = relationship("Pokemon", foreign_keys=[source_pokemon_id])


class PokemonMoveLearn(Base):
    """
    Tracks how a Pokemon can learn a move (egg, level-up, machine, tutor).
    Used by planner to find potential egg-move passing parents.
    """
    __tablename__ = "pokemon_move_learn"
    __table_args__ = (
        UniqueConstraint("pokemon_id", "move_id", "learn_method", "generation", name="uq_pml_unique"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pokemon_id = Column(Integer, ForeignKey("pokemon.id"), nullable=False, index=True)
    move_id = Column(Integer, ForeignKey("move.id"), nullable=False, index=True)
    learn_method = Column(String(40), nullable=False, index=True)  # egg, level-up, machine, tutor...
    generation = Column(String(20), nullable=False, default="unknown", index=True)  # ex: gen9

    pokemon = relationship("Pokemon", foreign_keys=[pokemon_id])
    move = relationship("Move", foreign_keys=[move_id])


class SmogonBuild(Base):
    """
    Cached build templates parsed from Smogon JSON sets.
    Data is seeded offline to keep runtime lightweight on low-resource hosts.
    """
    __tablename__ = "smogon_builds"
    __table_args__ = (
        UniqueConstraint("pokemon_id", "format", "build_name", name="uq_smogon_build_unique"),
        Index("idx_smogon_pokemon_gen_format", "pokemon_id", "generation", "format"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pokemon_id = Column(Integer, ForeignKey("pokemon.id"), nullable=False, index=True)
    pokemon_slug = Column(String(120), nullable=False, default="", index=True)

    format = Column(String(40), nullable=False, default="gen9ou", index=True)
    generation = Column(String(20), nullable=False, default="gen9", index=True)
    format_name = Column(String(40), nullable=False, default="ou", index=True)
    format_slug = Column(String(64), nullable=False, default="gen9ou", index=True)
    build_name = Column(String(120), nullable=False)
    source_url = Column(String(255), nullable=True)

    nature = Column(String(50), nullable=True)
    ability = Column(String(100), nullable=True)
    item = Column(String(100), nullable=True)
    moves_json = Column(Text, nullable=False, default="[]")
    move_slugs_json = Column(Text, nullable=False, default="[]")
    move_ids_json = Column(Text, nullable=False, default="[]")
    target_ivs_json = Column(Text, nullable=False, default="[true, true, true, true, true, true]")
    requires_hidden_ability = Column(Boolean, nullable=False, default=False)

    pokemon = relationship("Pokemon")


class CrawlHistory(Base):
    """Tracks ingestion status per Smogon format for admin progress monitoring."""

    __tablename__ = "crawl_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, default="smogon", index=True)
    format = Column(String(64), nullable=False, unique=True, index=True)
    generation = Column(String(20), nullable=False, default="unknown", index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending/success/failed
    record_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    error_log = Column(Text, nullable=True)
    source_url = Column(String(255), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
