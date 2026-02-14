import React, { useState, useEffect } from "react";
import PokemonSearch from "./PokemonSearch";
import AdvancedSearchPanel from "./AdvancedSearchPanel";
import { getPokemonDetails } from "../api";
import { useLanguage } from "../i18n";

const STAT_NAMES = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"];

/** Gender ratio bar: rate = % female, -1 = genderless */
function GenderRatio({ rate }) {
  const { t } = useLanguage();
  if (rate === undefined || rate === null) return null;
  if (rate < 0) {
    return <span className="gender-ratio gender-genderless">{t("genderless")}</span>;
  }
  const male = (100 - rate).toFixed(1).replace(/\.0$/, '');
  const female = rate.toFixed(1).replace(/\.0$/, '');
  return (
    <div className="gender-ratio">
      <div className="gender-bar">
        <div className="gender-male" style={{ width: `${100 - rate}%` }}>
          {100 - rate >= 15 && <span>♂ {male}%</span>}
        </div>
        <div className="gender-female" style={{ width: `${rate}%` }}>
          {rate >= 15 && <span>♀ {female}%</span>}
        </div>
      </div>
      {100 - rate < 15 && rate < 15 ? null :
        (100 - rate < 15 ? <span className="gender-label-outside gender-male-text">♂ {male}%</span> :
        rate < 15 ? <span className="gender-label-outside gender-female-text">♀ {female}%</span> : null)
      }
    </div>
  );
}

/**
 * ParentPanel — One parent's config: Pokemon search, IVs, held item, nature, ability.
 *
 * Props:
 *   label               — "Parent A" or "Parent B" (already translated)
 *   value               — { pokemonId, ivs, heldItem, nature, ability, abilityHidden }
 *   onChange(val)        — state updater
 *   natures             — array of { id, name, increased_stat, decreased_stat }
 *   lockedEggGroups     — egg groups from the OTHER parent (for compatibility lock)
 *   onEggGroupsChange   — callback to report this parent's egg groups up
 */
