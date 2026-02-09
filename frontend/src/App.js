import React, { useState, useEffect } from "react";
import ParentPanel from "./components/ParentPanel";
import ResultsPanel from "./components/ResultsPanel";
import { calculateBreeding, getNatures } from "./api";
import { useLanguage } from "./i18n";
import "./App.css";

const EMPTY_PARENT = {
  pokemonId: null,
  ivs: [true, true, true, true, true, true],
  heldItem: "none",
  nature: null,
  ability: null,
  abilityHidden: false,
};

function App() {
  const { t, lang, setLang } = useLanguage();
  const [parentA, setParentA] = useState({ ...EMPTY_PARENT });
  const [parentB, setParentB] = useState({ ...EMPTY_PARENT });
  const [targetIvs, setTargetIvs] = useState([true, true, true, true, true, true]);
  const [natures, setNatures] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch natures once on mount
  useEffect(() => {
    getNatures().then(setNatures).catch(() => {});
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
      };
      const data = await calculateBreeding(payload);
      setResults(data);
    } catch (err) {
      setError(err.message || t("calcFailed"));
    } finally {
      setLoading(false);
    }
  }

  function toggleLang() {
    setLang(lang === "en" ? "vi" : "en");
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-row">
          <div className="header-text">
            <h1>{t("title")}</h1>
            <p className="subtitle">{t("subtitle")}</p>
          </div>
          <button className="btn-lang" onClick={toggleLang} title={t("langToggle")}>
            {lang === "en" ? "🇻🇳 VI" : "🇬🇧 EN"}
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="app-main">
        {/* Parent panels side by side */}
        <section className="parents-row">
          <ParentPanel
            label={t("parentA")}
            value={parentA}
            onChange={setParentA}
            natures={natures}
          />
          <div className="parents-divider">
            <span className="divider-icon">x</span>
          </div>
          <ParentPanel
            label={t("parentB")}
            value={parentB}
            onChange={setParentB}
            natures={natures}
          />
        </section>

        {/* Target IVs — desired offspring spread */}
        <TargetIvsSection targetIvs={targetIvs} setTargetIvs={setTargetIvs} />

        {/* Calculate */}
        <section className="action-row">
          <button
            className="btn-calculate"
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
          Made by <strong>@DaoTacVoSi</strong> | GitHub: <a href="https://github.com/NguyenThanhDuy42124" target="_blank" rel="noopener noreferrer">NguyenThanhDuy42124</a>
        </p>
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
