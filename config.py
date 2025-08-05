# CS2选手爬虫配置文件

# 请求设置
REQUEST_CONFIG = {
    'timeout': 10,
    'max_retries': 3,
    'retry_delay': 5,
    'min_delay': 1.0,
    'max_delay': 3.0,
    'dynamic_delay': True,
    'delay_increment': 0.1,
    'max_delay_limit': 2.0
}

# 用户代理列表（轮换使用）
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

# 数据验证规则
VALIDATION_RULES = {
    'min_name_length': 2,
    'max_name_length': 20,
    'min_age': 15,
    'max_age': 50,
    'valid_roles': {
        'rifler', 'awper', 'igl', 'coach', 'support', 'lurker', 
        'rifler/awper', 'entry fragger', 'lurker/support'
    },
    'valid_nationalities': {
        'china', 'united states', 'russia', 'ukraine', 'denmark', 'sweden',
        'poland', 'france', 'germany', 'norway', 'estonia', 'latvia',
        'brazil', 'canada', 'israel', 'kazakhstan', 'netherlands', 'guatemala',
        'finland', 'spain', 'italy', 'belgium', 'austria', 'switzerland',
        'czech republic', 'slovakia', 'hungary', 'romania', 'bulgaria',
        'serbia', 'croatia', 'slovenia', 'bosnia and herzegovina',
        'montenegro', 'macedonia', 'albania', 'greece', 'turkey',
        'georgia', 'armenia', 'azerbaijan', 'uzbekistan', 'kyrgyzstan',
        'tajikistan', 'turkmenistan', 'mongolia', 'japan', 'south korea',
        'north korea', 'vietnam', 'thailand', 'malaysia', 'singapore',
        'indonesia', 'philippines', 'india', 'pakistan', 'bangladesh',
        'sri lanka', 'nepal', 'bhutan', 'myanmar', 'laos', 'cambodia',
        'australia', 'new zealand', 'fiji', 'papua new guinea',
        'south africa', 'egypt', 'morocco', 'algeria', 'tunisia',
        'libya', 'sudan', 'ethiopia', 'kenya', 'uganda', 'tanzania',
        'zambia', 'zimbabwe', 'botswana', 'namibia', 'angola',
        'mozambique', 'madagascar', 'mauritius', 'seychelles',
        'mexico', 'argentina', 'chile', 'peru', 'colombia', 'venezuela',
        'ecuador', 'bolivia', 'paraguay', 'uruguay', 'guyana',
        'suriname', 'french guiana', 'falkland islands'
    }
}

# 数据源配置
DATA_SOURCES = {
    'liquipedia': {
        'base_url': 'https://liquipedia.net/counterstrike',
        'regions': {
            'Europe': 'Portal:Players/Europe',
            'CIS': 'Portal:Players/CIS', 
            'Americas': 'Portal:Players/Americas',
            'Oceania': 'Portal:Players/Oceania',
            'Asia': 'Portal:Players/Asia',
            'Africa & Middle East': 'Portal:Players/Africa_&_Middle_East'
        },
        'enabled': True
    },
    'hltv': {
        'base_url': 'https://www.hltv.org',
        'stats_url': 'https://www.hltv.org/stats/players',
        'enabled': True
    },
    'famous_players': {
        'enabled': True,
        'players': [
            "s1mple", "ZywOo", "NiKo", "dev1ce", "coldzera", "f0rest", "GeT_RiGhT",
            "kennyS", "olofmeister", "GuardiaN", "paszaBiceps", "Snax", "shox", "KRIMZ",
            "flusha", "JW", "Xyp9x", "dupreeh", "gla1ve", "magisk", "electronic",
            "Boombl4", "Perfecto", "b1t", "m0NESY", "donk", "Ax1Le", "magixx",
            "chopper", "zont1x", "siuhy", "elige", "bLitz", "Techno", "Senzu",
            "mzinho", "910", "Wicadia", "HeavyGod", "torzsi", "Jimpphat", "flameZ",
            "mezii", "jottAAA", "iM", "w0nderful", "kyxsan", "Maka", "Staehr", "FL4MUS",
            "fame", "ICY", "NertZ", "ultimate", "snow", "nqz", "Tauson", "sl3nd",
            "PR", "story", "skullz", "exit", "Lucaozy", "brnz4n", "insani", "phzy",
            "JBa", "nicoodoz", "LNZ", "JDC", "fear", "somebody", "CYPHER", "jkaem",
            "kaze", "ChildKing", "L1haNg", "Attacker", "JamYoung", "Jee", "Mercury",
            "Moseyuh", "Westmelon", "z4kr", "EmiliaQAQ", "C4LLM3SU3", "xertioN"
        ]
    }
}

# 输出配置
OUTPUT_CONFIG = {
    'output_dir': 'output',
    'filename': 'cs2_players_optimized.csv',
    'encoding': 'utf-8',
    'backup_existing': True,
    'generate_report': True,
    'report_filename': 'statistics_report.txt'
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'log_file': 'crawler.log',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

# 错误处理配置
ERROR_HANDLING = {
    'max_consecutive_errors': 10,
    'error_cooldown': 60,  # 秒
    'retry_on_network_error': True,
    'retry_on_parse_error': False,
    'skip_invalid_players': True
}

# 数据清洗规则
DATA_CLEANING = {
    'remove_html_tags': True,
    'remove_wiki_links': True,
    'normalize_whitespace': True,
    'strip_quotes': True,
    'normalize_roles': True,
    'role_mapping': {
        'rifler/awper': 'Rifler',
        'entry fragger': 'Rifler',
        'lurker/support': 'Support',
        'awper': 'AWPer',
        'igl': 'IGL',
        'coach': 'Coach',
        'support': 'Support',
        'lurker': 'Lurker'
    }
} 