import React, { useState, useEffect } from "react";
import { browsePokemon, getEggGroups } from "../api";
import { useLanguage } from "../i18n";

const REGIONS = [
  { value: "", labelEn: "All Regions", labelVi: "Tất cả vùng" },
  { value: "kanto", labelEn: "Kanto (Gen 1)", labelVi: "Kanto (Gen 1)" },
  { value: "johto", labelEn: "Johto (Gen 2)", labelVi: "Johto (Gen 2)" },
  { value: "hoenn", labelEn: "Hoenn (Gen 3)", labelVi: "Hoenn (Gen 3)" },
  { value: "sinnoh", labelEn: "Sinnoh (Gen 4)", labelVi: "Sinnoh (Gen 4)" },
  { value: "unova", labelEn: "Unova (Gen 5)", labelVi: "Unova (Gen 5)" },
  { value: "kalos", labelEn: "Kalos (Gen 6)", labelVi: "Kalos (Gen 6)" },
  { value: "alola", labelEn: "Alola (Gen 7)", labelVi: "Alola (Gen 7)" },
  { value: "galar", labelEn: "Galar (Gen 8)", labelVi: "Galar (Gen 8)" },
  { value: "paldea", labelEn: "Paldea (Gen 9)", labelVi: "Paldea (Gen 9)" },
];

const PAGE_SIZE = 48;

/**
 * AdvancedSearchPanel — Full-screen modal for browsing & filtering all Pokémon.
 *
 * Props:
 *   open               — boolean, whether the panel is visible
 *   onClose()          — close callback
 *   onSelect(pokemon)  — pick callback { id, name, sprite_url }
 *   lockedEggGroups    — array of { id, name } from the partner's selected Pokémon
 */
export default function AdvancedSearchPanel({ open, onClose, onSelect, lockedEggGroups }) {
  const { t, lang } = useLanguage();
  const [name, setName] = useState("");
  const [eggGroupId, setEggGroupId] = useState("");
  const [region, setRegion] = useState("");
  const [eggGroups, setEggGroups] = useState([]);
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);

  // Fetch egg groups once
  useEffect(() => {
    getEggGroups().then(setEggGroups).catch(() => {});
  }, []);

  // Reset page when filters change
  useEffect(() => {
    setPage(0);
  }, [name, eggGroupId, region]);

  // Debounced fetch when any filter or page changes
  useEffect(() => {
    if (!open) return;

    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const params = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
        if (name.trim()) params.name = name.trim();
        if (eggGroupId) params.egg_group_id = eggGroupId;
        if (region) params.region = region;
        if (lockedEggGroups && lockedEggGroups.length > 0) {
          params.egg_group_ids = lockedEggGroups.map((g) => g.id).join(",");
        }
        const data = await browsePokemon(params);
        setResults(data.pokemon || []);
        setTotal(data.total || 0);
      } catch {
        setResults([]);
        setTotal(0);
      }
      setLoading(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [name, eggGroupId, region, page, open, lockedEggGroups]);

  // Reset filters when panel opens
  useEffect(() => {
    if (open) {
      setName("");
      setEggGroupId("");
      setRegion("");
      setPage(0);
    }
  }, [open]);

  if (!open) return null;

  function handleSelect(pokemon) {
    onSelect(pokemon);
    onClose();
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="advanced-panel-overlay" onClick={onClose}>
      <div className="advanced-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="advanced-panel-header">
          <h3>{t("browsePokemon")}</h3>
          <button className="advanced-panel-close" onClick={onClose}>✕</button>
        </div>

        {/* Egg group lock notice */}
        {lockedEggGroups && lockedEggGroups.length > 0 && (
          <div className="egg-lock-notice">
            🔒 {t("eggGroupLocked")}: {lockedEggGroups.map((g) => g.name).join(", ")}
          </div>
        )}

        {/* Filters row */}
        <div className="advanced-filters">
          <input
            type="text"
            className="advanced-search-input"
            placeholder={t("searchByName")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <select
            className="advanced-select"
            value={eggGroupId}
            onChange={(e) => setEggGroupId(e.target.value)}
          >
            <option value="">{t("allEggGroups")}</option>
            {eggGroups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
          <select
            className="advanced-select"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
          >
            {REGIONS.map((r) => (
              <option key={r.value} value={r.value}>
                {lang === "vi" ? r.labelVi : r.labelEn}
              </option>
            ))}
          </select>
        </div>

        {/* Results count */}
        <div className="advanced-results-info">
          {t("showingResults", { count: results.length, total })}
        </div>

        {/* Results grid */}
        <div className="advanced-results">
          {loading ? (
            <div className="advanced-loading">{t("loading")}</div>
          ) : results.length === 0 ? (
            <div className="advanced-not-found">{t("notFoundInDb")}</div>
          ) : (
            <div className="advanced-grid">
              {results.map((p) => (
                <div
                  key={p.id}
                  className="advanced-item"
                  onClick={() => handleSelect(p)}
                >
                  {p.sprite_url && (
                    <img
                      src={p.sprite_url}
                      alt={p.name}
                      className="advanced-sprite"
                    />
                  )}
                  <span className="advanced-id">#{p.id}</span>
                  <span className="advanced-name-text">{p.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="advanced-pagination">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="advanced-page-btn"
            >
              ← {t("prev") || "Prev"}
            </button>
            <span className="advanced-page-info">
              {page + 1} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className="advanced-page-btn"
            >
              {t("next") || "Next"} →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
