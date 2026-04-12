import React, { useState, useEffect } from "react";
import PokemonSearch from "./PokemonSearch";
import AdvancedSearchPanel from "./AdvancedSearchPanel";
import { getPokemonDetails, getPokemonForms, getSmogonBuilds, getSmogonBuildOptions } from "../api";
import { useLanguage } from "../i18n";

const STAT_NAMES = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"];

/** Format region name for display: "alola" → "Alola", "galar" → "Galar" */
function formatRegion(region) {
  if (!region) return "Base";
  return region.charAt(0).toUpperCase() + region.slice(1);
}

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
export default function ParentPanel({ label, value, onChange, natures, lockedEggGroups, onEggGroupsChange, onBuildApply }) {
  const { t } = useLanguage();
  const [details, setDetails] = useState(null);
  const [notFoundQuery, setNotFoundQuery] = useState(null);
  const [showBrowse, setShowBrowse] = useState(false);
  const [forms, setForms] = useState([]);       // available regional forms
  const [activeFormId, setActiveFormId] = useState(null);  // currently selected form ID
  const [builds, setBuilds] = useState([]);
  const [selectedGeneration, setSelectedGeneration] = useState("");
  const [selectedFormatName, setSelectedFormatName] = useState("");
  const [selectedBuildId, setSelectedBuildId] = useState("");
  const [buildOptions, setBuildOptions] = useState({ generations: [], formats: [] });

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
      setForms([]);
      setActiveFormId(null);
      setBuilds([]);
      setBuildOptions({ generations: [], formats: [] });
      setSelectedGeneration("");
      setSelectedFormatName("");
      setSelectedBuildId("");
      onEggGroupsChange && onEggGroupsChange([]);
      return;
    }
    let cancelled = false;
    getPokemonDetails(value.pokemonId).then((d) => {
      if (!cancelled) {
        setDetails(d);
        setActiveFormId(value.pokemonId);
        onEggGroupsChange && onEggGroupsChange(d.is_ditto ? [] : (d.egg_groups || []));
      }
    }).catch(() => {});
    // Also fetch available forms
    getPokemonForms(value.pokemonId).then((f) => {
      if (!cancelled) setForms(f || []);
    }).catch(() => {});

    getSmogonBuildOptions(value.pokemonId).then((meta) => {
      if (!cancelled) setBuildOptions(meta || { generations: [], formats: [] });
    }).catch(() => {
      if (!cancelled) setBuildOptions({ generations: [], formats: [] });
    });
    return () => { cancelled = true; };
  }, [value.pokemonId, onEggGroupsChange]);

  useEffect(() => {
    if (!value.pokemonId || !selectedGeneration) {
      setBuilds([]);
      setSelectedFormatName("");
      setSelectedBuildId("");
      return;
    }

    let cancelled = false;
    getSmogonBuildOptions(value.pokemonId, { generation: selectedGeneration }).then((meta) => {
      if (!cancelled) {
        setBuildOptions((prev) => ({
          generations: prev.generations || [],
          formats: meta?.formats || [],
        }));
      }
    }).catch(() => {
      if (!cancelled) {
        setBuildOptions((prev) => ({
          generations: prev.generations || [],
          formats: [],
        }));
      }
    });

    getSmogonBuilds(value.pokemonId, { generation: selectedGeneration }).then((rows) => {
      if (!cancelled) {
        setBuilds(rows || []);
        setSelectedBuildId("");
      }
    }).catch(() => {
      if (!cancelled) setBuilds([]);
    });

    return () => { cancelled = true; };
  }, [value.pokemonId, selectedGeneration]);

  function handleFormSwitch(formId) {
    if (formId === activeFormId) return;
    setActiveFormId(formId);
    // Load details for the selected form and update parent state
    getPokemonDetails(formId).then((d) => {
      setDetails(d);
      onEggGroupsChange && onEggGroupsChange(d.is_ditto ? [] : (d.egg_groups || []));
      onChange({ ...value, pokemonId: formId, ability: null, abilityHidden: false });
    }).catch(() => {});
  }

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
      gender: null,
    });
  }

  function handleClear() {
    setNotFoundQuery(null);
    setDetails(null);
    setForms([]);
    setActiveFormId(null);
    setBuilds([]);
    setBuildOptions({ generations: [], formats: [] });
    setSelectedGeneration("");
    setSelectedFormatName("");
    setSelectedBuildId("");
    update({ pokemonId: null, nature: null, ability: null, abilityHidden: false, gender: null });
  }

  function handleNotFound(query) {
    if (query === null) {
      setNotFoundQuery(null);
    } else {
      setNotFoundQuery(query);
      setDetails(null);
      update({ pokemonId: null, nature: null, ability: null, abilityHidden: false, gender: null });
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

  function handleBuildSelect(buildId) {
    setSelectedBuildId(buildId);
    const build = builds.find((b) => String(b.id) === String(buildId));
    if (!build) return;

    const selectedAbility = (details?.abilities || []).find((a) => a.name === build.ability);
    update({
      nature: build.nature || value.nature,
      ability: build.ability || value.ability,
      abilityHidden: selectedAbility ? !!selectedAbility.is_hidden : !!build.requires_hidden_ability,
    });

    if (onBuildApply) {
      onBuildApply(build, value.pokemonId);
    }
  }

  const selectedBuild = builds.find((b) => String(b.id) === String(selectedBuildId));
  const generationOptions = (buildOptions?.generations || []).filter(Boolean);
  const formatOptions = (buildOptions?.formats || []).filter(Boolean);
  const hasSmogonMeta = generationOptions.length > 0;
  const filteredBuilds = (builds || []).filter((b) => {
    if (selectedGeneration && b.generation !== selectedGeneration) return false;
    if (selectedFormatName && b.format_name !== selectedFormatName) return false;
    return true;
  });

  function fmtBoolIv(v) {
    return v ? "31" : "x";
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

      {/* Unbreedable warning — red tag */}
      {details && !details.is_breedable && (
        <div className="breed-warning">
          <span className="breed-warning-icon">⚠</span>
          <span className="breed-warning-text">
            {details.is_baby
              ? t("reasonBaby")
              : details.is_legendary
                ? t("reasonLegendary")
                : details.is_mythical
                  ? t("reasonMythical")
                  : t("reasonUndiscovered")}
          </span>
        </div>
      )}

      {/* Regional form selector — shown when forms exist */}
      {details && forms.length > 1 && (
        <div className="form-selector">
          <label className="form-selector-label">{t("regionLabel")}</label>
          <div className="form-btns">
            {forms.map((f) => (
              <button
                key={f.id}
                type="button"
                className={`form-btn${activeFormId === f.id ? " active" : ""}`}
                onClick={() => handleFormSwitch(f.id)}
                title={f.name}
              >
                {f.form_name ? formatRegion(f.form_name) : t("regionBase")}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Smogon template selector */}
      {details && (
        <div className="field">
          <label>{t("sampleBuild")}</label>
          {hasSmogonMeta ? (
            <>
              <label className="mini-label">{t("generationLabel")}</label>
              <select
                value={selectedGeneration}
                onChange={(e) => {
                  setSelectedGeneration(e.target.value);
                  setSelectedFormatName("");
                  setSelectedBuildId("");
                }}
              >
                <option value="">{t("selectGeneration")}</option>
                {generationOptions.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>

              <label className="mini-label">{t("formatLabel")}</label>
              <select
                value={selectedFormatName}
                onChange={(e) => {
                  setSelectedFormatName(e.target.value);
                  setSelectedBuildId("");
                }}
                disabled={!selectedGeneration}
              >
                <option value="">{t("selectFormat")}</option>
                {formatOptions.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>

              <label className="mini-label">{t("sampleBuild")}</label>
              <select
                value={selectedBuildId}
                onChange={(e) => handleBuildSelect(e.target.value)}
                disabled={!selectedGeneration || !selectedFormatName}
              >
                <option value="">{t("selectSampleBuild")}</option>
                {filteredBuilds.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.build_name}
                  </option>
                ))}
              </select>

              {selectedGeneration && selectedFormatName && filteredBuilds.length === 0 && (
                <div className="build-seed-hint">{t("sampleBuildNoMatchHint")}</div>
              )}

              {selectedBuild && (
                <div className="build-preview-card">
                  <div className="build-preview-head">
                    <strong>{selectedBuild.build_name}</strong>
                    <span className="build-preview-format">{selectedBuild.format}</span>
                  </div>

                  <div className="build-preview-meta">
                    <span><b>{t("nature")}:</b> {selectedBuild.nature || "-"}</span>
                    <span>
                      <b>{t("ability")}:</b> {selectedBuild.ability || "-"}
                      {selectedBuild.requires_hidden_ability ? ` (${t("hiddenAbility")})` : ""}
                    </span>
                    <span><b>{t("heldItem")}:</b> {selectedBuild.item || "-"}</span>
                  </div>

                  {Array.isArray(selectedBuild.moves) && selectedBuild.moves.length > 0 && (
                    <div className="build-preview-row">
                      <span className="build-preview-label">{t("movesLabel")}</span>
                      <div className="build-preview-tags">
                        {selectedBuild.moves.map((m) => (
                          <span key={`${selectedBuild.id}-${m}`} className="build-chip">{m}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {Array.isArray(selectedBuild.target_ivs) && selectedBuild.target_ivs.length === 6 && (
                    <div className="build-preview-row">
                      <span className="build-preview-label">{t("targetIvs")}</span>
                      <div className="build-preview-tags">
                        {STAT_NAMES.map((s, i) => (
                          <span key={`${selectedBuild.id}-iv-${s}`} className="build-chip iv-chip">
                            {s}: {fmtBoolIv(selectedBuild.target_ivs[i])}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="build-seed-hint">{t("sampleBuildEmptyHint")}</div>
          )}
        </div>
      )}

      {/* Gender selector — shown for non-genderless, non-Ditto Pokemon */}
      {details && details.gender_rate >= 0 && !details.is_ditto && (
        <div className="gender-selector">
          <label className="gender-selector-label">{t("genderLabel")}</label>
          <div className="gender-btns">
            <button
              type="button"
              className={`gender-btn gender-btn-male${value.gender === "male" ? " active" : ""}`}
              onClick={() => update({ gender: value.gender === "male" ? null : "male" })}
              disabled={details.gender_rate === 100}
              title={details.gender_rate === 100 ? t("femaleOnly") : "♂"}
            >
              ♂
            </button>
            <button
              type="button"
              className={`gender-btn gender-btn-female${value.gender === "female" ? " active" : ""}`}
              onClick={() => update({ gender: value.gender === "female" ? null : "female" })}
              disabled={details.gender_rate === 0}
              title={details.gender_rate === 0 ? t("maleOnly") : "♀"}
            >
              ♀
            </button>
          </div>
          <span className="gender-note">{t("genderNote")}</span>
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
