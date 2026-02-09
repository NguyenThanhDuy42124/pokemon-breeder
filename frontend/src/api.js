/**
 * api.js — Backend API service layer.
 *
 * Every function here maps to one FastAPI endpoint.
 * In development: REACT_APP_API_URL=http://localhost:8000
 * In production: empty string (same origin, FastAPI serves both API + frontend)
 */

const BASE = process.env.REACT_APP_API_URL || "";

// ─── Pokemon Search (autocomplete) ───────────────────────
export async function searchPokemon(query) {
  if (!query || query.length < 2) return [];
  const res = await fetch(`${BASE}/api/pokemon/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  return res.json();
}

// ─── Pokemon Details ─────────────────────────────────────
export async function getPokemonDetails(id) {
  const res = await fetch(`${BASE}/api/pokemon/${id}`);
  if (!res.ok) throw new Error("Pokemon not found");
  return res.json();
}

// ─── Compatible Breeding Partners ────────────────────────
export async function getCompatiblePartners(id) {
  const res = await fetch(`${BASE}/api/pokemon/${id}/compatible`);
  if (!res.ok) return [];
  return res.json();
}

// ─── Calculate Breeding Probabilities ────────────────────
export async function calculateBreeding(payload) {
  const res = await fetch(`${BASE}/api/breeding/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Calculation failed");
  }
  return res.json();
}

// ─── Natures (for Everstone dropdown) ────────────────────
export async function getNatures() {
  const res = await fetch(`${BASE}/api/natures`);
  if (!res.ok) return [];
  return res.json();
}

// ─── Egg Groups (reference) ──────────────────────────────
export async function getEggGroups() {
  const res = await fetch(`${BASE}/api/egg-groups`);
  if (!res.ok) return [];
  return res.json();
}
