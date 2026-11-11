"""Shared vocabulary for the Section 88 register.

One place for the category codes, their bilingual labels and the ordered keyword
rules, so the classifier, the rescue merge and the plate cannot drift apart.
"""

CATEGORY_LABELS = {
    "REL": "Religious 宗教",
    "EDU": "Education 教育",
    "MED": "Medical & Health 醫療衞生",
    "ELD": "Elderly 長者",
    "DIS": "Disability & Rehab 復康傷健",
    "YTH": "Youth & Children 青少年兒童",
    "WOM": "Women 婦女",
    "ART": "Arts & Culture 文化藝術",
    "SPT": "Sports & Recreation 體育康樂",
    "ENV": "Animals & Environment 動物環保",
    "CLN": "Clan & Native-place 宗親同鄉",
    "COM": "Community & Kaifong 社區街坊",
    "BIZ": "Professional & Business 專業商會",
    "WEL": "Social Welfare & Services 社會福利服務",
    "FND": "Foundation & Trust 基金信託",
    "ASN": "Clubs & Associations 會社協會",
    "OTH": "Other / Uncategorised 其他",
}

MAIN_CODES = list(CATEGORY_LABELS)

# Ordered: earlier categories win a tie in the keyword pre-filter.
CATEGORY_KEYWORDS = [
    ("REL", ["教會","教堂","廟","寺","庵","佛教","菩薩","道教","道堂","基督","天主","耶穌","福音","宣道","浸信","信義","循道","聖公","靈糧","神召","救世軍","清真","回教","孔教","黃大仙","關帝","天后宮","church","christ","gospel","ministr","catholic","buddhis","temple","islam","muslim","mosque","evangel","baptist"]),
    ("EDU", ["學校","中學","小學","幼稚園","幼兒園","書院","學院","教育","助學","獎學","校友","家長教師","補習","school","colleg","education","academ","scholarship","alumni","kindergarten","university"]),
    ("MED", ["醫院","醫療","醫學","健康","護理院","保健","病人","癌","紓緩","善終","hospital","medical","health","clinic","cancer","hospice","nursing","patient"]),
    ("ELD", ["長者","耆英","安老","老人","老年","銀齡","頤養","松柏","elderly","aged","old age","senior"]),
    ("DIS", ["殘疾","傷健","弱能","失明","視障","聾","聽障","智障","自閉","唐氏","康復","展能","復康","disab","blind","deaf","handicap","autis","rehab"]),
    ("YTH", ["青年","青少年","少年","兒童","幼童","學童","童軍","youth","children","child ","scout","teen","juvenile"]),
    ("WOM", ["婦女","婦聯","女性","母親","women","woman","ladies","female"]),
    ("ART", ["藝術","文化","音樂","戲","曲藝","粵劇","京劇","國畫","書法","舞蹈","劇團","合唱","文藝","美術","攝影","文學","art","culture","music","opera","choir","danc","drama","theatre","calligraph","heritage"]),
    ("SPT", ["體育","運動","武術","太極","龍舟","足球","籃球","康樂","康體","sport","athletic","martial","tai chi","football","recreation","fitness"]),
    ("ENV", ["動物","護生","流浪","環保","環境","綠色","保育","生態","animal","spca","environment","green","conserv","ecolog","wildlife","nature"]),
    ("CLN", ["宗親","同鄉","聯誼","世家","clan","native","clansmen"]),
    ("COM", ["街坊","居民","業主","社區","鄉事","坊眾","互助","neighbourhood","community","resident","village","kaifong","owners"]),
    ("BIZ", ["商會","工會","公會","實業","行業","僱員","職工","專業","chamber","trade","profession","commerc","industr","business"]),
    ("WEL", ["福利","社會服務","關懷","關愛","扶輪","獅子會","明愛","樂施","慈善","救濟","扶貧","賑災","welfare","caritas","rotary","lions","oxfam","relief","charit","caring"]),
    ("FND", ["基金","信託","foundation","trust","endowment"]),
    ("ASN", ["協會","學會","聯會","總會","會所","俱樂部","association","society","club","federation","council","league","union","institute"]),
]

RELIGION_LABELS = {
    "PROT": ("Protestant Christian", "基督新教"),
    "BUD": ("Buddhism", "佛教"),
    "CATH": ("Roman Catholic", "天主教"),
    "TAO": ("Taoism", "道教"),
    "FOLK": ("Chinese folk religion", "民間信仰"),
    "CHRX": ("Other Christian", "其他基督宗教"),
    "ISL": ("Islam", "伊斯蘭教"),
    "CONF": ("Confucianism", "孔教"),
    "HIN": ("Hindu", "印度教"),
    "SIK": ("Sikh", "錫克教"),
    "JEW": ("Jewish", "猶太教"),
    "BAHAI": ("Bahá'í", "巴哈伊"),
    "OTH": ("Other / unclear", "其他／不明"),
}

RELIGION_CODES = set(RELIGION_LABELS)

COMMUNITY_LABELS = {
    "MUTUAL": ("Mutual aid", "互助服務"),
    "KAIFONG": ("Kaifong welfare", "街坊福利"),
    "CIVIL": ("Civil society", "公民社會"),
    "OTH": ("Unclear", "不明"),
    "RURAL": ("Rural / indigenous", "鄉事原居民"),
    "OWNERS": ("Owners / residents", "業主居民"),
    "PATRIOTIC": ("Patriotic-named", "愛國建制"),
    "NATIVE": ("Native-place", "同鄉"),
}

COMMUNITY_CODES = set(COMMUNITY_LABELS)
