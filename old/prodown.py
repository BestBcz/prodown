import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import csv
import random
import os

# 设置请求头，模拟浏览器
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

# 定义所有地区的URL
region_urls = {
    "Europe": "https://liquipedia.net/counterstrike/Portal:Players/Europe",
    "CIS": "https://liquipedia.net/counterstrike/Portal:Players/CIS",
    "Americas": "https://liquipedia.net/counterstrike/Portal:Players/Americas",
    "Oceania": "https://liquipedia.net/counterstrike/Portal:Players/Oceania",
    "Asia": "https://liquipedia.net/counterstrike/Portal:Players/Asia",
    "Africa & Middle East": "https://liquipedia.net/counterstrike/Portal:Players/Africa_&_Middle_East"
}

# 存储所有选手链接
all_player_links = []

# 遍历每个地区
for region, url in region_urls.items():
    print(f"正在处理地区: {region}")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    tables = soup.find_all('table', class_='wikitable')
    for table in tables:
        links = table.find_all('a', href=True)
        for link in links:
            href = link['href']
            if (href.startswith('/counterstrike/') and
                    href.count('/') == 2 and
                    ' ' not in link.text.strip() and
                    len(link.text.strip()) < 15):
                all_player_links.append(link)

    print(f"{region} 找到 {len(tables)} 个表格，累计选手链接 {len(all_player_links)} 个")
    time.sleep(1)

print(f"总共找到 {len(all_player_links)} 个选手链接")

# 检查已处理链接（避免重复）
csv_file = 'cs2_players.csv'
processed_urls = set()
if os.path.exists(csv_file):
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            processed_urls.add(row[0])  # 用姓名作为唯一标识

# 准备CSV文件（追加模式）
with open(csv_file, 'a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # 如果文件是空的，写入表头
    if os.stat(csv_file).st_size == 0:
        writer.writerow(['姓名', '队伍', '国籍', '年龄', '游戏内位置'])

    # 处理链接
    for link in all_player_links:
        player_url = "https://liquipedia.net" + link['href']

        # 跳过已处理的链接
        if link.text.strip() in processed_urls:
            print(f"已处理: {player_url}，跳过")
            continue

        print(f"正在访问: {player_url}")

        try:
            player_response = requests.get(player_url, headers=headers)
            player_soup = BeautifulSoup(player_response.text, 'html.parser')

            if not player_soup.find('div', class_='infobox-cell-2', string='Nationality:'):
                print("这不是选手页面，跳过")
                continue

            name = player_soup.find('h1', class_='firstHeading').text.strip()
            team_elem = player_soup.find('div', class_='infobox-cell-2', string='Team:')
            team = team_elem.find_next('div').text.strip() if team_elem else "自由选手"

            nationality_elem = player_soup.find('div', class_='infobox-cell-2', string='Nationality:')
            nationality = nationality_elem.find_next('div').text.strip() if nationality_elem else "未知国籍"

            birth_elem = player_soup.find('div', class_='infobox-cell-2', string='Born:')
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

            role_elem = player_soup.find('div', class_='infobox-cell-2', string='Role:')
            role = role_elem.find_next('div').text.strip() if role_elem else "未知位置"

            print(f"姓名: {name}")
            print(f"队伍: {team}")
            print(f"国籍: {nationality}")
            print(f"年龄: {age}")
            print(f"游戏内位置: {role}")
            print("-" * 50)

            writer.writerow([name, team, nationality, age, role])

        except requests.exceptions.SSLError as e:
            print(f"SSL错误: {e}，跳过此链接")
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}，可能被拦截，跳过")
            time.sleep(5)  # 被拦截时休息5秒
        except AttributeError:
            print("某些数据缺失，跳过这个选手")

        # 随机延时1-3秒
        time.sleep(random.uniform(1, 3))

print(f"数据已保存到 {csv_file}")