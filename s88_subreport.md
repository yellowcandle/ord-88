# HK Section-88 Charities — Religious & Community Sub-Breakdowns

*LLM sub-classification via `qwen/qwen3.7-plus`. Religion/denomination and socio-political
character are **inferred from organisation names** and are indicative, not authoritative.*

## Religious groups by religion

![religion](s88_religion.png)

| Category | Count | % | Examples |
|---|---:|---:|---|
| Protestant Christian 基督新教 | 3,436 | 74.0% | 基督教418路社區教會有限公司 · 611靈糧堂有限公司 · 611靈糧堂有限公司 |
| Buddhism 佛教 | 482 | 10.4% | 中華彌勒文化慈善基金會有限公司 · 正念‧慈愛慈善基金有限公司 · 圓通精舍有限公司 |
| Roman Catholic 天主教 | 372 | 8.0% | Abbot in Hong Kong of  · Abbot in Hong Kong of  · Apostolic Catholic Chu |
| Taoism 道教 | 118 | 2.5% | 天教六壬良園舘有限公司 · 至和壇有限公司 · 正德道德堂有限公司 |
| Chinese folk religion 民間信仰 | 107 | 2.3% | 小西灣南海觀音廟管理委員會 · 觀塘潮僑工商界盂蘭勝會慈善基金有限公司 · 香港仔譚公爺廟有限公司 |
| Other Christian 其他基督宗教 | 53 | 1.1% | Aglow International Ho · 教會聚會所(基督徒管家) · 教會聚會所(基督徒管家)生命樹教育中心有限公 |
| Islam 伊斯蘭教 | 40 | 0.9% | Ahmadiyya Muslim Jamat · (中華回教博愛社) · (中華回教博愛社) |
| Unclear / other 不明 | 18 | 0.4% | 覺醒心靈成長中心有限公司 · 宣德(國際)有限公司 · 流堂有限公司 |
| Hindu 印度教 | 9 | 0.2% | Art of Living Society  · Bhaktivedanta Books Li · Bochasanwasi Shri Aksh |
| Sikh 錫克教 | 4 | 0.1% | Khalsa Diwan, Hong Kon · Khalsa Diwan, Hong Kon · Singh Sabha (H.K) Limi |
| Jewish 猶太教 | 3 | 0.1% | Chabad Lubavitch Jewis · Kehilat Zion Synagogue · United Jewish Congrega |
| Confucianism 孔教 | 3 | 0.1% | 孔教學院 · (香港孔聖堂有限公司) · (香港孔聖堂有限公司) |

### Protestant denominations

| Denomination | Count |
|---|---:|
| Independent | 1,273 |
| Baptist | 421 |
| Lutheran | 413 |
| Evangelical | 304 |
| Alliance | 295 |
| Pentecostal | 195 |
| Salvation-Army | 151 |
| Methodist | 127 |
| Anglican | 117 |
| Presbyterian | 69 |
| Adventist | 39 |
| Unstated | 27 |
| Brethren | 5 |

## Community groups by inferred socio-political character

![community](s88_community.png)

| Category | Count | % | Examples |
|---|---:|---:|---|
| General mutual-aid 互助服務 | 87 | 27.4% | 恒有餘力互助會 · 愛傳城中心有限公司 · 利眾社有限公司 |
| Kaifong welfare 街坊福利 | 72 | 22.6% | 石湖新村(河北段)街坊會 · 香港仔街坊福利會有限公司 · 香港仔街坊福利會有限公司 |
| Civil society / advocacy 公民社會 | 58 | 18.2% | 彩牛居民力量 · 堅離地同樂會慈善基金有限公司 · 全港社區發展連線有限公司 |
| Unclear 不明 | 30 | 9.4% | 昇普計劃 · 安迪潘瑜伽聯盟有限公司 · 護手社 |
| Patriotic / pro-establishment-named 愛國建制 | 27 | 8.5% | 香港中西區關愛服務及社區發展基金有限公司 · 博愛醫院歷屆總理聯誼會有限公司 · 博愛醫院歷屆總理聯誼會有限公司 |
| Owners / residents 業主居民 | 22 | 6.9% | 華人永遠墳場管理委員會 · 華人永遠墳場管理委員會 · 華人永遠墳場管理委員會 |
| Rural / indigenous 鄉事原居民 | 15 | 4.7% | 長洲鄉事委員會 · 山中小市有限公司 · 厦村鄉鄉事委員會 |
| Native-place 同鄉 | 7 | 2.2% | 香港仔田灣邨華富邨華貴邨潮僑坊眾盂蘭勝會有限 · Connecting Myanmar Lim · 印度之友 |

> **Caveat:** affiliation is inferred from naming patterns (e.g. 鄉事委員會 → rural-indigenous,
> 街坊福利會 → kaifong-grassroots, 各界聯會/社團聯會 → pro-establishment umbrella). It is a lean for
> the group as a *type*, not a verified political stance of any individual organisation.

**Outputs:** `sub_religion.csv`, `sub_community.csv`, `s88_religion.png`, `s88_community.png`