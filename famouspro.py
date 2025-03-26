import requests
import re
import csv
import time
from datetime import datetime

# MediaWiki API URL
api_url = "https://liquipedia.net/counterstrike/api.php"

# 国家名翻译表
country_translations = {
    "Ukraine": "乌克兰",
    "France": "法国",
    "Bosnia and Herzegovina": "波黑",
    "Denmark": "丹麦",
    "Brazil": "巴西",
    "Sweden": "瑞典",
    "Russia": "俄罗斯",
    "Poland": "波兰",
    "United States": "美国",
    "Canada": "加拿大",
    "Germany": "德国",
    "Finland": "芬兰",
    "Norway": "挪威"
    # 可根据需要扩展
}

def get_player_info(player_name):
    """获取指定选手的资料"""
    # 调用 API 获取 Wiki 文本
    params = {
        "action": "parse",
        "page": player_name,
        "format": "json",
        "prop": "wikitext"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    # 检查 API 返回是否有效
    if 'error' in data or 'parse' not in data:
        return {"姓名": player_name, "队伍": "未找到", "国籍": "未知国籍", "年龄": "未知年龄", "游戏内位置": "未知位置", "Major参与次数": 0}

    wikitext = data['parse']['wikitext']['*']

    # 提取 infobox
    infobox_match = re.search(r'\{\{Infobox player\n(.*?)\n\}\}', wikitext, re.DOTALL)
    if not infobox_match:
        return {"姓名": player_name, "队伍": "未找到", "国籍": "未知国籍", "年龄": "未知年龄", "游戏内位置": "未知位置", "Major参与次数": 0}

    infobox_text = infobox_match.group(1)
    infobox = {}
    for line in infobox_text.split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            infobox[key.strip().replace('|', '')] = value.strip()

    # 提取队伍
    team = infobox.get('team', '自由选手')

    # 提取并翻译国籍
    nationality = infobox.get('nationality', infobox.get('country', '未知国籍'))
    nationality = re.sub(r'\[\[|\]\]', '', nationality)  # 清理 Wiki 链接
    nationality_cn = country_translations.get(nationality, nationality)

    # 提取出生日期并计算年龄
    birth = infobox.get('birth_date', '')
    age = "未知年龄"
    if birth:
        year_match = re.search(r'\d{4}', birth)  # 匹配四位年份
        if year_match:
            birth_year = int(year_match.group(0))
            age = datetime.now().year - birth_year

    # 提取游戏内位置
    role = infobox.get('role', '未知位置')
    if 'rifler' in role.lower():
        role = "Rifler"  # 统一为 Rifler

    # 统计 Major 参与次数
    major_count = len(re.findall(r'\{\{Tournament results row.*?Major.*?\}\}', wikitext, re.DOTALL))

    # 返回选手信息字典
    return {
        "姓名": player_name,
        "队伍": team,
        "国籍": nationality_cn,
        "年龄": age,
        "游戏内位置": role,
        "Major参与次数": major_count
    }

# 选手名单
players = [
    "s1mple", "ZywOo", "NiKo", "dev1ce", "coldzera", "f0rest", "GeT_RiGhT",
    "kennyS", "olofmeister", "GuardiaN", "paszaBiceps", "Snax", "shox", "KRIMZ",
    "flusha", "JW", "Xyp9x", "dupreeh", "gla1ve", "magisk", "electronic",
    "Boombl4", "Perfecto", "b1t", "m0NESY", "donk", "Ax1Le", "sh1ro"
]

# CSV 文件路径
csv_file = 'cs2_players.csv'

# 检查已处理的数据，避免重复
processed_players = set()
try:
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            processed_players.add(row[0])
except FileNotFoundError:
    pass

# 写入 CSV
with open(csv_file, 'a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # 如果文件是新的，写入表头
    if not processed_players:
        writer.writerow(['姓名', '队伍', '国籍', '年龄', '游戏内位置', 'Major参与次数'])

    for player in players:
        if player in processed_players:
            print(f"已处理: {player}，跳过")
            continue

        print(f"正在查询: {player}")
        info = get_player_info(player)

        # 打印结果
        print(f"姓名: {info['姓名']}")
        print(f"队伍: {info['队伍']}")
        print(f"国籍: {info['国籍']}")
        print(f"年龄: {info['年龄']}")
        print(f"游戏内位置: {info['游戏内位置']}")
        print(f"Major参与次数: {info['Major参与次数']}")
        print("-" * 50)

        # 写入 CSV
        writer.writerow([
            info['姓名'], info['队伍'], info['国籍'],
            info['年龄'], info['游戏内位置'], info['Major参与次数']
        ])

        time.sleep(0.5)  # 避免请求过频

print(f"数据已保存到 {csv_file}")