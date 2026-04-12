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

// ─── Pokemon Forms (regional variants) ───────────────────
export async function getPokemonForms(id) {
  const res = await fetch(`${BASE}/api/pokemon/${id}/forms`);
  if (!res.ok) return [];
  return res.json();
}

// ─── Smogon Build Templates (seeded local data) ───────────
export async function getSmogonBuilds(id, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== "") qs.set(k, v);
  });
  const res = await fetch(`${BASE}/api/pokemon/${id}/smogon-builds?${qs.toString()}`);
  if (!res.ok) return [];
  return res.json();
}

export async function getSmogonBuildOptions(id, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== "") qs.set(k, v);
  });
  const res = await fetch(`${BASE}/api/pokemon/${id}/smogon-options?${qs.toString()}`);
  if (!res.ok) return { generations: [], formats: [] };
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

// ─── Rule-based Breeding Planner ─────────────────────────
export async function getBreedingRoadmap(payload) {
  const res = await fetch(`${BASE}/api/planner/roadmap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Planner failed");
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

// ─── Browse Pokemon (advanced search with filters) ───────
export async function browsePokemon(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== "") qs.set(k, v);
  });
  const res = await fetch(`${BASE}/api/pokemon/browse?${qs.toString()}`);
  if (!res.ok) return { total: 0, pokemon: [] };
  return res.json();
}

// ─── Server Status (for restart detection) ───────────────
export async function getServerStatus() {
  const res = await fetch(`${BASE}/api/server/status`);
  if (!res.ok) return null;
  return res.json();
}

// ─── Smogon Sync Status (admin) ──────────────────────────
export async function getSmogonSyncStatus() {
  const res = await fetch(`${BASE}/api/admin/smogon-sync-status`);
  if (!res.ok) return null;
  return res.json();
}
