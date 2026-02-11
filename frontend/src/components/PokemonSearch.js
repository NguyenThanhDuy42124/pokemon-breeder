import React, { useState, useEffect, useRef, useCallback } from "react";
import { browsePokemon } from "../api";
import { useLanguage } from "../i18n";

/**
 * PokemonSearch — Modern search with instant dropdown + browse button.
 *
 * Props:
 *   onSelect(pokemon)   — called when user picks a result { id, name, sprite_url }
 *   onNotFound(query)   — called when no results found on Enter
 *   placeholder         — input placeholder text
 *   lockedEggGroups     — array of { id, name } egg groups to filter by (from partner)
 *   onBrowseClick()     — called when the browse (☰) button is clicked
 */
export default function PokemonSearch({
  onSelect,
  onNotFound,
  placeholder = "Search Pokemon...",
  lockedEggGroups,
  onBrowseClick,
}) {
  const { t } = useLanguage();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const wrapperRef = useRef(null);
  const timerRef = useRef(null);
  const listRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClick(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Build search params respecting the egg group lock
  const buildParams = useCallback(
    (searchQuery) => {
      const params = { limit: 20 };
      if (searchQuery && searchQuery.trim()) {
        params.name = searchQuery.trim();
      }
      if (lockedEggGroups && lockedEggGroups.length > 0) {
        params.egg_group_ids = lockedEggGroups.map((g) => g.id).join(",");
      }
      return params;
    },
    [lockedEggGroups]
  );

  // Fetch results from the browse API
  const fetchResults = useCallback(
    async (searchQuery) => {
      setLoading(true);
      try {
        const data = await browsePokemon(buildParams(searchQuery));
        setResults(data.pokemon || []);
        setOpen(true);
      } catch {
        setResults([]);
      }
      setLoading(false);
    },
    [buildParams]
  );

  // Debounced search on query change
  useEffect(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      fetchResults(query);
    }, 250);
    return () => clearTimeout(timerRef.current);
  }, [query, fetchResults]);

  // Re-fetch when egg group lock changes
  useEffect(() => {
    if (open) {
      fetchResults(query);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lockedEggGroups]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll(".search-item");
      if (items[highlightIndex]) {
        items[highlightIndex].scrollIntoView({ block: "nearest" });
      }
    }
  }, [highlightIndex]);

  function handleFocus() {
    if (results.length > 0) {
      setOpen(true);
    } else {
      fetchResults(query);
    }
  }

  function pick(pokemon) {
    setQuery(pokemon.name);
    setOpen(false);
    setHighlightIndex(-1);
    onSelect(pokemon);
  }

  function handleKeyDown(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) { setOpen(true); return; }
      setHighlightIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlightIndex >= 0 && results[highlightIndex]) {
        pick(results[highlightIndex]);
      } else if (results.length === 1) {
        pick(results[0]);
      } else if (results.length === 0 && onNotFound) {
        onNotFound(query);
        setOpen(false);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="search-wrapper" ref={wrapperRef}>
      <div className="search-input-row">
        <input
          type="text"
          className="search-input search-input-with-btn"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setHighlightIndex(-1);
            if (onNotFound) onNotFound(null);
          }}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
        />
        {loading && <span className="search-spinner-inline">⟳</span>}
        <button
          className="btn-browse"
          onClick={(e) => {
            e.preventDefault();
            onBrowseClick && onBrowseClick();
          }}
          title={t("browsePokemon")}
          type="button"
        >
          <span className="browse-icon">☰</span>
        </button>
      </div>

      {open && (
        <ul className="search-dropdown" ref={listRef}>
          {results.length === 0 ? (
            <li className="search-item search-not-found">
              <span className="search-name">{t("notFoundInDb")}</span>
            </li>
          ) : (
            results.map((p, idx) => (
              <li
                key={p.id}
                onClick={() => pick(p)}
                className={`search-item ${idx === highlightIndex ? "search-item-highlight" : ""}`}
              >
                {p.sprite_url && (
                  <img src={p.sprite_url} alt={p.name} className="search-sprite" />
                )}
                <span className="search-name">
                  #{p.id} {p.name}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
