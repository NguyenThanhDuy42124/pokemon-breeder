import React, { useState, useEffect, useCallback } from "react";
import { useLanguage } from "../i18n";

/* ══════════════════════════════════════════════════════════
   Breeding Tips Data — English & Vietnamese
   ══════════════════════════════════════════════════════════ */
const TIPS_DATA = {
  en: {
    panelTitle: "Breeding Tips",
    back: "← Back",
    close: "✕",
    tips: [
      {
        id: "held-items",
        icon: "🎒",
        title: "Held Items Guide",
        subtitle: "Master breeding items for max efficiency",
        sections: [
          {
            type: "table",
            headers: ["Item", "Effect", "Best Use"],
            rows: [
              ["Destiny Knot", "Passes 5 IVs from both parents (normally 3)", "Must-have for IV breeding"],
              ["Everstone", "100% passes holder's Nature", "Use on parent with desired Nature"],
              ["Power Weight", "Guarantees HP IV from holder + 4 random", "When HP IV is priority"],
              ["Power Bracer", "Guarantees Atk IV from holder + 4 random", "When Atk IV is priority"],
              ["Power Belt", "Guarantees Def IV from holder + 4 random", "When Def IV is priority"],
              ["Power Lens", "Guarantees SpA IV from holder + 4 random", "When SpA IV is priority"],
              ["Power Band", "Guarantees SpD IV from holder + 4 random", "When SpD IV is priority"],
              ["Power Anklet", "Guarantees Spe IV from holder + 4 random", "When Spe IV is priority"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Best Combination",
            text: "Destiny Knot on one parent + Everstone on the other = Inherit 5 IVs + guaranteed Nature!",
          },
          {
            type: "note",
            variant: "warning",
            title: "⚠ Important",
            text: "If both parents hold Power Items, only one is randomly chosen. Power Item + Destiny Knot = 1 guaranteed IV + 4 random = 5 total IVs passed.",
          },
        ],
      },
      {
        id: "nature",
        icon: "🌿",
        title: "Nature Inheritance",
        subtitle: "How Natures pass to offspring",
        sections: [
          {
            type: "table",
            headers: ["Scenario", "Result"],
            rows: [
              ["No Everstone", "Random nature (1/25 = 4% each)"],
              ["One parent holds Everstone", "100% that parent's Nature"],
              ["Both parents hold Everstone", "50% chance from each parent"],
            ],
          },
          {
            type: "steps",
            title: "Strategy",
            items: [
              "Put Everstone on the parent with your desired Nature",
              "Give Destiny Knot to the other parent for IV breeding",
              "If both parents have good Natures, Everstone on both — 50/50 is still great!",
              "Mint items change Nature effects but do NOT affect breeding",
            ],
          },
        ],
      },
      {
        id: "hidden-ability",
        icon: "⭐",
        title: "Hidden Ability (HA)",
        subtitle: "How to breed for Hidden Abilities",
        sections: [
          {
            type: "table",
            headers: ["Scenario", "HA Chance"],
            rows: [
              ["♀ has HA × ♂ normal", "60%"],
              ["♀ normal × ♂ has HA", "0% (cannot pass!)"],
              ["♂ has HA × Ditto", "60%"],
              ["♀ has HA × Ditto", "60%"],
              ["Genderless has HA × Ditto", "60%"],
              ["Neither parent has HA", "0% (impossible)"],
            ],
          },
          {
            type: "note",
            variant: "warning",
            title: "⚠ Key Rule",
            text: "Males can only pass HA when breeding with Ditto! In normal ♂×♀ breeding, only the female's ability matters.",
          },
          {
            type: "note",
            variant: "info",
            title: "ℹ Regular Abilities",
            text: "For non-hidden abilities: ~80% chance to pass the mother's ability, ~20% for the other regular ability slot.",
          },
        ],
      },
      {
        id: "ivs-0-3",
        icon: "📊",
        title: "IVs: 0 → 1-2-3",
        subtitle: "Starting from scratch",
        sections: [
          {
            type: "text",
            text: "Don't worry about starting with 0 perfect IVs! Here are reliable ways to build up:",
          },
          {
            type: "steps",
            title: "🎯 Catching Pokemon with Good IVs",
            items: [
              "1★ Raid: At least 1 guaranteed perfect IV",
              "2★ Raid: At least 2 guaranteed perfect IVs",
              "3★ Raid: At least 3 guaranteed perfect IVs",
              "4★+ Raid: At least 4 guaranteed perfect IVs",
              "SOS Chains (30+): 4 guaranteed perfect IVs",
              "Friend Safari: 2 guaranteed perfect IVs",
            ],
          },
          {
            type: "steps",
            title: "🥚 Breeding Strategy",
            items: [
              "Catch 2 Pokemon of same egg group with different perfect IVs",
              "Without Destiny Knot: 3 random IVs inherited from parents",
              "Breed → check offspring IVs with Judge function",
              "Replace weaker parent with best offspring",
              "Repeat 2-3 generations → 2-3 perfect IVs easily!",
            ],
          },
        ],
      },
      {
        id: "ivs-4-5",
        icon: "📈",
        title: "IVs: 3 → 4-5",
        subtitle: "Getting competitive-ready Pokemon",
        sections: [
          {
            type: "steps",
            title: "Step-by-Step",
            items: [
              "Get 2 parents with 3+ IVs covering different stats (e.g., A: HP/Atk/Def, B: SpA/SpD/Spe)",
              "Give Destiny Knot to one parent (passes 5 of 12 combined IVs)",
              "Give Everstone to the other parent if Nature matters",
              "Breed 20-30 eggs per batch",
              "Check offspring → replace parents with better children",
              "After 1-2 generations → 4-5 IV Pokemon!",
            ],
          },
          {
            type: "table",
            headers: ["Parents", "Destiny Knot", "5IV Chance"],
            rows: [
              ["Both 3IV", "Yes", "~3%"],
              ["Both 4IV", "Yes", "~10%"],
              ["4IV + 5IV", "Yes", "~17%"],
              ["Both 5IV", "Yes", "~33%"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Pro Tip",
            text: "Always swap in better offspring as parents. IVs compound quickly — usually 5IV within 30-50 eggs!",
          },
        ],
      },
      {
        id: "ivs-6",
        icon: "💎",
        title: "IVs: 5 → 6 (Perfect)",
        subtitle: "The holy grail of breeding",
        sections: [
          {
            type: "text",
            text: "Getting all 6 perfect IVs is the hardest part. Here's how and when it's worth it:",
          },
          {
            type: "steps",
            title: "📐 The Math",
            items: [
              "Destiny Knot passes 5 of 12 parent IVs",
              "6th stat is completely random: 1/32 chance for 31",
              "Two 6IV parents + Destiny Knot: ~3.13% per egg",
              "Two 5IV parents (complementary): ~0.52% per egg",
              "Average: 32-200 eggs depending on parents",
            ],
          },
          {
            type: "table",
            headers: ["Parents", "6IV Chance", "Avg. Eggs"],
            rows: [
              ["6IV + 6IV", "~3.13%", "~32"],
              ["6IV + 5IV", "~1.56%", "~64"],
              ["5IV + 5IV (complementary)", "~0.52%", "~192"],
              ["5IV + 5IV (same missing stat)", "~0%", "Nearly impossible"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Alternative: Hyper Training",
            text: "Use Bottle Cap (1 stat) or Gold Bottle Cap (all stats) at Lv.100. Note: Hyper Trained IVs do NOT pass down in breeding!",
          },
          {
            type: "note",
            variant: "info",
            title: "ℹ Practical Advice",
            text: "Most competitive players breed for 5IV (dump the unused stat) + Bottle Cap for the 6th if needed. A 0 Atk IV is actually desired for special attackers (reduces Foul Play & confusion damage)!",
          },
        ],
      },
    ],
  },

  vi: {
    panelTitle: "Mẹo Lai Giống",
    back: "← Quay lại",
    close: "✕",
    tips: [
      {
        id: "held-items",
        icon: "🎒",
        title: "Hướng Dẫn Vật Phẩm",
        subtitle: "Sử dụng vật phẩm lai giống hiệu quả",
        sections: [
          {
            type: "table",
            headers: ["Vật phẩm", "Hiệu ứng", "Mẹo sử dụng"],
            rows: [
              ["Destiny Knot", "Truyền 5 IVs từ 2 bố mẹ (thường là 3)", "Bắt buộc khi lai IVs"],
              ["Everstone", "100% truyền Tính cách của người giữ", "Cho bố/mẹ có Tính cách mong muốn"],
              ["Power Weight", "Đảm bảo IV HP từ người giữ + 4 ngẫu nhiên", "Khi ưu tiên IV HP"],
              ["Power Bracer", "Đảm bảo IV Atk từ người giữ + 4 ngẫu nhiên", "Khi ưu tiên IV Atk"],
              ["Power Belt", "Đảm bảo IV Def từ người giữ + 4 ngẫu nhiên", "Khi ưu tiên IV Def"],
              ["Power Lens", "Đảm bảo IV SpA từ người giữ + 4 ngẫu nhiên", "Khi ưu tiên IV SpA"],
              ["Power Band", "Đảm bảo IV SpD từ người giữ + 4 ngẫu nhiên", "Khi ưu tiên IV SpD"],
              ["Power Anklet", "Đảm bảo IV Spe từ người giữ + 4 ngẫu nhiên", "Khi ưu tiên IV Spe"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Tổ Hợp Tốt Nhất",
            text: "Destiny Knot cho 1 bố/mẹ + Everstone cho bố/mẹ còn lại = Thừa hưởng 5 IVs + đảm bảo Tính cách!",
          },
          {
            type: "note",
            variant: "warning",
            title: "⚠ Lưu Ý",
            text: "Nếu cả 2 bố mẹ giữ Power Item, chỉ 1 được chọn ngẫu nhiên. Power Item + Destiny Knot = 1 IV đảm bảo + 4 ngẫu nhiên = 5 IVs tổng.",
          },
        ],
      },
      {
        id: "nature",
        icon: "🌿",
        title: "Di Truyền Tính Cách",
        subtitle: "Cách Tính cách truyền sang con",
        sections: [
          {
            type: "table",
            headers: ["Trường hợp", "Kết quả"],
            rows: [
              ["Không có Everstone", "Tính cách ngẫu nhiên (1/25 = 4% mỗi loại)"],
              ["Một bố/mẹ giữ Everstone", "100% Tính cách của bố/mẹ đó"],
              ["Cả hai giữ Everstone", "50% từ mỗi bố/mẹ"],
            ],
          },
          {
            type: "steps",
            title: "Chiến Lược",
            items: [
              "Đặt Everstone cho bố/mẹ có Tính cách mong muốn",
              "Đặt Destiny Knot cho bố/mẹ còn lại để lai IVs",
              "Nếu cả 2 bố mẹ Tính cách tốt, Everstone cho cả 2 — 50/50 vẫn tốt!",
              "Mint thay đổi hiệu ứng Tính cách nhưng KHÔNG ảnh hưởng lai giống",
            ],
          },
        ],
      },
      {
        id: "hidden-ability",
        icon: "⭐",
        title: "Đặc Tính Ẩn (HA)",
        subtitle: "Cách lai để có Đặc tính ẩn",
        sections: [
          {
            type: "table",
            headers: ["Trường hợp", "Tỉ lệ HA"],
            rows: [
              ["♀ có HA × ♂ thường", "60%"],
              ["♀ thường × ♂ có HA", "0% (không thể truyền!)"],
              ["♂ có HA × Ditto", "60%"],
              ["♀ có HA × Ditto", "60%"],
              ["Không giới tính có HA × Ditto", "60%"],
              ["Cả hai không có HA", "0% (không thể)"],
            ],
          },
          {
            type: "note",
            variant: "warning",
            title: "⚠ Quy Tắc Quan Trọng",
            text: "Con đực chỉ truyền HA khi lai với Ditto! Trong lai giống ♂×♀ bình thường, chỉ đặc tính của con cái mới quan trọng.",
          },
          {
            type: "note",
            variant: "info",
            title: "ℹ Đặc Tính Thường",
            text: "Với đặc tính không ẩn: ~80% truyền đặc tính của mẹ, ~20% cho slot đặc tính thường còn lại.",
          },
        ],
      },
      {
        id: "ivs-0-3",
        icon: "📊",
        title: "IVs: 0 → 1-2-3",
        subtitle: "Bắt đầu từ con số 0",
        sections: [
          {
            type: "text",
            text: "Đừng lo khi bắt đầu với 0 IVs hoàn hảo! Đây là các cách đáng tin cậy:",
          },
          {
            type: "steps",
            title: "🎯 Bắt Pokemon Có IVs Tốt",
            items: [
              "Raid 1★: Ít nhất 1 IV hoàn hảo đảm bảo",
              "Raid 2★: Ít nhất 2 IVs hoàn hảo đảm bảo",
              "Raid 3★: Ít nhất 3 IVs hoàn hảo đảm bảo",
              "Raid 4★+: Ít nhất 4 IVs hoàn hảo đảm bảo",
              "SOS Chain (30+): 4 IVs hoàn hảo đảm bảo",
              "Friend Safari: 2 IVs hoàn hảo đảm bảo",
            ],
          },
          {
            type: "steps",
            title: "🥚 Chiến Lược Lai Giống",
            items: [
              "Bắt 2 Pokemon cùng nhóm trứng với IVs hoàn hảo khác nhau",
              "Không có Destiny Knot: 3 IVs ngẫu nhiên được thừa hưởng",
              "Lai → kiểm tra IVs con với chức năng Judge",
              "Thay thế bố/mẹ yếu hơn bằng con tốt nhất",
              "Lặp lại 2-3 thế hệ → 2-3 IVs hoàn hảo dễ dàng!",
            ],
          },
        ],
      },
      {
        id: "ivs-4-5",
        icon: "📈",
        title: "IVs: 3 → 4-5",
        subtitle: "Pokemon sẵn sàng thi đấu",
        sections: [
          {
            type: "steps",
            title: "Từng Bước",
            items: [
              "Chuẩn bị 2 bố mẹ có 3+ IVs ở các stat khác nhau (VD: A: HP/Atk/Def, B: SpA/SpD/Spe)",
              "Đặt Destiny Knot cho 1 bố/mẹ (truyền 5 trong 12 IVs tổng)",
              "Đặt Everstone cho bố/mẹ còn lại nếu cần Tính cách",
              "Lai 20-30 trứng mỗi đợt",
              "Kiểm tra con → thay bố mẹ bằng con tốt hơn",
              "Sau 1-2 thế hệ → Pokemon 4-5 IVs!",
            ],
          },
          {
            type: "table",
            headers: ["Bố mẹ", "Destiny Knot", "Tỉ lệ 5IV"],
            rows: [
              ["Cả 2 có 3IV", "Có", "~3%"],
              ["Cả 2 có 4IV", "Có", "~10%"],
              ["4IV + 5IV", "Có", "~17%"],
              ["Cả 2 có 5IV", "Có", "~33%"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Mẹo Pro",
            text: "Luôn thay bố mẹ bằng con tốt hơn. IVs tích lũy nhanh — thường đạt 5IV trong 30-50 trứng!",
          },
        ],
      },
      {
        id: "ivs-6",
        icon: "💎",
        title: "IVs: 5 → 6 (Hoàn Hảo)",
        subtitle: "Đỉnh cao lai giống Pokemon",
        sections: [
          {
            type: "text",
            text: "Đạt 6 IVs hoàn hảo (31) là phần khó nhất. Đây là cách và khi nào đáng làm:",
          },
          {
            type: "steps",
            title: "📐 Toán Học",
            items: [
              "Destiny Knot truyền 5 trong 12 IVs bố mẹ",
              "Stat thứ 6 hoàn toàn ngẫu nhiên: 1/32 cơ hội cho 31",
              "Hai bố mẹ 6IV + Destiny Knot: ~3.13% mỗi trứng",
              "Hai bố mẹ 5IV (bổ sung): ~0.52% mỗi trứng",
              "Trung bình: 32-200 trứng tùy bố mẹ",
            ],
          },
          {
            type: "table",
            headers: ["Bố mẹ", "Tỉ lệ 6IV", "TB trứng"],
            rows: [
              ["6IV + 6IV", "~3.13%", "~32"],
              ["6IV + 5IV", "~1.56%", "~64"],
              ["5IV + 5IV (bổ sung)", "~0.52%", "~192"],
              ["5IV + 5IV (cùng thiếu)", "~0%", "Gần như bất khả thi"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Cách Thay Thế: Hyper Training",
            text: "Dùng Bottle Cap (1 stat) hoặc Gold Bottle Cap (tất cả) tại Lv.100. Lưu ý: IVs Hyper Train KHÔNG truyền qua lai giống!",
          },
          {
            type: "note",
            variant: "info",
            title: "ℹ Lời Khuyên Thực Tế",
            text: "Hầu hết người chơi thi đấu lai 5IV (bỏ stat không cần) rồi dùng Bottle Cap cho stat thứ 6. IV Atk = 0 thực ra được ưa chuộng cho đánh đặc biệt (giảm sát thương Foul Play & confusion)!",
          },
        ],
      },
    ],
  },
};

/* ══════════════════════════════════════════════════════════
   Section Renderers
   ══════════════════════════════════════════════════════════ */

function TipTable({ headers, rows }) {
  return (
    <div className="tip-table-wrapper">
      <table className="tip-table">
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TipSteps({ title, items }) {
  return (
    <div className="tip-steps">
      {title && <h4 className="tip-steps-title">{title}</h4>}
      <ol className="tip-steps-list">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ol>
    </div>
  );
}

function TipNote({ variant, title, text }) {
  return (
    <div className={`tip-note tip-note-${variant || "info"}`}>
      {title && <strong className="tip-note-title">{title}</strong>}
      <p className="tip-note-text">{text}</p>
    </div>
  );
}

function renderSection(section, idx) {
  switch (section.type) {
    case "table":
      return <TipTable key={idx} headers={section.headers} rows={section.rows} />;
    case "steps":
      return <TipSteps key={idx} title={section.title} items={section.items} />;
    case "note":
      return <TipNote key={idx} variant={section.variant} title={section.title} text={section.text} />;
    case "text":
      return <p key={idx} className="tip-text">{section.text}</p>;
    default:
      return null;
  }
}

/* ══════════════════════════════════════════════════════════
   Main Component
   ══════════════════════════════════════════════════════════ */

export default function TipsPanel({ isOpen, onToggle }) {
  const { lang } = useLanguage();
  const [activeTipId, setActiveTipId] = useState(null);

  const data = TIPS_DATA[lang] || TIPS_DATA.en;
  const activeTip = data.tips.find((t) => t.id === activeTipId);

  const handleClose = useCallback(() => {
    setActiveTipId(null);
    onToggle();
  }, [onToggle]);

  const handleBack = useCallback(() => {
    setActiveTipId(null);
  }, []);

  // Escape key to close
  useEffect(() => {
    function handleEsc(e) {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    }
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [isOpen, handleClose]);

  // Reset active tip when sidebar closes
  useEffect(() => {
    if (!isOpen) setActiveTipId(null);
  }, [isOpen]);

  return (
    <>
      {/* Toggle tab — left edge */}
      {!isOpen && (
        <button
          className="tips-toggle-btn"
          onClick={onToggle}
          title={data.panelTitle}
        >
          <span className="tips-toggle-icon">💡</span>
          <span className="tips-toggle-text">TIPS</span>
        </button>
      )}

      {/* Overlay (mobile: click to close) */}
      {isOpen && <div className="tips-overlay" onClick={handleClose} />}

      {/* Sidebar */}
      <aside className={`tips-sidebar ${isOpen ? "open" : ""}`}>
        {/* Header */}
        <div className="tips-sidebar-header">
          {activeTipId ? (
            <button className="tips-back-btn" onClick={handleBack}>
              {data.back}
            </button>
          ) : (
            <h3 className="tips-sidebar-title">
              <span className="tips-title-icon">💡</span> {data.panelTitle}
            </h3>
          )}
          <button className="tips-close-btn" onClick={handleClose}>
            {data.close}
          </button>
        </div>

        {/* Content */}
        <div className="tips-sidebar-content">
          {!activeTipId ? (
            /* ── Menu ── */
            <div className="tips-menu">
              {data.tips.map((tip) => (
                <button
                  key={tip.id}
                  className="tips-menu-item"
                  onClick={() => setActiveTipId(tip.id)}
                >
                  <span className="tips-menu-icon">{tip.icon}</span>
                  <div className="tips-menu-text">
                    <span className="tips-menu-title">{tip.title}</span>
                    <span className="tips-menu-subtitle">{tip.subtitle}</span>
                  </div>
                  <span className="tips-menu-arrow">›</span>
                </button>
              ))}
            </div>
          ) : (
            /* ── Detail ── */
            <div className="tip-detail">
              <div className="tip-detail-header">
                <span className="tip-detail-icon">{activeTip.icon}</span>
                <div>
                  <h3 className="tip-detail-title">{activeTip.title}</h3>
                  <p className="tip-detail-subtitle">{activeTip.subtitle}</p>
                </div>
              </div>
              <div className="tip-detail-body">
                {activeTip.sections.map((section, idx) =>
                  renderSection(section, idx)
                )}
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
