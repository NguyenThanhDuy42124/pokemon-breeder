from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

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
