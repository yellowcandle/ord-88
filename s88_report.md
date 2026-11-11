# Hong Kong Section-88 Tax-Exempt Charities — Categorisation

**Source:** IRD `s88list.csv` · **As at:** 30 September 2026 · **Total organisations:** 17,623

**Method:** hybrid classifier — deterministic bilingual keyword matching for confident
single-match names, with `qwen/qwen3.7-plus` (via OpenRouter) as the LLM tie-breaker for
ambiguous (multi-keyword) and unmatched names.

![category distribution](s88_categories.png)

| # | Category | Count | % | Examples |
|---|---|---:|---:|---|
| 1 | Religious 宗教 | 4,645 | 26.4% | 小西灣南海觀音廟管理委員會 · 中華彌勒文化慈善基金會有限公司 · 天教六壬良園舘有限公司 |
| 2 | Education 教育 | 2,598 | 14.7% | 「向山舉目」助學金會 · 大埔泮涌社區教育中心有限公司 · 卓信英才有限公司 |
| 3 | Foundation & Trust 基金信託 | 2,292 | 13.0% | 啟路文教基金有限公司 · 千日成長基金會有限公司 · 100WF Hong Kong Foundati |
| 4 | Social Welfare & Services 社會福利服務 | 2,041 | 11.6% | 植皂坊義工隊 · 樂助同行 · 潤愛同行有限公司 |
| 5 | Clubs & Associations 會社協會 | 1,450 | 8.2% | 八仁社 · 友情有善協會 · 希望之橋協會 |
| 6 | Medical & Health 醫療衞生 | 1,290 | 7.3% | 健康行動有限公司 · 先進生物醫學儀器中心有限公司 · 這裏有愛癌症病人協會有限公司 |
| 7 | Arts & Culture 文化藝術 | 738 | 4.2% | 曲藝草蘆 · 香港振興京劇票房有限公司 · 黃大仙舞蹈坊 |
| 8 | Youth & Children 青少年兒童 | 686 | 3.9% | "F. O. C. U. S." (Focus  · 青鳥 · Adoptive Families of Hon |
| 9 | Community & Kaifong 社區街坊 | 318 | 1.8% | 石湖新村(河北段)街坊會 · 香港中西區關愛服務及社區發展基金有限公司 · 恒有餘力互助會 |
| 10 | Animals & Environment 動物環保 | 307 | 1.7% | 羽毛愛心伸展 · 綠色環保互動委員會有限公司 · 有尾無尾拯救隊有限公司 |
| 11 | Women 婦女 | 282 | 1.6% | 港區婦聯代表聯誼會基金有限公司 · 亞洲婦女協進會有限公司 · 亞洲婦女協進會有限公司 |
| 12 | Disability & Rehab 復康傷健 | 265 | 1.5% | Access HK · 愛加倍國際愛聾協會有限公司 · 香港精神復元者聯盟 |
| 13 | Elderly 長者 | 199 | 1.1% | 香港老戰士之家 · 耆英堂香港服務社 · 第二人生創生舍有限公司 |
| 14 | Professional & Business 專業商會 | 173 | 1.0% | 禁毒專業聯盟有限公司 · 國際人才組織聯合會有限公司 · 香港中文大學外科醫生協會有限公司 |
| 15 | Sports & Recreation 體育康樂 | 152 | 0.9% | 耆樂運動會 · 樂陽體育協會 · 3L Swim |
| 16 | Other / Uncategorised 其他 | 94 | 0.5% | 1A Group Limited · 1cm Limited · (香港仔有限公司) |
| 17 | Clan & Native-place 宗親同鄉 | 93 | 0.5% | 香港鍾氏宗親慈善基金有限公司 · Asian Regional Exchange  · 香港泉州慈善促進總會有限公司 |

**Outputs:** `s88list_categorised.csv` (per-org labels), `category_counts.json`, `s88_categories.png`