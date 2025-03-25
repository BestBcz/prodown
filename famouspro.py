import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import time

# 设置请求头
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}

# 手动整理的知名选手名单（约177个，可扩展）
famous_players = [
    "s1mple", "ZywOo", "NiKo", "dev1ce", "coldzera", "f0rest", "GeT_RiGhT",
    "kennyS", "olofmeister", "GuardiaN", "paszaBiceps", "Snax", "shox", "KRIMZ",
    "flusha", "JW", "Xyp9x", "dupreeh", "gla1ve", "magisk", "electronic",
    "Boombl4", "Perfecto", "b1t", "m0NESY", "donk", "Ax1Le", "sh1ro", "nafany",
    "Stewie2K", "ELiGE", "twistzz", "NAF", "nitr0", "tarik", "autimatic",
    "Skadoodle", "Hiko", "seangares", "daps", "stanislaw", "Brehze", "Ethan",
    "cerq", "dycha", "hades", "mantuu", "ropz", "broky", "karrigan", "rain",
    "tabseN", "syrsoN", "tiziaN", "gade", "stavn", "cadiaN", "TeSeS", "sjuush",
    "refrezh", "blameF", "k0nfig", "valde", "acoR", "jabbi", "nicoodoz",
    "Spinx", "flamie", "sdy", "yekindar", "degster", "patsi", "r1nkle",
    "headtr1ck", "Mir", "Jame", "FL1T", "Qikert", "Buster",
    "WorldEdit", "markeloff", "Edward", "zeus", "starix", "ceh9",
    "neo", "TaZ", "pasha", "byali", "FalleN", "fer", "TACO", "fnx", "LUCAS1",
    "HEN1", "kscerato", "yuurih", "arT", "VINI", "saffee", "drop", "chelo",
    "biguzera", "felps", "zews", "Boltz", "bit", "trk", "MalbsMd", "chrisJ",
    "oskar", "STYKO", "ISSAA", "woxic", "XANTARES", "Calyx", "MAJ3R", "hampus",
    "Plopski", "nawwk", "Golden", "REZ", "Brollan", "es3tag", "farlig", "bubzkji",
    "Lucky", "poizon", "ottoNd", "allu", "sergej", "xseveN", "Aleksib", "suNny",
     "jks", "AZR", "Gratisfaction", "Liazz",  "INS",
    "BnTeT", "LETN1",  "adreN", "RUSH",
    "ScreaM", "Ex6TenZ", "SmithZz", "RpK", "bodyy", "NBK-", "apEX",
    "Happy", "KioShiMa", "Zonic", "THREAT", "pronax", "dennis", "twist",
    "Lekr0", "draken",  "Maikelele", "fox", "aizy", "MSL",  "cajunb",
    "TenZ","s0m", "smooya", "Grim", "floppy", "oSee","junior", "ztr",  "frozen",
    "huNter-", "NertZ", "SunPayus", "jL"
]

print(f"知名选手名单包含 {len(famous_players)} 个选手")

# 检查已处理的数据
csv_file = 'cs2_famous_players.csv'
processed_urls = set()
try:
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            processed_urls.add(row[0])
except FileNotFoundError:
    pass

# 写入CSV
with open(csv_file, 'a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    if not processed_urls:
        writer.writerow(['姓名', '队伍', '国籍', '年龄', '游戏内位置'])

    for name in famous_players:
        if name in processed_urls:
            print(f"已处理: {name}，跳过")
            continue

        player_url = f"https://liquipedia.net/counterstrike/{name}"
        print(f"正在访问: {player_url}")

        try:
            response = requests.get(player_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            if not soup.find('div', class_='infobox-cell-2', string='Nationality:'):
                print("这不是选手页面，跳过")
                continue

            team_elem = soup.find('div', class_='infobox-cell-2', string='Team:')
            team = team_elem.find_next('div').text.strip() if team_elem else "自由选手"
            nationality_elem = soup.find('div', class_='infobox-cell-2', string='Nationality:')
            nationality = nationality_elem.find_next('div').text.strip() if nationality_elem else "未知国籍"
            birth_elem = soup.find('div', class_='infobox-cell-2', string='Born:')
            age = "未知年龄"
            if birth_elem:
                birth_date = birth_elem.find_next('div').text.strip()
                try:
                    birth_parts = birth_date.split(',')
                    if len(birth_parts) > 1:
                        birth_year = int(birth_parts[-1].strip().split()[0])
                        age = datetime.now().year - birth_year
                except (ValueError, IndexError):
                    age = "未知年龄"
            role_elem = soup.find('div', class_='infobox-cell-2', string='Role:')
            role = role_elem.find_next('div').text.strip() if role_elem else "未知位置"

            print(f"姓名: {name}")
            print(f"队伍: {team}")
            print(f"国籍: {nationality}")
            print(f"年龄: {age}")
            print(f"游戏内位置: {role}")
            print("-" * 50)

            writer.writerow([name, team, nationality, age, role])

        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}，跳过")

        time.sleep(0.2)  # 延时0.2秒

print(f"数据已保存到 {csv_file}")