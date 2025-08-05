import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import csv
import random
import os
import re
import json
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import urljoin, urlparse
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PlayerInfo:
    """选手信息数据类"""
    name: str
    team: str = "自由选手"
    nationality: str = "未知国籍"
    age: str = "未知年龄"
    role: str = "未知位置"
    source: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        return {
            '姓名': self.name,
            '队伍': self.team,
            '国籍': self.nationality,
            '年龄': str(self.age),
            '游戏内位置': self.role
        }

class CS2PlayerCrawler:
    """CS2选手信息爬虫类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 请求控制
        self.request_count = 0
        self.last_request_time = 0
        self.min_delay = 1.0
        self.max_delay = 3.0
        
        # 数据验证规则
        self.valid_roles = {'rifler', 'awper', 'igl', 'coach', 'support', 'lurker'}
        self.valid_nationalities = {
            'china', 'united states', 'russia', 'ukraine', 'denmark', 'sweden',
            'poland', 'france', 'germany', 'norway', 'estonia', 'latvia',
            'brazil', 'canada', 'israel', 'kazakhstan', 'netherlands', 'guatemala'
        }
        
    def _rate_limit(self):
        """智能请求频率控制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)
        
        # 动态调整延迟
        if self.request_count % 50 == 0:
            self.min_delay = min(2.0, self.min_delay + 0.1)
            logger.info(f"调整请求延迟为: {self.min_delay}s")
        
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
    
    def _validate_player_info(self, player: PlayerInfo) -> bool:
        """验证选手信息"""
        if not player.name or len(player.name.strip()) < 2:
            return False
        
        # 验证年龄
        if isinstance(player.age, int) and (player.age < 15 or player.age > 50):
            logger.warning(f"年龄异常: {player.name} - {player.age}")
            player.age = "未知年龄"
        
        # 验证角色
        if player.role.lower() not in self.valid_roles:
            player.role = "未知位置"
        
        return True
    
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
    
    def crawl_liquipedia_by_region(self) -> List[PlayerInfo]:
        """从Liquipedia按地区爬取选手信息"""
        region_urls = {
            "Europe": "https://liquipedia.net/counterstrike/Portal:Players/Europe",
            "CIS": "https://liquipedia.net/counterstrike/Portal:Players/CIS",
            "Americas": "https://liquipedia.net/counterstrike/Portal:Players/Americas",
            "Oceania": "https://liquipedia.net/counterstrike/Portal:Players/Oceania",
            "Asia": "https://liquipedia.net/counterstrike/Portal:Players/Asia",
            "Africa & Middle East": "https://liquipedia.net/counterstrike/Portal:Players/Africa_&_Middle_East"
        }
        
        all_players = []
        
        for region, url in region_urls.items():
            logger.info(f"正在处理地区: {region}")
            
            response = self._make_request(url)
            if not response:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table', class_='wikitable')
            
            region_players = []
            for table in tables:
                links = table.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if (href.startswith('/counterstrike/') and
                            href.count('/') == 2 and
                            ' ' not in link.text.strip() and
                            len(link.text.strip()) < 15):
                        region_players.append(link)
            
            logger.info(f"{region} 找到 {len(region_players)} 个选手链接")
            all_players.extend(region_players)
        
        return self._process_player_links(all_players, "Liquipedia")
    
    def crawl_hltv_top500(self) -> List[PlayerInfo]:
        """从HLTV爬取Top 500选手"""
        hltv_url = "https://www.hltv.org/stats/players?start=0&limit=500"
        
        response = self._make_request(hltv_url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        player_names = []
        
        for row in soup.select('table.stats-table tbody tr'):
            name_elem = row.find('a', class_='player-nick')
            if name_elem:
                name = self._clean_text(name_elem.text)
                if name:
                    player_names.append(name)
        
        logger.info(f"从HLTV找到 {len(player_names)} 个Top选手")
        return self._process_player_names(player_names, "HLTV")
    
    def crawl_famous_players(self) -> List[PlayerInfo]:
        """爬取知名选手信息"""
        famous_players = [
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
        
        return self._process_player_names(famous_players, "Famous")
    
    def _process_player_links(self, links: List, source: str) -> List[PlayerInfo]:
        """处理选手链接列表"""
        players = []
        
        for link in links:
            player_url = "https://liquipedia.net" + link['href']
            player_info = self._get_player_info_from_liquipedia(player_url)
            if player_info:
                player_info.source = source
                if self._validate_player_info(player_info):
                    players.append(player_info)
        
        return players
    
    def _process_player_names(self, names: List[str], source: str) -> List[PlayerInfo]:
        """处理选手姓名列表"""
        players = []
        
        for name in names:
            player_info = self._get_player_info_by_name(name)
            if player_info:
                player_info.source = source
                if self._validate_player_info(player_info):
                    players.append(player_info)
        
        return players
    
    def _get_player_info_from_liquipedia(self, url: str) -> Optional[PlayerInfo]:
        """从Liquipedia页面获取选手信息"""
        response = self._make_request(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 检查是否为选手页面
        if not soup.find('div', class_='infobox-cell-2', string='Nationality:'):
            return None
        
        try:
            # 提取姓名
            name_elem = soup.find('h1', class_='firstHeading')
            name = self._clean_text(name_elem.text) if name_elem else ""
            
            # 提取队伍
            team_elem = soup.find('div', class_='infobox-cell-2', string='Team:')
            team = "自由选手"
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
                    role = self._clean_text(role_div.text)
            
            return PlayerInfo(name=name, team=team, nationality=nationality, age=age, role=role)
            
        except Exception as e:
            logger.error(f"解析选手信息失败 {url}: {e}")
            return None
    
    def _get_player_info_by_name(self, name: str) -> Optional[PlayerInfo]:
        """通过姓名获取选手信息"""
        # 尝试从Liquipedia获取
        liquipedia_url = f"https://liquipedia.net/counterstrike/{name}"
        player_info = self._get_player_info_from_liquipedia(liquipedia_url)
        
        if player_info:
            return player_info
        
        # 如果Liquipedia没有，尝试从HLTV获取基本信息
        return self._get_player_info_from_hltv(name)
    
    def _get_player_info_from_hltv(self, name: str) -> Optional[PlayerInfo]:
        """从HLTV获取选手基本信息"""
        search_url = f"https://www.hltv.org/search?query={name}"
        
        response = self._make_request(search_url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        player_link = soup.find("a", class_="player-nick")
        
        if not player_link:
            return None
        
        player_url = "https://www.hltv.org" + player_link['href']
        player_response = self._make_request(player_url)
        
        if not player_response:
            return None
        
        player_soup = BeautifulSoup(player_response.text, 'html.parser')
        
        # HLTV信息提取（简化版）
        team = "自由选手"
        nationality = "未知国籍"
        age = "未知年龄"
        role = "未知位置"
        
        # 尝试提取队伍信息
        team_elem = player_soup.find("div", class_="player-info")
        if team_elem:
            team_text = team_elem.get_text()
            # 简单的队伍信息提取逻辑
            if "team" in team_text.lower():
                team = "活跃选手"  # HLTV通常不显示具体队伍
        
        return PlayerInfo(name=name, team=team, nationality=nationality, age=age, role=role)
    
    def save_to_csv(self, players: List[PlayerInfo], filename: str):
        """保存选手信息到CSV文件"""
        if not players:
            logger.warning("没有选手数据可保存")
            return
        
        # 确保输出目录存在
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        
        # 检查已存在的数据
        existing_players = set()
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    existing_players.add(row['姓名'])
        
        # 写入新数据
        with open(filepath, 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['姓名', '队伍', '国籍', '年龄', '游戏内位置']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            # 如果文件为空，写入表头
            if filepath.stat().st_size == 0:
                writer.writeheader()
            
            new_count = 0
            for player in players:
                if player.name not in existing_players:
                    writer.writerow(player.to_dict())
                    new_count += 1
                    existing_players.add(player.name)
            
            logger.info(f"保存了 {new_count} 个新选手信息到 {filepath}")
    
    def merge_and_deduplicate(self, players_list: List[List[PlayerInfo]]) -> List[PlayerInfo]:
        """合并并去重选手信息"""
        all_players = {}
        
        for players in players_list:
            for player in players:
                if player.name not in all_players:
                    all_players[player.name] = player
                else:
                    # 如果已存在，选择信息更完整的版本
                    existing = all_players[player.name]
                    if (player.age != "未知年龄" and existing.age == "未知年龄") or \
                       (player.team != "自由选手" and existing.team == "自由选手"):
                        all_players[player.name] = player
        
        return list(all_players.values())

def main():
    """主函数"""
    logger.info("开始CS2选手信息爬取")
    
    crawler = CS2PlayerCrawler()
    
    # 爬取不同来源的数据
    all_players = []
    
    # 1. 爬取Liquipedia地区数据
    try:
        logger.info("开始爬取Liquipedia地区数据...")
        liquipedia_players = crawler.crawl_liquipedia_by_region()
        all_players.append(liquipedia_players)
        logger.info(f"Liquipedia地区数据爬取完成，获得 {len(liquipedia_players)} 个选手")
    except Exception as e:
        logger.error(f"Liquipedia地区数据爬取失败: {e}")
    
    # 2. 爬取HLTV Top 500
    try:
        logger.info("开始爬取HLTV Top 500数据...")
        hltv_players = crawler.crawl_hltv_top500()
        all_players.append(hltv_players)
        logger.info(f"HLTV Top 500数据爬取完成，获得 {len(hltv_players)} 个选手")
    except Exception as e:
        logger.error(f"HLTV Top 500数据爬取失败: {e}")
    
    # 3. 爬取知名选手
    try:
        logger.info("开始爬取知名选手数据...")
        famous_players = crawler.crawl_famous_players()
        all_players.append(famous_players)
        logger.info(f"知名选手数据爬取完成，获得 {len(famous_players)} 个选手")
    except Exception as e:
        logger.error(f"知名选手数据爬取失败: {e}")
    
    # 合并并去重
    final_players = crawler.merge_and_deduplicate(all_players)
    logger.info(f"合并后共有 {len(final_players)} 个唯一选手")
    
    # 保存数据
    crawler.save_to_csv(final_players, "cs2_players_optimized.csv")
    
    # 生成统计报告
    generate_report(final_players)
    
    logger.info("爬取任务完成")

def generate_report(players: List[PlayerInfo]):
    """生成数据统计报告"""
    if not players:
        return
    
    # 统计信息
    total_players = len(players)
    players_with_age = sum(1 for p in players if p.age != "未知年龄")
    players_with_team = sum(1 for p in players if p.team != "自由选手")
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
CS2选手数据统计报告
==================
总选手数: {total_players}
有年龄信息的选手: {players_with_age} ({players_with_age/total_players*100:.1f}%)
有队伍信息的选手: {players_with_team} ({players_with_team/total_players*100:.1f}%)
有角色信息的选手: {players_with_role} ({players_with_role/total_players*100:.1f}%)

国籍分布 (Top 10):
"""
    
    # 按数量排序国籍
    sorted_nationalities = sorted(nationality_count.items(), key=lambda x: x[1], reverse=True)
    for nationality, count in sorted_nationalities[:10]:
        report += f"{nationality}: {count} ({count/total_players*100:.1f}%)\n"
    
    report += "\n角色分布:\n"
    for role, count in role_count.items():
        report += f"{role}: {count} ({count/total_players*100:.1f}%)\n"
    
    # 保存报告
    with open("output/statistics_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info("统计报告已生成: output/statistics_report.txt")
    print(report)

if __name__ == "__main__":
    main() 