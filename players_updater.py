#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CS2选手信息更新器
专门用于更新players.csv文件中已有选手的最新信息
"""

import requests
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

class PlayersUpdater:
    """选手信息更新器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.hltv.org/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0',
        })
        
        # 请求控制
        self.request_count = 0
        self.last_request_time = 0
        self.min_delay = 1.0
        
    def _rate_limit(self):
        """请求频率控制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_request(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        """安全的请求方法"""
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败 {url}: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """清理文本数据"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除Wiki链接标记
        text = re.sub(r'\[\[|\]\]', '', text)
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        return text
    
    def _standardize_role(self, role: str) -> str:
        """标准化角色信息"""
        if not role:
            return "未知位置"
        
        role_lower = role.lower()
        
        # 角色标准化映射
        role_mapping = {
            # 标准角色
            'rifler': 'Rifler',
            'awper': 'AWPer',
            'igl': 'Rifler',  # In-game leader归类为Rifler
            'in-game leader': 'Rifler',
            'coach': 'Coach',
            'assistant coach': 'Coach',  # Assistant Coach归类为Coach
            'support': 'Support',
            'lurker': 'Lurker',
            
            # 特殊角色归类
            'streamer': 'Free Agent',  # Streamer归类为Free Agent
            'broadcast analyst': 'Free Agent',  # Broadcast Analyst归类为Free Agent
            'analyst': 'Free Agent',
            'manager': 'Free Agent',
            'player': 'Rifler',
            'entry fragger': 'Rifler',
            'entry': 'Rifler',
            'fragger': 'Rifler',
            'rifler/awper': 'Rifler',
            'awper/rifler': 'AWPer',
            'lurker/support': 'Support',
            'support/lurker': 'Support',
        }
        
        # 查找匹配的角色
        for key, value in role_mapping.items():
            if key in role_lower:
                return value
        
        # 如果没有匹配，返回原始角色（首字母大写）
        return role.capitalize()
    
    def _extract_age_from_birth_date(self, birth_date: str) -> str:
        """从出生日期提取年龄"""
        try:
            # 匹配年份模式
            year_patterns = [
                r'(\d{4})',  # 标准4位年份
                r'born\s+(\d{4})',  # born 1995
                r'(\d{4})\s*年',  # 1995年
            ]
            
            for pattern in year_patterns:
                match = re.search(pattern, birth_date, re.IGNORECASE)
                if match:
                    birth_year = int(match.group(1))
                    current_year = datetime.now().year
                    age = current_year - birth_year
                    
                    if 15 <= age <= 50:  # 合理的年龄范围
                        return str(age)
            
            return "未知年龄"
        except (ValueError, TypeError) as e:
            logger.warning(f"年龄解析失败: {birth_date} - {e}")
            return "未知年龄"
    
    def load_existing_players(self, csv_file: str = "players.csv") -> List[str]:
        """从CSV文件加载已有选手姓名"""
        player_names = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    player_names.append(row['姓名'])
            
            logger.info(f"从 {csv_file} 加载了 {len(player_names)} 个选手姓名")
            return player_names
        except FileNotFoundError:
            logger.error(f"文件未找到: {csv_file}")
            return []
        except Exception as e:
            logger.error(f"读取CSV文件失败: {e}")
            return []
    
    def get_player_info_from_liquipedia(self, name: str) -> Optional[PlayerInfo]:
        """从Liquipedia获取选手最新信息"""
        url = f"https://liquipedia.net/counterstrike/{name}"
        
        response = self._make_request(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 检查是否为选手页面
        if not soup.find('div', class_='infobox-cell-2', string='Nationality:'):
            logger.warning(f"不是有效的选手页面: {name}")
            return None
        
        try:
            # 提取姓名
            name_elem = soup.find('h1', class_='firstHeading')
            name = self._clean_text(name_elem.text) if name_elem else ""
            
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
            
            # 如果角色是未知位置，尝试从HLTV获取
            if role == "未知位置":
                logger.info(f"Liquipedia角色未知，尝试从HLTV获取: {name}")
                hltv_role = self._get_role_from_hltv(name)
                if hltv_role and hltv_role != "未知位置":
                    role = hltv_role
                    logger.info(f"从HLTV获取到角色: {name} - {role}")
            
            return PlayerInfo(name=name, team=team, nationality=nationality, age=age, role=role)
            
        except Exception as e:
            logger.error(f"解析选手信息失败 {name}: {e}")
            return None
    
    def _get_role_from_hltv(self, name: str) -> Optional[str]:
        """从HLTV获取选手角色信息（备选：使用本地角色数据库）"""
        try:
            # 首先尝试从HLTV获取（可能被阻止）
            player_url = f"https://www.hltv.org/stats/players/{name.lower()}"
            response = self._make_request(player_url)
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                role = self._extract_role_from_hltv_page(soup, name)
                if role and role != "未知位置":
                    return self._standardize_role(role)
            
            # 如果HLTV失败，使用本地角色数据库
            return self._get_role_from_local_database(name)
            
        except Exception as e:
            logger.warning(f"从HLTV获取角色失败 {name}: {e}")
            # 使用本地数据库作为备选
            return self._get_role_from_local_database(name)
    
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
    
    def _extract_role_from_hltv_page(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        """从HLTV页面提取角色信息"""
        try:
            # 方法1: 从页面文本中查找角色关键词
            page_text = soup.get_text().lower()
            
            # 关键词匹配
            if "awper" in page_text or "sniper" in page_text or "awp" in page_text:
                return "AWPer"
            elif "rifler" in page_text or "entry" in page_text or "fragger" in page_text:
                return "Rifler"
            elif "igl" in page_text or "leader" in page_text or "in-game leader" in page_text:
                return "Rifler"  # IGL归类为Rifler
            elif "support" in page_text:
                return "Support"
            elif "lurker" in page_text:
                return "Lurker"
            elif "coach" in page_text:
                return "Coach"
            
            # 方法2: 从武器使用统计推断
            weapon_elements = soup.find_all(text=lambda text: text and any(weapon in text.lower() for weapon in ["awp", "ak", "m4", "famas", "galil"]))
            if weapon_elements:
                awp_count = sum(1 for elem in weapon_elements if "awp" in elem.lower())
                rifle_count = sum(1 for elem in weapon_elements if any(rifle in elem.lower() for rifle in ["ak", "m4", "famas", "galil"]))
                
                if awp_count > rifle_count:
                    return "AWPer"
                elif rifle_count > 0:
                    return "Rifler"
            
            # 方法3: 从选手描述中查找
            description_elements = soup.find_all(["p", "div", "span"], class_=lambda x: x and any(keyword in x.lower() for keyword in ["description", "info", "bio", "about"]))
            for elem in description_elements:
                text = elem.get_text().lower()
                if "awper" in text or "sniper" in text:
                    return "AWPer"
                elif "rifler" in text or "entry" in text:
                    return "Rifler"
                elif "igl" in text or "leader" in text:
                    return "Rifler"
                elif "support" in text:
                    return "Support"
                elif "lurker" in text:
                    return "Lurker"
            
            return None
            
        except Exception as e:
            logger.warning(f"从HLTV页面提取角色失败 {name}: {e}")
            return None
    
    def update_players_info(self, player_names: List[str], output_file: str = "updated_players.csv", max_players: int = None) -> List[PlayerInfo]:
        """更新选手信息"""
        updated_players = []
        
        # 如果指定了最大数量，则只处理前N个选手
        if max_players:
            player_names = player_names[:max_players]
        
        total_players = len(player_names)
        
        logger.info(f"开始更新 {total_players} 个选手的信息...")
        
        for i, name in enumerate(player_names, 1):
            logger.info(f"正在处理 ({i}/{total_players}): {name}")
            
            player_info = self.get_player_info_from_liquipedia(name)
            if player_info:
                updated_players.append(player_info)
                logger.info(f"✓ 成功更新: {name} - {player_info.team}")
            else:
                logger.warning(f"✗ 更新失败: {name}")
            
            # 每处理10个选手显示一次进度
            if i % 10 == 0:
                logger.info(f"进度: {i}/{total_players} ({i/total_players*100:.1f}%)")
        
        logger.info(f"更新完成！成功更新 {len(updated_players)}/{total_players} 个选手")
        return updated_players
    
    def save_updated_players(self, players: List[PlayerInfo], filename: str):
        """保存更新后的选手信息"""
        if not players:
            logger.warning("没有选手数据可保存")
            return
        
        # 确保输出目录存在
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['姓名', '队伍', '国籍', '年龄', '游戏内位置']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            
            for player in players:
                writer.writerow(player.to_dict())
        
        logger.info(f"已保存 {len(players)} 个选手信息到 {filepath}")
    
    def generate_update_report(self, original_count: int, updated_count: int, players: List[PlayerInfo]):
        """生成更新报告"""
        if not players:
            return
        
        # 统计信息
        players_with_age = sum(1 for p in players if p.age != "未知年龄")
        players_with_team = sum(1 for p in players if p.team != "Free Agent")
        players_with_role = sum(1 for p in players if p.role != "未知位置")
        
        # 国籍统计
        nationality_count = {}
        for player in players:
            nationality = player.nationality
            nationality_count[nationality] = nationality_count.get(nationality, 0) + 1
        
        # 角色统计
        role_count = {}
        for player in players:
            role = player.role
            role_count[role] = role_count.get(role, 0) + 1
        
        # 生成报告
        report = f"""
CS2选手信息更新报告
==================
原始选手数: {original_count}
成功更新数: {updated_count}
更新成功率: {updated_count/original_count*100:.1f}%

数据完整性:
- 有年龄信息的选手: {players_with_age} ({players_with_age/updated_count*100:.1f}%)
- 有队伍信息的选手: {players_with_team} ({players_with_team/updated_count*100:.1f}%)
- 有角色信息的选手: {players_with_role} ({players_with_role/updated_count*100:.1f}%)

国籍分布 (Top 10):
"""
        
        # 按数量排序国籍
        sorted_nationalities = sorted(nationality_count.items(), key=lambda x: x[1], reverse=True)
        for nationality, count in sorted_nationalities[:10]:
            report += f"{nationality}: {count} ({count/updated_count*100:.1f}%)\n"
        
        report += "\n角色分布:\n"
        for role, count in role_count.items():
            report += f"{role}: {count} ({count/updated_count*100:.1f}%)\n"
        
        # 保存报告
        with open("output/update_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info("更新报告已生成: output/update_report.txt")
        print(report)

def main():
    """主函数"""
    import sys
    
    # 检查命令行参数
    max_players = None
    if len(sys.argv) > 1:
        try:
            max_players = int(sys.argv[1])
            logger.info(f"将只更新前 {max_players} 个选手")
        except ValueError:
            logger.warning("无效的参数，将更新所有选手")
    
    logger.info("开始CS2选手信息更新")
    
    updater = PlayersUpdater()
    
    # 1. 加载已有选手姓名
    player_names = updater.load_existing_players("players.csv")
    if not player_names:
        logger.error("没有找到选手数据，程序退出")
        return
    
    # 2. 更新选手信息
    updated_players = updater.update_players_info(player_names, "updated_players.csv", max_players)
    
    # 3. 保存更新后的数据
    updater.save_updated_players(updated_players, "updated_players.csv")
    
    # 4. 生成更新报告
    original_count = len(player_names) if not max_players else min(max_players, len(player_names))
    updater.generate_update_report(original_count, len(updated_players), updated_players)
    
    logger.info("选手信息更新任务完成")

if __name__ == "__main__":
    main() 