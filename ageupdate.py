import requests
from bs4 import BeautifulSoup
import csv
import time

# HLTV 选手页面基础 URL
hltv_base_url = "https://www.hltv.org/player/"

# 设置请求头，模拟浏览器访问
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_player_age(player_name):
    """通过 HLTV 查询选手的年龄"""
    try:
        # 构造选手页面 URL
        # HLTV 的 URL 格式为 https://www.hltv.org/player/<id>/<name>
        # 由于我们没有 ID，先通过搜索页面找到选手
        search_url = f"https://www.hltv.org/search?query={player_name}"
        search_response = requests.get(search_url, headers=headers)

        if search_response.status_code != 200:
            print(f"搜索失败: {player_name}，状态码: {search_response.status_code}")
            return {"姓名": player_name, "年龄": "未知年龄"}

        # 解析搜索结果页面
        search_soup = BeautifulSoup(search_response.text, 'html.parser')
        player_link = search_soup.find("a", class_="player-nick")

        if not player_link:
            print(f"未找到 {player_name} 的 HLTV 页面")
            return {"姓名": player_name, "年龄": "未知年龄"}

        # 获取选手页面 URL
        player_url = player_link['href']
        player_response = requests.get(f"https://www.hltv.org{player_url}", headers=headers)

        if player_response.status_code != 200:
            print(f"请求选手页面失败: {player_name}，状态码: {player_response.status_code}")
            return {"姓名": player_name, "年龄": "未知年龄"}

        # 解析选手页面
        soup = BeautifulSoup(player_response.text, 'html.parser')

        # HLTV 页面中年龄通常在 class="player-info" 的 div 中
        info_div = soup.find("div", class_="player-info")
        if not info_div:
            print(f"未找到 {player_name} 的信息区域")
            return {"姓名": player_name, "年龄": "未知年龄"}

        # 查找包含年龄的元素（通常在 "Age: X years" 格式中）
        age_span = info_div.find("span", string=lambda text: text and "years" in text.lower())
        if not age_span:
            print(f"未找到 {player_name} 的年龄信息")
            return {"姓名": player_name, "年龄": "未知年龄"}

        # 提取年龄
        age_text = age_span.text.strip()
        age = ''.join(filter(str.isdigit, age_text))  # 提取数字
        if age and age.isdigit():
            age = int(age)
        else:
            age = "未知年龄"

        return {"姓名": player_name, "年龄": age}

    except Exception as e:
        print(f"查询错误: {player_name} - {e}")
        return {"姓名": player_name, "年龄": "未知年龄"}

# 选手名单（去重）
players = [
    "s1mple", "ZywOo", "NiKo", "dev1ce", "coldzera", "f0rest", "GeT_RiGhT",
    "kennyS", "olofmeister", "GuardiaN", "Snax", "shox", "KRIMZ", "flusha",
    "JW", "Xyp9x", "dupreeh", "gla1ve", "magisk", "electronic", "Boombl4",
    "Perfecto", "b1t", "m0NESY", "donk", "Ax1Le", "sh1ro", "nafany",
    "Stewie2K", "twistzz", "NAF", "nitr0", "tarik", "autimatic", "Skadoodle",
    "Hiko", "daps", "stanislaw", "Brehze", "Ethan", "dycha", "hades", "mantuu",
    "ropz", "broky", "karrigan", "rain", "tabseN", "syrsoN", "gade", "stavn",
    "cadiaN", "TeSeS", "sjuush", "refrezh", "blameF", "k0nfig", "valde", "acoR",
    "jabbi", "nicoodoz", "Spinx", "flamie", "sdy", "degster", "patsi", "r1nkle",
    "headtr1ck", "Mir", "Jame", "FL1T", "Qikert", "Buster", "WorldEdit", "Edward",
    "TaZ", "pasha", "byali", "FalleN", "fer", "TACO", "fnx", "LUCAS1", "HEN1",
    "kscerato", "yuurih", "arT", "VINI", "saffee", "drop", "chelo", "biguzera",
    "felps", "zews", "Boltz", "MalbsMd", "chrisJ", "oskar", "STYKO", "ISSAA",
    "woxic", "XANTARES", "Calyx", "MAJ3R", "hampus", "nawwk", "Golden", "REZ",
    "Brollan", "es3tag", "ottoNd", "allu", "sergej", "Aleksib", "suNny", "jks",
    "AZR", "Gratisfaction", "Liazz", "INS", "BnTeT", "LETN1", "RUSH", "Ex6TenZ",
    "SmithZz", "RpK", "bodyy", "NBK", "apEX", "Happy", "KioShiMa", "Zonic",
    "dennis", "twist", "Lekr0", "aizy", "MSL", "cajunb", "TenZ", "s0m", "smooya",
    "Grim", "floppy", "oSee", "junior", "ztr", "frozen", "huNter", "NertZ",
    "SunPayus", "jL", "Summer", "Starry", "EliGE", "magixx", "chopper", "zont1x",
    "siuhy", "bLitz", "Techno", "Senzu", "mzinho", "910", "Wicadia", "HeavyGod",
    "torzsi", "Jimpphat", "flameZ", "mezii", "jottAAA", "iM", "w0nderful",
    "kyxsan", "Maka", "Staehr", "FL4MUS", "fame", "ICY", "ultimate", "snow",
    "nqz", "Tauson", "sl3nd", "PR", "story", "skullz", "exit", "Lucaozy", "brnz4n",
    "insani", "phzy", "JBa", "LNZ", "JDC", "fear", "somebody", "CYPHER", "jkaem",
    "kaze", "ChildKing", "L1haNg", "Attacker", "JamYoung", "Jee", "Mercury",
    "Moseyuh", "Westmelon", "z4kr", "EmiliaQAQ", "C4LLM3SU3", "xertioN"
]
players = list(dict.fromkeys(players))  # 去重

# CSV 文件路径
csv_file = 'player.csv'

# 覆盖写入 CSV
with open(csv_file, 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # 写入表头
    writer.writerow(['姓名', '年龄'])

    for player in players:
        print(f"正在查询: {player}")
        info = get_player_age(player)

        # 打印结果
        print(f"姓名: {info['姓名']}")
        print(f"年龄: {info['年龄']}")
        print("-" * 50)

        # 写入 CSV
        writer.writerow([info['姓名'], info['年龄']])

        time.sleep(1)  # 增加延迟，避免请求过频被封

print(f"数据已保存到 {csv_file}")