import React, { useState, useEffect, useRef } from "react";
import { searchPokemon } from "../api";

/**
 * PokemonSearch — Debounced autocomplete search input.
 *
 * Props:
 *   onSelect(pokemon)  — called when user picks a result { id, name, sprite_url }
 *   placeholder        — input placeholder text
 */
export default function PokemonSearch({ onSelect, placeholder = "Search Pokemon..." }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapperRef = useRef(null);
  const timerRef = useRef(null);

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

  // Debounced search
  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      const data = await searchPokemon(query);
      setResults(data);
      setOpen(data.length > 0);
      setLoading(false);
    }, 300);
    return () => clearTimeout(timerRef.current);
  }, [query]);

  function pick(pokemon) {
    setQuery(pokemon.name);
    setOpen(false);
    onSelect(pokemon);
  }

  return (
    <div className="search-wrapper" ref={wrapperRef}>
      <input
        type="text"
        className="search-input"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder={placeholder}
        autoComplete="off"
      />
      {loading && <span className="search-spinner">...</span>}
      {open && (
        <ul className="search-dropdown">
          {results.map((p) => (
            <li key={p.id} onClick={() => pick(p)} className="search-item">
              {p.sprite_url && (
                <img src={p.sprite_url} alt={p.name} className="search-sprite" />
              )}
              <span className="search-name">
                #{p.id} {p.name}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
