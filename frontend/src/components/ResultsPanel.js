import React, { useState } from "react";
import { useLanguage } from "../i18n";

/**
 * ResultsPanel — Displays breeding calculation results.
 *
 * Props:
 *   results   — BreedingResponse from the API (or null)
 *   loading   — boolean
 *   error     — error string (or null)
 */
export default function ResultsPanel({ results, loading, error }) {
  const { t } = useLanguage();
  const [expandedRow, setExpandedRow] = useState(null);

  if (loading) {
    return (
      <div className="results-panel">
        <div className="results-loading">{t("calculatingProbs")}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results-panel">
        <div className="results-error">{error}</div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="results-panel results-empty">
        <p dangerouslySetInnerHTML={{ __html: t("selectParentsPrompt") }} />
      </div>
    );
  }

  const { parent_a, parent_b, held_item_a, held_item_b, inherited_count, results: rows, nature_info, ability_info, target_iv_result } = results;

  return (
    <div className="results-panel">
      <h3>{t("breedingResults")}</h3>

      {/* Summary */}
      <div className="results-summary">
        <span className="summary-parents">
          <strong>{parent_a}</strong> x <strong>{parent_b}</strong>
        </span>
        <span className="summary-items">
          {t("items")}: {formatItem(held_item_a)} / {formatItem(held_item_b)}
        </span>
        <span className="summary-inherited">
          {t("ivsInherited", { count: inherited_count })}
        </span>
      </div>

      {/* IV Probability Table */}
      <div className="results-table-wrapper">
        <table className="results-table">
          <thead>
            <tr>
              <th>{t("perfectIvsCol")}</th>
              <th>{t("probability")}</th>
              <th>{t("approxEggs")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const eggs = row.probability > 0 ? Math.ceil(1 / row.probability) : "---";
              const isExpanded = expandedRow === row.perfect_iv_count;
              return (
                <React.Fragment key={row.perfect_iv_count}>
                  <tr
                    className={`result-row ${isExpanded ? "expanded" : ""}`}
                    onClick={() => setExpandedRow(isExpanded ? null : row.perfect_iv_count)}
                  >
                    <td className="iv-count-cell">
                      <span className="iv-count">{row.perfect_iv_count}</span>
                      <span className="iv-count-label">/ 6</span>
                    </td>
                    <td className="prob-cell">
                      <div className="prob-bar-bg">
                        <div
                          className="prob-bar"
                          style={{ width: `${Math.min(row.probability * 100, 100)}%` }}
                        />
                      </div>
                      <span className="prob-text">{row.percentage}</span>
                    </td>
                    <td className="eggs-cell">~{eggs}</td>
                    <td className="expand-cell">{isExpanded ? "▲" : "▼"}</td>
                  </tr>
                  {isExpanded && (
                    <tr className="explanation-row">
                      <td colSpan={4}>
                        <pre className="explanation-text">{row.explanation}</pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Target IV Result */}
      {target_iv_result && (
        <div className="info-card target-iv-card">
          <h4>{t("targetIvResult")}</h4>
          <div className="target-iv-summary">
            <span className="target-stat-tags">
              {t("targetStats")}:{" "}
              {target_iv_result.target_stats.map((s, i) => (
                <span key={s} className="stat-tag">{s}</span>
              ))}
            </span>
          </div>
          <div className="target-iv-prob-row">
            <div className="target-iv-main-prob">
              <span className="target-prob-value">{target_iv_result.percentage}</span>
              <span className="target-prob-label">{t("targetExact")}</span>
            </div>
            <div className="target-iv-eggs">
              <span className="target-eggs-value">~{target_iv_result.eggs_estimate}</span>
              <span className="target-eggs-label">{t("approxEggs")}</span>
            </div>
            {(() => {
              const generalRow = rows.find(r => r.perfect_iv_count === target_iv_result.target_count);
              if (generalRow) {
                return (
                  <div className="target-iv-compare">
                    <span className="target-compare-value">{generalRow.percentage}</span>
                    <span className="target-compare-label">
                      {t("vsGeneral", { count: target_iv_result.target_count })}
                    </span>
                  </div>
                );
              }
              return null;
            })()}
          </div>
          <pre className="explanation-text">{target_iv_result.explanation}</pre>
        </div>
      )}

      {/* Nature Info */}
      {nature_info && (
        <div className="info-card nature-card">
          <h4>{t("natureInheritance")}</h4>
          {nature_info.inherited_nature ? (
            <p>
              <strong>{nature_info.inherited_nature}</strong> {t("natureWord")}
              {nature_info.from_parent && ` (${t("fromParent", { parent: nature_info.from_parent })})`}
              {" "}— {(nature_info.probability * 100).toFixed(0)}% {t("chance")}
            </p>
          ) : (
            <p>{t("randomNature")}</p>
          )}
          <p className="info-explanation">{nature_info.explanation}</p>
        </div>
      )}

      {/* Ability Info */}
      {ability_info && (
        <div className="info-card ability-card">
          <h4>{t("abilityInheritance")}</h4>
          {ability_info.ability_name ? (
            <p>
              <strong>{ability_info.ability_name}</strong>
              {ability_info.is_hidden && ` (${t("hidden")})`}
              {" "}— {(ability_info.probability * 100).toFixed(0)}% {t("chance")}
            </p>
          ) : (
            <p>{t("noAbilitySelected")}</p>
          )}
          <p className="info-explanation">{ability_info.explanation}</p>
        </div>
      )}
    </div>
  );
}

function formatItem(item) {
  if (!item || item === "none") return "None";
  return item
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
