import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import time

# 设置请求头，模拟浏览器
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}

# 从HLTV获取Top 500选手
hltv_url = "https://www.hltv.org/stats/players?start=0&limit=500"  # 前500名
response = requests.get(hltv_url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

player_links = []
for row in soup.select('table.stats-table tbody tr'):
    name_elem = row.find('a', class_='player-nick')
    if name_elem:
        name = name_elem.text.strip()
        player_links.append(name)

print(f"从HLTV找到 {len(player_links)} 个Top选手")

# 准备CSV文件
csv_file = 'cs2_top500_players.csv'
processed_urls = set()

# 检查已处理的数据（避免重复）
try:
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            processed_urls.add(row[0])
except FileNotFoundError:
    pass  # 如果文件不存在，跳过

# 写入CSV（追加模式）
with open(csv_file, 'a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # 如果文件是新的，写入表头
    if not processed_urls:
        writer.writerow(['姓名', '队伍', '国籍', '年龄', '游戏内位置'])

    for name in player_links:
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

        time.sleep(0.5)  # 延时0.5秒

print(f"数据已保存到 {csv_file}")