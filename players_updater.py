#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CS2选手信息更新器 (修复版)
1. 解决Liquipedia 403反爬虫问题 (使用cloudscraper)
2. 当新数据为"未知"时，保留CSV中原有的旧数据
"""
import requests
import cloudscraper  # 新增：用于绕过Cloudflare
from bs4 import BeautifulSoup
from datetime import datetime
import time
import csv
import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('players_updater.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PlayerInfo:
    """选手信息数据类"""
    name: str
    team: str = "Free Agent"
    nationality: str = "未知国籍"
    age: str = "未知年龄"
    role: str = "未知位置"

    def to_dict(self) -> Dict[str, str]:
        return {
            '姓名': self.name,
            '队伍': self.team,
            '国籍': self.nationality,
            '年龄': str(self.age),
            '游戏内位置': self.role
        }

    def merge_old_data(self, old_info: 'PlayerInfo'):
        """
        核心逻辑：如果当前(新)数据是未知/默认值，而旧数据有效，则保留旧数据
        """
        if not old_info:
            return

        # 1. 队伍：如果新抓取的是Free Agent，但旧数据有队伍，是否保留？
        # 这里比较微妙，因为选手真的可能变成了自由人。
        # 如果你希望严格"抓不到才用旧的"，可以保留下面这行注释：
        # if self.team == "Free Agent" and old_info.team != "Free Agent": self.team = old_info.team

        # 2. 国籍
        if self.nationality == "未知国籍" and old_info.nationality != "未知国籍":
            self.nationality = old_info.nationality
            logger.info(f"  └─ [{self.name}] 国籍获取失败，保留旧数据: {self.nationality}")

        # 3. 年龄
        if self.age == "未知年龄" and old_info.age != "未知年龄":
            self.age = old_info.age
            logger.info(f"  └─ [{self.name}] 年龄获取失败，保留旧数据: {self.age}")

        # 4. 角色
        if self.role == "未知位置" and old_info.role != "未知位置":
            self.role = old_info.role
            logger.info(f"  └─ [{self.name}] 角色获取失败，保留旧数据: {self.role}")

class PlayersUpdater:
    """选手信息更新器"""

    def __init__(self):
        # 修改点1：使用 cloudscraper 替换 requests.Session
        # 它可以自动处理 Cloudflare 的 JS 验证
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        # 修改点2：Liquipedia 要求 User-Agent 包含联系方式，否则容易被封
        # 请将 your_email@example.com 替换为你真实的邮箱，或者保持原样试试
        self.headers = {
            'User-Agent': 'CS2PlayerDataBot/1.0 (scrapper_bot@gmail.com)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

        # 请求控制
        self.request_count = 0
        self.last_request_time = 0
        # 修改点3：增加延迟，避免触发 429 Too Many Requests
        self.min_delay = 2.0

    def _rate_limit(self):
        """请求频率控制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """安全的请求方法 (使用 cloudscraper)"""
        try:
            self._rate_limit()
            # 使用 scraper 发送请求
            response = self.scraper.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response
        except Exception as e:
            # 捕获所有请求异常
            logger.error(f"请求失败 {url}: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """清理文本数据"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'\[\[|\]\]', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        return text

    def _standardize_role(self, role: str) -> str:
        """标准化角色信息 (保持原有逻辑)"""
        if not role:
            return "未知位置"

        role_lower = role.lower()

        # 角色标准化映射
        role_mapping = {
            'rifler': 'Rifler', 'awper': 'AWPer', 'igl': 'Rifler',
            'in-game leader': 'Rifler', 'coach': 'Coach', 'assistant coach': 'Coach',
            'support': 'Support', 'lurker': 'Lurker', 'streamer': 'Free Agent',
            'broadcast analyst': 'Free Agent', 'analyst': 'Free Agent',
            'manager': 'Free Agent', 'player': 'Rifler', 'entry fragger': 'Rifler',
            'entry': 'Rifler', 'fragger': 'Rifler',
            'rifler/awper': 'Rifler', 'awper/rifler': 'AWPer',
            'lurker/support': 'Support', 'support/lurker': 'Support',
        }

        for key, value in role_mapping.items():
            if key in role_lower:
                return value

        return role.capitalize()

    def _extract_age_from_birth_date(self, birth_date: str) -> str:
        """从出生日期提取年龄"""
        try:
            year_patterns = [r'(\d{4})', r'born\s+(\d{4})', r'(\d{4})\s*年']
            for pattern in year_patterns:
                match = re.search(pattern, birth_date, re.IGNORECASE)
                if match:
                    birth_year = int(match.group(1))
                    current_year = datetime.now().year
                    age = current_year - birth_year
                    if 15 <= age <= 50:
                        return str(age)
            return "未知年龄"
        except (ValueError, TypeError):
            return "未知年龄"

    def load_existing_players(self, csv_file: str = "players.csv") -> Dict[str, PlayerInfo]:
        """
        修改点：读取CSV并返回 {姓名: PlayerInfo对象} 的字典
        这样我们在更新时可以查阅旧数据
        """
        existing_data = {}

        try:
            # 使用 utf-8-sig 以兼容 Excel 保存的 CSV (带BOM)
            with open(csv_file, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    name = row.get('姓名', '').strip()
                    if name:
                        existing_data[name] = PlayerInfo(
                            name=name,
                            team=row.get('队伍', 'Free Agent'),
                            nationality=row.get('国籍', '未知国籍'),
                            age=row.get('年龄', '未知年龄'),
                            role=row.get('游戏内位置', '未知位置')
                        )

            logger.info(f"从 {csv_file} 加载了 {len(existing_data)} 条旧数据存档")
            return existing_data
        except FileNotFoundError:
            logger.error(f"文件未找到: {csv_file}")
            return {}
        except Exception as e:
            logger.error(f"读取CSV文件失败: {e}")
            return {}

    def get_player_info_from_liquipedia(self, name: str) -> Optional[PlayerInfo]:
        """从Liquipedia获取选手最新信息"""
        # 处理特殊名字，Liquipedia URL对空格敏感
        url_name = name.replace(" ", "_")
        url = f"https://liquipedia.net/counterstrike/{url_name}"

        response = self._make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 简单校验页面有效性
        if "Liquipedia" not in soup.title.string:
            logger.warning(f"页面解析异常: {name}")
            return None

        try:
            # 提取姓名 (保持原名)

            # 提取队伍
            team_elem = soup.find('div', class_='infobox-cell-2', string='Team:')
            team = "Free Agent"
            if team_elem:
                team_div = team_elem.find_next('div')
                if team_div:
                    team = self._clean_text(team_div.text)

            # 提取国籍
            nationality_elem = soup.find('div', class_='infobox-cell-2', string='Nationality:')
            nationality = "未知国籍"
            if nationality_elem:
                nationality_div = nationality_elem.find_next('div')
                if nationality_div:
                    nationality = self._clean_text(nationality_div.text)

            # 提取年龄
            birth_elem = soup.find('div', class_='infobox-cell-2', string='Born:')
            age = "未知年龄"
            if birth_elem:
                birth_div = birth_elem.find_next('div')
                if birth_div:
                    birth_date = self._clean_text(birth_div.text)
                    age = self._extract_age_from_birth_date(birth_date)

            # 提取角色
            role_elem = soup.find('div', class_='infobox-cell-2', string='Role:')
            role = "未知位置"
            if role_elem:
                role_div = role_elem.find_next('div')
                if role_div:
                    raw_role = self._clean_text(role_div.text)
                    role = self._standardize_role(raw_role)

            # 如果Liquipedia没找到角色，尝试本地逻辑（为了代码简洁，去掉了HLTV请求，因为HLTV反爬更严）
            if role == "未知位置":
                local_role = self._get_role_from_local_database(name)
                if local_role:
                    role = local_role

            return PlayerInfo(name=name, team=team, nationality=nationality, age=age, role=role)

        except Exception as e:
            logger.error(f"解析选手信息失败 {name}: {e}")
            return None
    
    def _get_role_from_local_database(self, name: str) -> Optional[str]:
        """从本地角色数据库获取选手角色信息"""
        # 知名选手的角色数据库
        player_roles = {
            # 顶级AWPer
            "s1mple": "AWPer",
            "ZywOo": "AWPer", 
            "sh1ro": "AWPer",
            "broky": "AWPer",
            "torzsi": "AWPer",
            "m0NESY": "AWPer",
            "Jame": "AWPer",
            "SunPayus": "AWPer",
            "w0nderful": "AWPer",
            "nicoodoz": "AWPer",
            "acoR": "AWPer",
            "syrsoN": "AWPer",
            "kennyS": "AWPer",
            "GuardiaN": "AWPer",
            "JW": "AWPer",
            "Skadoodle": "AWPer",
            "FalleN": "AWPer",
            "HEN1": "AWPer",
            "saffee": "AWPer",
            "Gratisfaction": "AWPer",
            "oskar": "AWPer",
            "allu": "AWPer",
            "ottoNd": "AWPer",
            "phzy": "AWPer",
            "story": "AWPer",
            "Jee": "AWPer",
            "sl3nd": "AWPer",
            "910": "AWPer",
            "WorldEdit": "AWPer",
            
            # 顶级Rifler
            "NiKo": "Rifler",
            "dev1ce": "AWPer",  # 虽然主要是AWPer，但也会用步枪
            "electronic": "Rifler",
            "b1t": "Rifler",
            "ropz": "Rifler",
            "rain": "Rifler",
            "karrigan": "Rifler",  # IGL
            "tabseN": "Rifler",
            "stavn": "Rifler",
            "cadiaN": "Rifler",  # IGL
            "TeSeS": "Rifler",
            "sjuush": "Rifler",
            "refrezh": "Rifler",
            "blameF": "Rifler",
            "k0nfig": "Rifler",
            "valde": "Rifler",
            "jabbi": "Rifler",
            "Spinx": "Rifler",
            "flamie": "Rifler",
            "sdy": "Rifler",
            "degster": "AWPer",
            "patsi": "Rifler",
            "r1nkle": "AWPer",
            "headtr1ck": "AWPer",
            "Mir": "Rifler",
            "FL1T": "Rifler",
            "Qikert": "Rifler",
            "Buster": "Rifler",
            "Edward": "Rifler",
            "TaZ": "Coach",
            "pasha": "Rifler",
            "byali": "Rifler",
            "fer": "Rifler",
            "TACO": "Rifler",
            "fnx": "Rifler",
            "LUCAS1": "Rifler",
            "kscerato": "Rifler",
            "yuurih": "Rifler",
            "arT": "Rifler",
            "VINI": "Rifler",
            "drop": "Rifler",
            "chelo": "Rifler",
            "biguzera": "Rifler",
            "felps": "Rifler",
            "Boltz": "Rifler",
            "MalbsMd": "Rifler",
            "chrisJ": "AWPer",
            "STYKO": "Rifler",
            "ISSAA": "Rifler",
            "woxic": "AWPer",
            "XANTARES": "Rifler",
            "Calyx": "Rifler",
            "MAJ3R": "Rifler",
            "hampus": "Rifler",
            "nawwk": "AWPer",
            "Golden": "Coach",
            "REZ": "Rifler",
            "Brollan": "Rifler",
            "es3tag": "Rifler",
            "allu": "AWPer",
            "sergej": "Rifler",
            "Aleksib": "Rifler",  # IGL
            "suNny": "Rifler",
            "jks": "Rifler",
            "AZR": "Rifler",
            "Liazz": "Rifler",
            "INS": "Rifler",
            "BnTeT": "Rifler",
            "LETN1": "Coach",
            "RUSH": "Rifler",
            "Ex6TenZ": "Coach",
            "SmithZz": "Coach",
            "RpK": "Rifler",
            "bodyy": "Rifler",
            "NBK": "Rifler",
            "apEX": "Rifler",
            "Happy": "Rifler",
            "KioShiMa": "Rifler",
            "Zonic": "Coach",
            "dennis": "Rifler",
            "twist": "Rifler",
            "Lekr0": "Rifler",
            "aizy": "Rifler",
            "MSL": "Rifler",
            "cajunb": "Rifler",
            "TenZ": "Rifler",
            "s0m": "Rifler",
            "smooya": "AWPer",
            "Grim": "Rifler",
            "floppy": "Rifler",
            "oSee": "AWPer",
            "junior": "AWPer",
            "ztr": "Rifler",
            "frozen": "Rifler",
            "huNter": "Rifler",
            "NertZ": "Rifler",
            "jL": "Rifler",
            "Summer": "Rifler",
            "Starry": "Rifler",
            "EliGE": "Rifler",
            "magixx": "Rifler",
            "chopper": "Rifler",
            "zont1x": "Rifler",
            "siuhy": "Rifler",
            "bLitz": "Rifler",
            "Techno": "Rifler",
            "Senzu": "Rifler",
            "mzinho": "Rifler",
            "Wicadia": "Rifler",
            "HeavyGod": "Rifler",
            "flameZ": "Rifler",
            "mezii": "Rifler",
            "jottAAA": "Rifler",
            "iM": "Rifler",
            "kyxsan": "Rifler",
            "Maka": "Rifler",
            "Staehr": "Rifler",
            "FL4MUS": "Rifler",
            "fame": "Rifler",
            "ICY": "AWPer",
            "ultimate": "AWPer",
            "snow": "Rifler",
            "nqz": "AWPer",
            "Tauson": "Rifler",
            "PR": "Rifler",
            "skullz": "Rifler",
            "exit": "Rifler",
            "Lucaozy": "Rifler",
            "brnz4n": "Rifler",
            "insani": "Rifler",
            "JBa": "Rifler",
            "LNZ": "Rifler",
            "JDC": "Rifler",
            "fear": "Rifler",
            "somebody": "Rifler",
            "CYPHER": "Rifler",
            "jkaem": "Rifler",
            "kaze": "AWPer",
            "ChildKing": "Rifler",
            "L1haNg": "Rifler",
            "Attacker": "Rifler",
            "JamYoung": "Rifler",
            "Mercury": "Rifler",
            "Moseyuh": "Rifler",
            "Westmelon": "Rifler",
            "z4kr": "Rifler",
            "EmiliaQAQ": "Rifler",
            "C4LLM3SU3": "Rifler",
            "xertioN": "Rifler",
            
            # 经典选手
            "coldzera": "Rifler",
            "f0rest": "Rifler",
            "GeT_RiGhT": "Rifler",
            "olofmeister": "Rifler",
            "Snax": "Rifler",
            "shox": "Rifler",
            "KRIMZ": "Rifler",
            "flusha": "Rifler",
            "Xyp9x": "Coach",
            "dupreeh": "Rifler",
            "gla1ve": "Rifler",
            "magisk": "Rifler",
            "Boombl4": "Rifler",
            "Perfecto": "Rifler",
            "donk": "Rifler",
            "Ax1Le": "Rifler",
            "nafany": "Rifler",
            "Stewie2K": "Rifler",
            "twistzz": "Rifler",
            "NAF": "Rifler",
            "nitr0": "Rifler",
            "tarik": "Rifler",
            "autimatic": "Rifler",
            "Hiko": "Rifler",
            "daps": "Coach",
            "stanislaw": "Rifler",
            "Brehze": "Rifler",
            "Ethan": "Rifler",
            "dycha": "Rifler",
            "hades": "AWPer",
            "mantuu": "AWPer",
            "gade": "Rifler",
            "valde": "Rifler",
            "acoR": "AWPer",
            "jabbi": "Rifler",
            "nicoodoz": "AWPer",
            "flamie": "Rifler",
            "sdy": "Rifler",
            "degster": "AWPer",
            "patsi": "Rifler",
            "r1nkle": "AWPer",
            "headtr1ck": "AWPer",
            "Mir": "Rifler",
            "Jame": "AWPer",
            "FL1T": "Rifler",
            "Qikert": "Rifler",
            "Buster": "Rifler",
            "WorldEdit": "AWPer",
            "Edward": "Rifler",
            "pasha": "Rifler",
            "byali": "Rifler",
            "FalleN": "AWPer",
            "fer": "Rifler",
            "TACO": "Rifler",
            "fnx": "Rifler",
            "LUCAS1": "Rifler",
            "HEN1": "AWPer",
            "kscerato": "Rifler",
            "yuurih": "Rifler",
            "arT": "Rifler",
            "VINI": "Rifler",
            "saffee": "AWPer",
            "drop": "Rifler",
            "chelo": "Rifler",
            "biguzera": "Rifler",
            "felps": "Rifler",
            "zews": "Coach",
            "Boltz": "Rifler",
            "MalbsMd": "Rifler",
            "chrisJ": "AWPer",
            "oskar": "AWPer",
            "STYKO": "Rifler",
            "ISSAA": "Rifler",
            "woxic": "AWPer",
            "XANTARES": "Rifler",
            "Calyx": "Rifler",
            "MAJ3R": "Rifler",
            "hampus": "Rifler",
            "nawwk": "AWPer",
            "Golden": "Coach",
            "REZ": "Rifler",
            "Brollan": "Rifler",
            "es3tag": "Rifler",
            "ottoNd": "AWPer",
            "allu": "AWPer",
            "sergej": "Rifler",
            "suNny": "Rifler",
            "jks": "Rifler",
            "AZR": "Rifler",
            "Gratisfaction": "AWPer",
            "Liazz": "Rifler",
            "INS": "Rifler",
            "BnTeT": "Rifler",
            "LETN1": "Coach",
            "RUSH": "Rifler",
            "Ex6TenZ": "Coach",
            "SmithZz": "Coach",
            "RpK": "Rifler",
            "bodyy": "Rifler",
            "NBK": "Rifler",
            "apEX": "Rifler",
            "Happy": "Rifler",
            "KioShiMa": "Rifler",
            "Zonic": "Coach",
            "dennis": "Rifler",
            "twist": "Rifler",
            "Lekr0": "Rifler",
            "aizy": "Rifler",
            "MSL": "Rifler",
            "cajunb": "Rifler",
            "TenZ": "Rifler",
            "s0m": "Rifler",
            "smooya": "AWPer",
            "Grim": "Rifler",
            "floppy": "Rifler",
            "oSee": "AWPer",
            "junior": "AWPer",
            "ztr": "Rifler",
            "frozen": "Rifler",
            "huNter": "Rifler",
            "NertZ": "Rifler",
            "SunPayus": "AWPer",
            "jL": "Rifler",
            "Summer": "Rifler",
            "Starry": "Rifler",
            "EliGE": "Rifler",
            "magixx": "Rifler",
            "chopper": "Rifler",
            "zont1x": "Rifler",
            "siuhy": "Rifler",
            "bLitz": "Rifler",
            "Techno": "Rifler",
            "Senzu": "Rifler",
            "mzinho": "Rifler",
            "Wicadia": "Rifler",
            "HeavyGod": "Rifler",
            "flameZ": "Rifler",
            "mezii": "Rifler",
            "jottAAA": "Rifler",
            "iM": "Rifler",
            "w0nderful": "AWPer",
            "kyxsan": "Rifler",
            "Maka": "Rifler",
            "Staehr": "Rifler",
            "FL4MUS": "Rifler",
            "fame": "Rifler",
            "ICY": "AWPer",
            "ultimate": "AWPer",
            "snow": "Rifler",
            "nqz": "AWPer",
            "Tauson": "Rifler",
            "sl3nd": "AWPer",
            "PR": "Rifler",
            "story": "AWPer",
            "skullz": "Rifler",
            "exit": "Rifler",
            "Lucaozy": "Rifler",
            "brnz4n": "Rifler",
            "insani": "Rifler",
            "phzy": "AWPer",
            "JBa": "Rifler",
            "nicoodoz": "AWPer",
            "LNZ": "Rifler",
            "JDC": "Rifler",
            "fear": "Rifler",
            "somebody": "Rifler",
            "CYPHER": "Rifler",
            "jkaem": "Rifler",
            "kaze": "AWPer",
            "ChildKing": "Rifler",
            "L1haNg": "Rifler",
            "Attacker": "Rifler",
            "JamYoung": "Rifler",
            "Jee": "AWPer",
            "Mercury": "Rifler",
            "Moseyuh": "Rifler",
            "Westmelon": "Rifler",
            "z4kr": "Rifler",
            "EmiliaQAQ": "Rifler",
            "C4LLM3SU3": "Rifler",
            "xertioN": "Rifler",
        }
        
        # 查找选手角色
        if name in player_roles:
            role = player_roles[name]
            logger.info(f"从本地数据库获取角色: {name} - {role}")
            return role
        
        return None

    def update_players_info(self, existing_data: Dict[str, PlayerInfo], output_file: str = "updated_players.csv", max_players: int = None) -> List[PlayerInfo]:
        """更新选手信息 (带合并逻辑)"""
        updated_players_list = []
        player_names = list(existing_data.keys())

        if max_players:
            player_names = player_names[:max_players]

        total_players = len(player_names)
        logger.info(f"开始更新 {total_players} 个选手的信息...")

        for i, name in enumerate(player_names, 1):
            logger.info(f"正在处理 ({i}/{total_players}): {name}")

            # 1. 获取新数据
            new_info = self.get_player_info_from_liquipedia(name)

            # 2. 如果获取成功，进行合并
            if new_info:
                old_info = existing_data.get(name)
                # 核心步骤：如果新数据是"未知"，则使用旧数据
                new_info.merge_old_data(old_info)

                updated_players_list.append(new_info)
                logger.info(f"✓ 更新成功: {name} -> {new_info.team}")
            else:
                # 3. 如果完全抓取失败（比如404），直接使用旧数据（如果存在）
                old_info = existing_data.get(name)
                if old_info:
                    updated_players_list.append(old_info)
                    logger.warning(f"✗ 抓取失败，使用旧数据存档: {name}")
                else:
                    logger.error(f"✗ 抓取失败且无旧数据: {name}")

            if i % 10 == 0:
                logger.info(f"进度: {i}/{total_players} ({i/total_players*100:.1f}%)")

        return updated_players_list

    def save_updated_players(self, players: List[PlayerInfo], filename: str):
        """保存更新后的选手信息"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as file:
            fieldnames = ['姓名', '队伍', '国籍', '年龄', '游戏内位置']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for player in players:
                writer.writerow(player.to_dict())
        logger.info(f"已保存 {len(players)} 个选手信息到 {filepath}")

    # ... (generate_update_report 方法保持不变，可以直接复制原来的) ...
    def generate_update_report(self, original_count: int, updated_count: int, players: List[PlayerInfo]):
        # 为了简洁，这里省略代码，逻辑与你原代码一致
        pass

def main():
    """主函数"""
    import sys

    max_players = None
    if len(sys.argv) > 1:
        try:
            max_players = int(sys.argv[1])
        except ValueError:
            pass

    updater = PlayersUpdater()

    # 1. 加载已有数据 (现在返回的是字典)
    existing_data = updater.load_existing_players("players.csv")
    if not existing_data:
        return

    # 2. 更新信息 (传入整个字典以便合并)
    updated_players = updater.update_players_info(existing_data, "updated_players.csv", max_players)

    # 3. 保存
    updater.save_updated_players(updated_players, "updated_players.csv")

    # 4. 报告 (此处稍微调整参数匹配)
    updater.generate_update_report(len(existing_data), len(updated_players), updated_players)

if __name__ == "__main__":
    main()