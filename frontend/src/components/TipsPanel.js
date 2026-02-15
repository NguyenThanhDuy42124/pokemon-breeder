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
        id: "author-guide",
        icon: "🧬",
        title: "Secret Family Recipe",
        subtitle: "Step-by-step from 0IV to 6IV by @DaoTacVoSi",
        sections: [
          {
            type: "note",
            variant: "info",
            title: "🧬 Complete 0→6IV Roadmap",
            text: "This is the author's personal breeding strategy — a practical, step-by-step route from catching wild Pokémon to achieving perfect 6IV.",
          },
          {
            type: "steps",
            title: "STEP 1: Build a \"Gene Bank\"",
            items: [
              "Catch many Pokémon of the same species",
              "Keep those with 1–2 different perfect IVs (31)",
              "Goal: have 31s spread across all stats for combining later",
              "Example: Mon A → HP 31 | Mon B → Atk 31 | Mon C → Spe 31 | Mon D → SpD 31",
            ],
          },
          {
            type: "steps",
            title: "STEP 2: Combine to 2IV",
            items: [
              "Give each parent the Power Item matching their perfect stat",
              "HP 31 → Power Weight | Atk 31 → Power Bracer",
              "Power Items guarantee that stat is inherited",
              "Result: offspring with 2 perfect IVs!",
            ],
          },
          {
            type: "steps",
            title: "STEP 3: Build up 3IV → 4IV",
            items: [
              "Breed 2IV offspring with another Pokémon that has the missing 31 stats",
              "Keep using Power Items to lock important stats",
              "Replace weaker parents with better offspring each time",
              "Principle: whichever has more 31s becomes the main breeder",
              "Gradually you'll reach 3IV → then 4IV!",
            ],
          },
          {
            type: "steps",
            title: "STEP 4: Switch to Destiny Knot (acceleration phase)",
            items: [
              "Once you have a 3–4IV Pokémon, it's Destiny Knot time",
              "One parent holds Destiny Knot (passes 5 random IVs from both parents)",
              "Other parent holds Power Item for the most important stat",
              "Destiny Knot (5 IVs) + Power Item (1 guaranteed) = huge boost",
              "Repeat until you get the desired 5IV spread",
            ],
          },
          {
            type: "steps",
            title: "STEP 5: Hunt for 6IV (the \"RNG prayer\" phase)",
            items: [
              "Once you have two 5IV parents:",
              "One holds Destiny Knot, other holds Power Item for the key stat",
              "The 6th stat is pure luck: ~1/32 chance to roll 31",
              "Just be patient — it will come!",
            ],
          },
          {
            type: "table",
            headers: ["Phase", "Method", "Result"],
            rows: [
              ["1IV → 2IV", "Power Items", "2 perfect IVs"],
              ["2IV → 3IV → 4IV", "Power Items + swap parents", "3–4 perfect IVs"],
              ["3–4IV → 5IV", "Destiny Knot + Power Item", "5 perfect IVs"],
              ["5IV + 5IV → 6IV", "Destiny Knot + Power Item", "6 perfect IVs (🎲 ~1/32)"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Author's Note",
            text: "The key is patience and always swapping in better offspring. Don't try to jump from 0 to 6IV — build your gene pool gradually!",
          },
        ],
      },
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
        id: "egg-groups-gender",
        icon: "♂️♀️",
        title: "Egg Groups & Gender",
        subtitle: "Who can breed with whom?",
        sections: [
          {
            type: "text",
            text: "Breeding compatibility depends on Egg Groups, and the offspring species depends on the parents' gender. Understanding these rules is key!",
          },
          {
            type: "steps",
            title: "🥚 Egg Group Rules",
            items: [
              "Each Pokémon belongs to 1 or 2 Egg Groups (e.g., Charmander = Monster + Dragon)",
              "Two Pokémon can breed if they share at least 1 Egg Group",
              "Ditto can breed with any breedable Pokémon regardless of Egg Group",
              "\"Undiscovered\" Egg Group = cannot breed (legendaries, baby Pokémon)",
              "There are 15 Egg Groups total: Monster, Water 1/2/3, Bug, Flying, Field, Fairy, Grass, Human-Like, Mineral, Amorphous, Dragon, Ditto, Undiscovered",
            ],
          },
          {
            type: "steps",
            title: "♂️♀️ Gender & Offspring",
            items: [
              "Normal breeding (\u2642 × \u2640): offspring is always the female's species (base form)",
              "Ditto breeding: offspring is always the non-Ditto parent's species (base form)",
              "Gender ratio varies by species (e.g., starters = 87.5% \u2642 / 12.5% \u2640)",
              "Some Pokémon are male-only, female-only, or genderless",
              "Genderless Pokémon can only breed with Ditto",
            ],
          },
          {
            type: "table",
            headers: ["Gender Ratio", "Example Species", "Note"],
            rows: [
              ["50% \u2642 / 50% \u2640", "Pikachu, Eevee", "Most common"],
              ["87.5% \u2642 / 12.5% \u2640", "Starters, Riolu", "Hard to get females"],
              ["75% \u2642 / 25% \u2640", "Abra, Machop", "Fairly common"],
              ["100% \u2642", "Tauros, Braviary", "Needs Ditto to breed"],
              ["100% \u2640", "Chansey, Kangaskhan", "Always female offspring"],
              ["Genderless", "Magnemite, Porygon", "Ditto only"],
            ],
          },
          {
            type: "note",
            variant: "info",
            title: "ℹ Starter Tip",
            text: "Starters have 87.5% male ratio, making female starters rare. If you need to breed abilities from the female line, grab a Ditto \u2014 it is much easier!",
          },
        ],
      },
      {
        id: "ivs-0-3",
        icon: "📊",
        title: "IVs: 0 → 1-2-3",
        subtitle: "Build from scratch — Torchic example",
        sections: [
          {
            type: "text",
            text: "This is the standard process for building perfect IVs from zero. We'll use Torchic as an example — targeting perfect Attack and Speed first.",
          },
          {
            type: "steps",
            title: "📦 Step 1: Gather Materials",
            items: [
              "Find Torchic A with 31 Attack (or use a Ditto with 31 Atk)",
              "Find Torchic B with 31 Speed (or use a Ditto with 31 Spe)",
              "Any Torchic from wild / raid works — just check IVs with Judge",
              "Tip: Ditto with specific 31 IVs are very handy here!",
            ],
          },
          {
            type: "steps",
            title: "⚡ Step 2: Force 2 Perfect IVs",
            items: [
              "Parent A holds Power Bracer → guarantees Atk 31 is passed",
              "Parent B holds Power Anklet → guarantees Spe 31 is passed",
              "Both Power Items lock their stat → offspring gets 31 Atk + 31 Spe!",
              "Breed until you get a Torchic with both 31 Atk AND 31 Spe",
            ],
          },
          {
            type: "steps",
            title: "🔗 Step 3: Expand with Destiny Knot",
            items: [
              "Now your 2IV Torchic (Atk + Spe = 31) is the new parent",
              "Give it Destiny Knot → passes 5 of 12 combined IVs",
              "Breed with a partner that has other 31 IVs (HP, Def, SpD…)",
              "Destiny Knot inherits 5 IVs → strong chance to combine everything",
              "Check offspring → swap in better children as parents → repeat!",
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Key Insight",
            text: "Power Items guarantee specific IVs — use them first to lock 2 stats. Then switch to Destiny Knot to maximize total inheritance. This gets you to 2-3 perfect IVs in just a few eggs!",
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
        id: "author-guide",
        icon: "🧬",
        title: "Bí Kíp Gia Truyền",
        subtitle: "Hướng dẫn từ 0IV đến 6IV bởi @DaoTacVoSi",
        sections: [
          {
            type: "note",
            variant: "info",
            title: "🧬 Lộ Trình Hoàn Chỉnh 0→6IV",
            text: "Đây là chiến lược lai giống cá nhân của tác giả — một lộ trình thực tế, từng bước từ bắt Pokemon hoang dã đến đạt 6IV hoàn hảo.",
          },
          {
            type: "steps",
            title: "BƯỚC 1: Tạo \"Ngân Hàng Gene\"",
            items: [
              "Bắt nhiều Pokémon cùng loài",
              "Giữ lại những con có 1–2 IV 31 khác nhau",
              "Mục tiêu: có đủ các chỉ số 31 rải đều để ghép sau này",
              "Ví dụ: Con A → HP 31 | Con B → Atk 31 | Con C → Spe 31 | Con D → SpD 31",
            ],
          },
          {
            type: "steps",
            title: "BƯỚC 2: Ghép thành 2IV",
            items: [
              "Cho mỗi con cầm Power Item tương ứng với chỉ số 31 của nó",
              "HP 31 → Power Weight | Atk 31 → Power Bracer",
              "Power Item đảm bảo chỉ số đó được truyền lại",
              "Kết quả: con ra đời sẽ có 2 IV hoàn hảo!",
            ],
          },
          {
            type: "steps",
            title: "BƯỚC 3: Xây dần 3IV → 4IV",
            items: [
              "Ghép con 2IV với con khác có IV 31 còn thiếu",
              "Tiếp tục dùng Power Item để khóa các chỉ số quan trọng",
              "Mỗi lần ra con tốt hơn thì thay bố/mẹ cũ bằng con mới",
              "Nguyên tắc: con nào nhiều IV 31 hơn → giữ lại làm \"giống chính\"",
              "Dần dần bạn sẽ có 3IV → rồi 4IV hoàn hảo!",
            ],
          },
          {
            type: "steps",
            title: "BƯỚC 4: Chuyển sang Destiny Knot (giai đoạn tăng tốc)",
            items: [
              "Khi đã có con 3–4IV, đã đến lúc dùng Destiny Knot",
              "Một con cầm Destiny Knot (truyền 5 IV bất kỳ từ bố mẹ)",
              "Con còn lại cầm Power Item cho chỉ số quan trọng nhất",
              "Destiny Knot (5 IVs) + Power Item (1 đảm bảo) = boost lớn",
              "Lặp lại đến khi ra 5IV mong muốn",
            ],
          },
          {
            type: "steps",
            title: "BƯỚC 5: Săn 6IV (giai đoạn \"RNG cầu nguyện\")",
            items: [
              "Khi đã có 2 con 5IV:",
              "1 con cầm Destiny Knot, 1 con cầm Power Item",
              "Chỉ số còn lại là may rủi: ~1/32 cơ hội để random ra 31",
              "Lúc này chỉ cần kiên nhẫn — sẽ đến thôi!",
            ],
          },
          {
            type: "table",
            headers: ["Giai đoạn", "Phương pháp", "Kết quả"],
            rows: [
              ["1IV → 2IV", "Power Items", "2 IVs hoàn hảo"],
              ["2IV → 3IV → 4IV", "Power Items + thay bố mẹ", "3–4 IVs hoàn hảo"],
              ["3–4IV → 5IV", "Destiny Knot + Power Item", "5 IVs hoàn hảo"],
              ["5IV + 5IV → 6IV", "Destiny Knot + Power Item", "6 IVs hoàn hảo (🎲 ~1/32)"],
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Lời Nhắn Từ Tác Giả",
            text: "Bí quyết là kiên nhẫn và luôn thay bố mẹ bằng con tốt hơn. Đừng cố nhảy từ 0 lên 6IV — hãy xây dựng ngân hàng gene từ từ!",
          },
        ],
      },
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
        id: "egg-groups-gender",
        icon: "♂️♀️",
        title: "Nhóm Trứng & Giới Tính",
        subtitle: "Ai lai được với ai?",
        sections: [
          {
            type: "text",
            text: "Khả năng lai giống phụ thuộc vào Nhóm Trứng, và loài con phụ thuộc giới tính bố mẹ. Hiểu các quy tắc này là chìa khóa!",
          },
          {
            type: "steps",
            title: "🥚 Quy Tắc Nhóm Trứng",
            items: [
              "Mỗi Pokémon thuộc 1 hoặc 2 Nhóm Trứng (VD: Charmander = Monster + Dragon)",
              "Hai Pokémon lai được nếu có ít nhất 1 Nhóm Trứng chung",
              "Ditto lai được với bất kỳ Pokémon nào có thể lai",
              "Nhóm \"Undiscovered\" = không thể lai (huyền thoại, baby Pokémon)",
              "Có 15 Nhóm Trứng: Monster, Water 1/2/3, Bug, Flying, Field, Fairy, Grass, Human-Like, Mineral, Amorphous, Dragon, Ditto, Undiscovered",
            ],
          },
          {
            type: "steps",
            title: "♂️♀️ Giới Tính & Pokemon Con",
            items: [
              "Lai thường (♂ × ♀): con luôn là loài của mẹ (dạng tiến hóa đầu)",
              "Lai với Ditto: con luôn là loài của bố/mẹ không phải Ditto (dạng đầu)",
              "Tỉ lệ giới tính khác nhau theo loài (VD: starter = 87.5% ♂ / 12.5% ♀)",
              "Một số Pokémon chỉ đực, chỉ cái, hoặc không giới tính",
              "Pokémon không giới tính chỉ lai được với Ditto",
            ],
          },
          {
            type: "table",
            headers: ["Tỉ Lệ Giới Tính", "Loài Ví Dụ", "Ghi Chú"],
            rows: [
              ["50% ♂ / 50% ♀", "Pikachu, Eevee", "Phổ biến nhất"],
              ["87.5% ♂ / 12.5% ♀", "Starter, Riolu", "Khó kiếm con cái"],
              ["75% ♂ / 25% ♀", "Abra, Machop", "Khá phổ biến"],
              ["100% ♂", "Tauros, Braviary", "Cần Ditto để lai"],
              ["100% ♀", "Chansey, Kangaskhan", "Con luôn là cái"],
              ["Không giới tính", "Magnemite, Porygon", "Chỉ Ditto"],
            ],
          },
          {
            type: "note",
            variant: "info",
            title: "ℹ Mẹo Starter",
            text: "Starter có tỉ lệ 87.5% đực, nên starter cái rất hiếm. Nếu cần lai đặc tính từ dòng mẹ, dùng Ditto sẽ dễ hơn nhiều!",
          },
        ],
      },
      {
        id: "ivs-0-3",
        icon: "📊",
        title: "IVs: 0 → 1-2-3",
        subtitle: "Xây dựng từ số 0 — ví dụ Torchic",
        sections: [
          {
            type: "text",
            text: "Đây là quy trình chuẩn để build IV hoàn hảo từ con số 0. Lấy Torchic làm ví dụ — nhắm 31 Attack và Speed trước.",
          },
          {
            type: "steps",
            title: "📦 Bước 1: Gom Nguyên Liệu",
            items: [
              "Tìm Torchic A có 31 Attack (hoặc dùng Ditto có 31 Atk)",
              "Tìm Torchic B có 31 Speed (hoặc dùng Ditto có 31 Spe)",
              "Torchic hoang dã / raid đều được — check IVs bằng Judge",
              "Mẹo: Ditto có 31 IV ở stat cụ thể rất hữu ích ở bước này!",
            ],
          },
          {
            type: "steps",
            title: "⚡ Bước 2: Ép 2 IV Hoàn Hảo",
            items: [
              "Bố/Mẹ A cầm Power Bracer → đảm bảo truyền Atk 31",
              "Bố/Mẹ B cầm Power Anklet → đảm bảo truyền Spe 31",
              "Cả 2 Power Item khóa stat → con có 31 Atk + 31 Spe!",
              "Lai cho đến khi được Torchic có cả 31 Atk VÀ 31 Spe",
            ],
          },
          {
            type: "steps",
            title: "🔗 Bước 3: Mở Rộng với Destiny Knot",
            items: [
              "Giờ bạn có Torchic 2IV (Atk + Spe = 31) làm bố/mẹ mới",
              "Đặt Destiny Knot cho nó → truyền 5 trong 12 IVs tổng",
              "Lai với Pokemon có 31 IV ở stat khác (HP, Def, SpD…)",
              "Destiny Knot thừa hưởng 5 IVs → cơ hội cao ghép tất cả",
              "Check con → thay bố mẹ bằng con tốt hơn → lặp lại!",
            ],
          },
          {
            type: "note",
            variant: "success",
            title: "💡 Điểm Mấu Chốt",
            text: "Power Item đảm bảo IV cụ thể — dùng chúng trước để khóa 2 stat. Sau đó chuyển sang Destiny Knot để tối đa tổng IV được thừa hưởng. Có 2-3 IV hoàn hảo chỉ trong vài quả trứng!",
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