export default function ParentPanel({ label, value, onChange, natures, lockedEggGroups, onEggGroupsChange }) {
  const { t } = useLanguage();
  const [details, setDetails] = useState(null);
  const [notFoundQuery, setNotFoundQuery] = useState(null);
  const [showBrowse, setShowBrowse] = useState(false);

  const HELD_ITEMS = [
    { value: "none", label: t("itemNone") },
    { value: "destiny_knot", label: t("itemDestinyKnot") },
    { value: "everstone", label: t("itemEverstone") },
    { value: "power_hp", label: t("itemPowerHp") },
    { value: "power_atk", label: t("itemPowerAtk") },
    { value: "power_def", label: t("itemPowerDef") },
    { value: "power_spa", label: t("itemPowerSpa") },
    { value: "power_spd", label: t("itemPowerSpd") },
    { value: "power_spe", label: t("itemPowerSpe") },
  ];

  // Fetch full details when pokemon changes
  useEffect(() => {
    if (!value.pokemonId) {
      setDetails(null);
      onEggGroupsChange && onEggGroupsChange([]);
      return;
    }
    let cancelled = false;
    getPokemonDetails(value.pokemonId).then((d) => {
      if (!cancelled) {
        setDetails(d);
        // Ditto breeds with anything — don't lock partner's egg groups
        onEggGroupsChange && onEggGroupsChange(d.is_ditto ? [] : (d.egg_groups || []));
      }
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [value.pokemonId, onEggGroupsChange]);

  function update(patch) {
    onChange({ ...value, ...patch });
  }

  function handlePokemonSelect(pokemon) {
    setNotFoundQuery(null);
    update({
      pokemonId: pokemon.id,
      nature: null,
      ability: null,
      abilityHidden: false,
    });
  }

  function handleClear() {
    setNotFoundQuery(null);
    setDetails(null);
    update({ pokemonId: null, nature: null, ability: null, abilityHidden: false });
  }

  function handleNotFound(query) {
    if (query === null) {
      setNotFoundQuery(null);
    } else {
      setNotFoundQuery(query);
      setDetails(null);
      update({ pokemonId: null, nature: null, ability: null, abilityHidden: false });
    }
  }

  function toggleIv(index) {
    const newIvs = [...value.ivs];
    newIvs[index] = !newIvs[index];
    update({ ivs: newIvs });
  }

  function setAllIvs(val) {
    update({ ivs: [val, val, val, val, val, val] });
  }

  return (
    <div className="parent-panel">
      <h3 className="parent-label">{label}</h3>

      {/* Pokemon search */}
      <PokemonSearch
        onSelect={handlePokemonSelect}
        onNotFound={handleNotFound}
        onClear={handleClear}
        placeholder={t("searchParent", { label })}
        lockedEggGroups={lockedEggGroups}
        onBrowseClick={() => setShowBrowse(true)}
        selectedPokemon={value.pokemonId}
      />

      {/* Advanced browse panel (modal) */}
      <AdvancedSearchPanel
        open={showBrowse}
        onClose={() => setShowBrowse(false)}
        onSelect={handlePokemonSelect}
        lockedEggGroups={lockedEggGroups}
      />

      {/* Selected pokemon preview */}
      {details && (
        <div className="pokemon-preview">
          {details.sprite_url && (
            <img src={details.sprite_url} alt={details.name} className="preview-sprite" />
          )}
          <div className="preview-info">
            <strong>#{details.id} {details.name}</strong>
            <span className="preview-egg-groups">
              {t("eggGroups")}: {details.egg_groups.map((g) => g.name).join(", ")}
            </span>
            <GenderRatio rate={details.gender_rate} />
          </div>
          <button className="btn-preview-clear" onClick={handleClear} title={t("clear")} type="button">✕</button>
        </div>
      )}

      {/* Not found preview */}
      {notFoundQuery && !details && (
        <div className="pokemon-preview not-found-preview">
          <div className="preview-info">
            <span className="not-found-text">{t("pokemonNotFound", { query: notFoundQuery })}</span>
          </div>
        </div>
      )}

      {/* IV checkboxes */}
      <div className="iv-section">
        <div className="iv-header">
          <span>{t("perfectIvs")}</span>
          <div className="iv-quick-btns">
            <button type="button" onClick={() => setAllIvs(true)} className="btn-mini">{t("all")}</button>
            <button type="button" onClick={() => setAllIvs(false)} className="btn-mini">{t("none")}</button>
          </div>
        </div>
        <div className="iv-grid">
          {STAT_NAMES.map((stat, i) => (
            <label key={stat} className={`iv-checkbox ${value.ivs[i] ? "checked" : ""}`}>
              <input
                type="checkbox"
                checked={value.ivs[i]}
                onChange={() => toggleIv(i)}
              />
              <span className="iv-label">{stat}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Held Item */}
      <div className="field">
        <label>{t("heldItem")}</label>
        <select
          value={value.heldItem}
          onChange={(e) => update({ heldItem: e.target.value })}
        >
          {HELD_ITEMS.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
      </div>

      {/* Nature (only relevant if Everstone is held by this parent) */}
      <div className="field">
        <label>{t("nature")} {value.heldItem === "everstone" && <span className="badge">{t("everstoneActive")}</span>}</label>
        <select
          value={value.nature || ""}
          onChange={(e) => update({ nature: e.target.value || null })}
        >
          <option value="">{t("selectNature")}</option>
          {natures.map((n) => (
            <option key={n.id} value={n.name}>
              {n.name}
              {n.increased_stat && n.decreased_stat
                ? ` (+${n.increased_stat} / -${n.decreased_stat})`
                : ` (${t("neutral")})`}
            </option>
          ))}
        </select>
      </div>

      {/* Ability */}
      {details && details.abilities && details.abilities.length > 0 && (
        <div className="field">
          <label>{t("ability")}</label>
          <select
            value={value.ability || ""}
            onChange={(e) => {
              const sel = details.abilities.find((a) => a.name === e.target.value);
              update({
                ability: e.target.value || null,
                abilityHidden: sel ? sel.is_hidden : false,
              });
            }}
          >
            <option value="">{t("selectAbility")}</option>
            {details.abilities.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name} {a.is_hidden ? `(${t("hiddenAbility")})` : ""}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
