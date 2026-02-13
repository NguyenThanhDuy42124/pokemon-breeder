/**
 * i18n.js — Internationalization (English + Vietnamese).
 *
 * Usage:
 *   import { useLanguage, LanguageProvider } from "./i18n";
 *   const { t, lang, setLang } = useLanguage();
 *   t("title")  // → "Pokemon Breeding Calculator" or "Máy Tính Lai Giống Pokemon"
 */

import React, { createContext, useContext, useState, useCallback } from "react";

// ══════════════════════════════════════════════════════════
// TRANSLATION DICTIONARIES
// ══════════════════════════════════════════════════════════

const translations = {
  en: {
    // Header
    title: "Pokemon Breeding Calculator",
    subtitle: "Gen 9 IV / Nature / Ability Inheritance",

    // Parent panels
    parentA: "Parent A",
    parentB: "Parent B",
    searchPlaceholder: "Search Pokemon...",
    searchParent: "Search {label}...",
    eggGroups: "Egg Groups",

    // IVs
    perfectIvs: "Perfect IVs (31)",
    all: "All",
    none: "None",

    // Held items
    heldItem: "Held Item",
    itemNone: "None",
    itemDestinyKnot: "Destiny Knot",
    itemEverstone: "Everstone",
    itemPowerHp: "Power Weight (HP)",
    itemPowerAtk: "Power Bracer (Atk)",
    itemPowerDef: "Power Belt (Def)",
    itemPowerSpa: "Power Lens (SpA)",
    itemPowerSpd: "Power Band (SpD)",
    itemPowerSpe: "Power Anklet (Spe)",

    // Nature
    nature: "Nature",
    everstoneActive: "Everstone active!",
    selectNature: "-- select nature --",
    neutral: "Neutral",

    // Ability
    ability: "Ability",
    hidden: "Hidden",
    hiddenAbility: "Hidden Ability",
    selectAbility: "-- select ability --",

    // Action row
    breedingWithDitto: "Breeding with Ditto",
    dittoHint: "(affects ability inheritance)",
    calculate: "Calculate",
    calculating: "Calculating...",

    // Results
    breedingResults: "Breeding Results",
    items: "Items",
    ivsInherited: "{count} of 6 IVs inherited",
    perfectIvsCol: "Perfect IVs",
    probability: "Probability",
    approxEggs: "Approx. Eggs",
    natureInheritance: "Nature Inheritance",
    abilityInheritance: "Ability Inheritance",
    natureWord: "nature",
    fromParent: "from {parent}",
    chance: "chance",
    randomNature: "Random nature — 4% each (no Everstone)",
    noAbilitySelected: "No ability selected",
    calculatingProbs: "Calculating probabilities...",
    selectBothParents: "Please select both parents first.",
    selectParentsPrompt: "Select two parents and click <strong>Calculate</strong> to see breeding probabilities.",
    calcFailed: "Calculation failed.",

    // Footer
    footer: "Data sourced from PokéAPI. Math uses exact combinatorics (no RNG).",

    // Language toggle
    langToggle: "Tieng Viet",

    // Theme toggle
    themeToggle: "Switch to light mode",

    // Target IVs
    targetIvs: "Desired Offspring IVs",
    targetIvsHint: "Select which IVs you want the baby to have (31)",
    targetIvResult: "Target IV Probability",
    targetStats: "Target stats",
    targetExact: "Exact match probability",
    vsGeneral: "vs. General {count}/6",
    pokemonNotFound: "No Pokémon found for \"{query}\"",

    // Browse / Advanced search
    browsePokemon: "Browse Pokémon",
    clear: "Clear",
    searchByName: "Search by name...",
    allEggGroups: "All Egg Groups",
    eggGroupLocked: "Filtered by partner's egg group",
    showingResults: "Showing {count} of {total}",
    loading: "Loading...",
    notFoundInDb: "Not found in database",
    notFoundEggGroupHint: "Results are filtered by partner's egg group. Try clearing the other parent first.",
    prev: "Prev",
    next: "Next",
  },

  vi: {
    // Header
    title: "Máy Tính Lai Giống Pokémon",
    subtitle: "Gen 9 - Chỉ số cá thể / Tính cách / Đặc tính",

    // Parent panels
    parentA: "Bố/Mẹ A",
    parentB: "Bố/Mẹ B",
    searchPlaceholder: "Tìm Pokémon...",
    searchParent: "Tìm {label}...",
    eggGroups: "Nhóm Trứng",

    // IVs
    perfectIvs: "IVs hoàn hảo (31)",
    all: "Tất cả",
    none: "Bỏ chọn",

    // Held items
    heldItem: "Vật phẩm giữ",
    itemNone: "Không",
    itemDestinyKnot: "Dây Chỉ Đỏ (Destiny Knot)",
    itemEverstone: "Đá Bất Biến (Everstone)",
    itemPowerHp: "Tạ Sức Mạnh (HP)",
    itemPowerAtk: "Vòng Tay Sức Mạnh (Atk)",
    itemPowerDef: "Đai Sức Mạnh (Def)",
    itemPowerSpa: "Kính Sức Mạnh (SpA)",
    itemPowerSpd: "Băng Đô Sức Mạnh (SpD)",
    itemPowerSpe: "Vòng Chân Sức Mạnh (Spe)",

    // Nature
    nature: "Tính cách",
    everstoneActive: "Đá Bất Biến đang hoạt động!",
    selectNature: "-- chọn tính cách --",
    neutral: "Trung tính",

    // Ability
    ability: "Đặc tính",
    hidden: "Ẩn",
    hiddenAbility: "Đặc tính ẩn",
    selectAbility: "-- chọn đặc tính --",

    // Action row
    breedingWithDitto: "Lai với Ditto",
    dittoHint: "(ảnh hưởng đến di truyền đặc tính)",
    calculate: "Tính toán",
    calculating: "Đang tính...",

    // Results
    breedingResults: "Kết quả lai giống",
    items: "Vật phẩm",
    ivsInherited: "{count} trong 6 IVs được di truyền",
    perfectIvsCol: "IVs hoàn hảo",
    probability: "Xác suất",
    approxEggs: "Số trứng (ước tính)",
    natureInheritance: "Di truyền tính cách",
    abilityInheritance: "Di truyền đặc tính",
    natureWord: "tính cách",
    fromParent: "từ {parent}",
    chance: "cơ hội",
    randomNature: "Tính cách ngẫu nhiên — mỗi loại 4% (không có Everstone)",
    noAbilitySelected: "Chưa chọn đặc tính",
    calculatingProbs: "Đang tính xác suất...",
    selectBothParents: "Vui lòng chọn cả hai bố mẹ trước.",
    selectParentsPrompt: "Chọn hai bố mẹ và nhấn <strong>Tính toán</strong> để xem xác suất lai giống.",
    calcFailed: "Tính toán thất bại.",

    // Footer
    footer: "Dữ liệu từ PokéAPI. Toán học sử dụng tổ hợp chính xác (không RNG).",

    // Language toggle
    langToggle: "English",

    // Theme toggle
    themeToggle: "Chuyển sang chế độ sáng",

    // Target IVs
    targetIvs: "IVs mong muốn cho con",
    targetIvsHint: "Chọn các chỉ số bạn muốn con có (31)",
    targetIvResult: "Xác suất IVs mong muốn",
    targetStats: "Chỉ số mục tiêu",
    targetExact: "Xác suất chính xác",
    vsGeneral: "so với {count}/6 chung",
    pokemonNotFound: "Không tìm thấy Pokémon \"{query}\"",

    // Browse / Advanced search
    browsePokemon: "Duyệt Pokémon",
    clear: "Xóa",
    searchByName: "Tìm theo tên...",
    allEggGroups: "Tất cả nhóm trứng",
    eggGroupLocked: "Lọc theo nhóm trứng đối tác",
    showingResults: "Hiển thị {count} trong {total}",
    loading: "Đang tải...",
    notFoundInDb: "Không tìm thấy trong cơ sở dữ liệu",
    notFoundEggGroupHint: "Kết quả đang lọc theo nhóm trứng đối tác. Hãy thử xóa Pokémon bên kia trước.",
    prev: "Trước",
    next: "Tiếp",
  },
};

// ══════════════════════════════════════════════════════════
// REACT CONTEXT
// ══════════════════════════════════════════════════════════

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    // Persist language preference
    return localStorage.getItem("pokemon-breeder-lang") || "en";
  });

  const changeLang = useCallback((newLang) => {
    setLang(newLang);
    localStorage.setItem("pokemon-breeder-lang", newLang);
  }, []);

  const t = useCallback(
    (key, params) => {
      let text = translations[lang]?.[key] || translations.en[key] || key;
      // Replace {param} placeholders
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          text = text.replace(`{${k}}`, v);
        });
      }
      return text;
    },
    [lang]
  );

  return (
    <LanguageContext.Provider value={{ lang, setLang: changeLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
