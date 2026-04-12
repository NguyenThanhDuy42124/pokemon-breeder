import React, { useState, useEffect, useCallback, useRef } from "react";
import ParentPanel from "./components/ParentPanel";
import ResultsPanel from "./components/ResultsPanel";
import TipsPanel from "./components/TipsPanel";
import { calculateBreeding, getNatures, getServerStatus, getBreedingRoadmap, getSmogonSyncStatus } from "./api";
import { useLanguage } from "./i18n";
import "./App.css";

const EMPTY_PARENT = {
  pokemonId: null,
  ivs: [true, true, true, true, true, true],
  heldItem: "none",
  nature: null,
  ability: null,
  abilityHidden: false,
  gender: null,
};

function App() {
  const { t, lang, setLang } = useLanguage();

  // Theme: persist in localStorage
  const [theme, setTheme] = useState(() =>
    localStorage.getItem("pokemon-breeder-theme") || "dark"
  );
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("pokemon-breeder-theme", theme);
  }, [theme]);

  // Tips sidebar: persist open/closed state
  const [tipsOpen, setTipsOpen] = useState(() =>
    localStorage.getItem("pokemon-breeder-tips") !== "closed"
  );
  useEffect(() => {
    localStorage.setItem("pokemon-breeder-tips", tipsOpen ? "open" : "closed");
  }, [tipsOpen]);

  const [parentA, setParentA] = useState({ ...EMPTY_PARENT });
  const [parentB, setParentB] = useState({ ...EMPTY_PARENT });
  const [targetIvs, setTargetIvs] = useState([true, true, true, true, true, true]);
  const [natures, setNatures] = useState([]);
  const [results, setResults] = useState(null);
  const [selectedBuild, setSelectedBuild] = useState(null);
  const [selectedBuildPokemonId, setSelectedBuildPokemonId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Egg group locking: when one parent is selected, lock the other to compatible egg groups
  const [parentAEggGroups, setParentAEggGroups] = useState([]);
  const [parentBEggGroups, setParentBEggGroups] = useState([]);

  const handleParentAEggGroups = useCallback((groups) => setParentAEggGroups(groups), []);
  const handleParentBEggGroups = useCallback((groups) => setParentBEggGroups(groups), []);

  // Fetch natures once on mount
  useEffect(() => {
    getNatures().then(setNatures).catch(() => {});
  }, []);

  // Server restart detection: poll /api/server/status every 30s
  const [serverBanner, setServerBanner] = useState(null); // { type, message }
  const knownStartedAt = useRef(null);
  const [smogonSync, setSmogonSync] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function checkServer() {
      try {
        const status = await getServerStatus();
        if (!status || !mounted) return;

        if (knownStartedAt.current === null) {
          // First check — just record the startup time
          knownStartedAt.current = status.started_at;
        } else if (status.started_at !== knownStartedAt.current) {
          // Server restarted!
          knownStartedAt.current = status.started_at;
          setServerBanner({
            type: "restart",
            message: lang === "vi"
              ? `⚡ Server đã khởi động lại và cập nhật lúc ${new Date(status.started_at + "Z").toLocaleTimeString()}.  Tải lại trang để nhận bản mới nhất!`
              : `⚡ Server restarted & updated at ${new Date(status.started_at + "Z").toLocaleTimeString()}. Reload for the latest version!`,
          });
          // Auto-dismiss after 15s
          setTimeout(() => { if (mounted) setServerBanner(null); }, 15000);
        }
      } catch {
        // Server unreachable — show offline banner
        if (mounted && knownStartedAt.current !== null) {
          setServerBanner({
            type: "offline",
            message: lang === "vi"
              ? "🔄 Server đang khởi động lại, vui lòng đợi..."
              : "🔄 Server is restarting, please wait...",
          });
        }
      }
    }

    checkServer();
    const interval = setInterval(checkServer, 30000); // every 30s
    return () => { mounted = false; clearInterval(interval); };
  }, [lang]);

  useEffect(() => {
    let mounted = true;

    async function loadSyncStatus() {
      try {
        const payload = await getSmogonSyncStatus();
        if (mounted) setSmogonSync(payload);
      } catch {
        if (mounted) setSmogonSync(null);
      }
    }

    loadSyncStatus();
    const interval = setInterval(loadSyncStatus, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  async function handleCalculate() {
    if (!parentA.pokemonId || !parentB.pokemonId) {
      setError(t("selectBothParents"));
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const payload = {
        parent_a_id: parentA.pokemonId,
        parent_b_id: parentB.pokemonId,
        parent_a_ivs: parentA.ivs,
        parent_b_ivs: parentB.ivs,
        held_item_a: parentA.heldItem,
        held_item_b: parentB.heldItem,
        parent_a_nature: parentA.nature,
        parent_b_nature: parentB.nature,
        parent_a_ability: parentA.ability,
        parent_b_ability: parentB.ability,
        parent_a_ability_hidden: parentA.abilityHidden,
        parent_b_ability_hidden: parentB.abilityHidden,
        breeding_with_ditto: parentA.pokemonId === 132 || parentB.pokemonId === 132,
        target_ivs: targetIvs,
        lang: lang,
        parent_a_gender: parentA.gender,
        parent_b_gender: parentB.gender,
      };
      const data = await calculateBreeding(payload);

      let roadmapSteps = [];
      try {
        const plannerPayload = {
          pokemon_id: selectedBuildPokemonId || data.offspring_id || parentA.pokemonId,
          parent_a_id: parentA.pokemonId,
          parent_b_id: parentB.pokemonId,
          parent_a_ivs: parentA.ivs,
          parent_b_ivs: parentB.ivs,
          target_nature: selectedBuild?.nature || null,
          target_ability: selectedBuild?.ability || null,
          target_ivs: targetIvs,
          target_moves: selectedBuild?.moves || [],
          requires_hidden_ability: !!selectedBuild?.requires_hidden_ability,
          generation: selectedBuild?.generation || null,
          lang,
        };
        const roadmap = await getBreedingRoadmap(plannerPayload);
        roadmapSteps = roadmap?.steps || [];
      } catch {
        roadmapSteps = [];
      }

      setResults({ ...data, planner_steps: roadmapSteps });
    } catch (err) {
      setError(err.message || t("calcFailed"));
    } finally {
      setLoading(false);
    }
  }

  function handleBuildApply(build, pokemonId) {
    setSelectedBuild(build || null);
    setSelectedBuildPokemonId(pokemonId || null);
    if (build?.target_ivs && Array.isArray(build.target_ivs) && build.target_ivs.length === 6) {
      setTargetIvs(build.target_ivs);
    }
  }

  function toggleLang() {
    setLang(lang === "en" ? "vi" : "en");
  }

  function toggleTheme() {
    setTheme(prev => (prev === "dark" ? "light" : "dark"));
  }

  const bothSelected = parentA.pokemonId && parentB.pokemonId;

  return (
    <div className={`app ${tipsOpen ? 'tips-open' : ''}`}>
      <TipsPanel isOpen={tipsOpen} onToggle={() => setTipsOpen(!tipsOpen)} />

      {/* Header */}
      <header className="app-header">
        <div className="header-row">
          <div className="header-text">
            <h1>{t("title")}</h1>
            <p className="subtitle">{t("subtitle")}</p>
          </div>
          <div className="header-buttons">
            <button className="btn-theme" onClick={toggleTheme} title={t("themeToggle")}>
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            <button className="btn-lang" onClick={toggleLang} title={t("langToggle")}>
              {lang === "en" ? "🇻🇳 VI" : "🇬🇧 EN"}
            </button>
          </div>
        </div>
      </header>

      {/* Server restart/update notification banner */}
      {serverBanner && (
        <div className={`server-banner server-banner-${serverBanner.type}`}>
          <span>{serverBanner.message}</span>
          {serverBanner.type === "restart" && (
            <button className="server-banner-btn" onClick={() => window.location.reload()}>
              {lang === "vi" ? "Tải lại" : "Reload"}
            </button>
          )}
          <button className="server-banner-close" onClick={() => setServerBanner(null)}>✕</button>
        </div>
      )}

      {/* Main content */}
      <main className="app-main">
        {smogonSync && (
          <section className="admin-sync-card">
            <div className="admin-sync-head">
              <h3>Smogon Sync Status</h3>
              <span className="admin-sync-meta">
                {smogonSync.success_formats}/{smogonSync.total_formats} formats
              </span>
            </div>

            <div className="admin-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round((smogonSync.success_formats / Math.max(smogonSync.total_formats || 1, 1)) * 100)}>
              <div
                className="admin-progress-fill"
                style={{ width: `${(smogonSync.success_formats / Math.max(smogonSync.total_formats || 1, 1)) * 100}%` }}
              />
            </div>

            <div className="admin-sync-grid">
              <span>Records: <b>{smogonSync.smogon_build_records}</b></span>
              <span>Success: <b>{smogonSync.success_formats}</b></span>
              <span>Pending: <b>{smogonSync.pending_formats}</b></span>
              <span>Failed: <b>{smogonSync.failed_formats}</b></span>
            </div>

            {smogonSync.last_updated_at && (
              <div className="admin-sync-updated">
                Last update: {new Date(smogonSync.last_updated_at + "Z").toLocaleString()}
              </div>
            )}

            {Array.isArray(smogonSync.by_generation) && smogonSync.by_generation.length > 0 && (
              <div className="admin-sync-tags">
                {smogonSync.by_generation.map((row) => (
                  <span key={row.generation} className="admin-sync-tag">
                    {row.generation}: {row.synced_formats}
                  </span>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Parent panels side by side */}
        <section className="parents-row">
          <ParentPanel
            label={t("parentA")}
            value={parentA}
            onChange={setParentA}
            natures={natures}
            lockedEggGroups={parentBEggGroups}
            onEggGroupsChange={handleParentAEggGroups}
            onBuildApply={handleBuildApply}
          />
          <div className="parents-divider">
            <span className="divider-icon">x</span>
          </div>
          <ParentPanel
            label={t("parentB")}
            value={parentB}
            onChange={setParentB}
            natures={natures}
            lockedEggGroups={parentAEggGroups}
            onEggGroupsChange={handleParentBEggGroups}
            onBuildApply={handleBuildApply}
          />
        </section>

        {/* Target IVs — desired offspring spread */}
        <TargetIvsSection targetIvs={targetIvs} setTargetIvs={setTargetIvs} />

        {/* Calculate */}
        <section className="action-row">
          <button
            className={`btn-calculate${bothSelected && !loading ? ' ready' : ''}`}
            onClick={handleCalculate}
            disabled={loading}
          >
            {loading ? t("calculating") : t("calculate")}
          </button>
        </section>

        {/* Results */}
        <section className="results-section">
          <ResultsPanel results={results} loading={loading} error={error} />
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>{t("footer")}</p>
        <p className="footer-credits">
          Made by <strong>@DaoTacVoSi05</strong> | GitHub: <a href="https://github.com/NguyenThanhDuy42124" target="_blank" rel="noopener noreferrer">NguyenThanhDuy42124</a>
        </p>
        <div className="footer-links">
        </div>
      </footer>
    </div>
  );
}

export default App;

const STAT_NAMES = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"];

function TargetIvsSection({ targetIvs, setTargetIvs }) {
  const { t } = useLanguage();

  function toggleIv(index) {
    const next = [...targetIvs];
    next[index] = !next[index];
    setTargetIvs(next);
  }

  function setAll(val) {
    setTargetIvs([val, val, val, val, val, val]);
  }

  return (
    <section className="target-ivs-section">
      <div className="target-ivs-header">
        <h3>{t("targetIvs")}</h3>
        <span className="target-ivs-hint">{t("targetIvsHint")}</span>
      </div>
      <div className="target-ivs-body">
        <div className="iv-quick-btns">
          <button type="button" onClick={() => setAll(true)} className="btn-mini">{t("all")}</button>
          <button type="button" onClick={() => setAll(false)} className="btn-mini">{t("none")}</button>
        </div>
        <div className="iv-grid iv-grid-target">
          {STAT_NAMES.map((stat, i) => (
            <label key={stat} className={`iv-checkbox ${targetIvs[i] ? "checked" : ""}`}>
              <input
                type="checkbox"
                checked={targetIvs[i]}
                onChange={() => toggleIv(i)}
              />
              <span className="iv-label">{stat}</span>
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}
