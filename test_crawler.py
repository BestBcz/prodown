#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CS2选手爬虫测试脚本
测试优化后的爬虫功能和数据验证
"""

import sys
import os
import time
import logging
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from optimized_crawler import CS2PlayerCrawler, PlayerInfo
from data_validator import DataValidator
from config import *

# 配置测试日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_data_validator():
    """测试数据验证器"""
    logger.info("开始测试数据验证器...")
    
    validator = DataValidator()
    
    # 测试数据
    test_players = [
        {
            'name': 's1mple',
            'team': 'Natus Vincere',
            'nationality': 'Ukraine',
            'age': '28',
            'role': 'AWPer'
        },
        {
            'name': 'ZywOo',
            'team': 'Team Vitality',
            'nationality': 'France',
            'age': '25',
            'role': 'AWPer'
        },
        {
            'name': 'Invalid Player',
            'team': '',
            'nationality': 'Invalid Country',
            'age': '100',
            'role': 'Invalid Role'
        },
        {
            'name': 'a',  # 太短的姓名
            'team': 'Test Team',
            'nationality': 'United States',
            'age': '20',
            'role': 'Rifler'
        }
    ]
    
    # 测试单个数据验证
    for i, player in enumerate(test_players):
        logger.info(f"测试数据 {i+1}: {player['name']}")
        validation_result = validator.validate_player_info(player)
        
        if validation_result.is_valid:
            logger.info(f"✓ 数据有效: {player['name']}")
        else:
            logger.warning(f"✗ 数据无效: {player['name']}")
            for error in validation_result.errors:
                logger.warning(f"  错误: {error}")
        
        for warning in validation_result.warnings:
            logger.warning(f"  警告: {warning}")
    
    # 测试批量验证
    logger.info("测试批量验证...")
    validated_players = validator.batch_validate(test_players)
    logger.info(f"批量验证结果: {len(validated_players)} 个有效数据")
    
    # 生成验证报告
    report = validator.generate_validation_report(test_players)
    logger.info("验证报告:")
    print(report)
    
    return True

def test_crawler_basic():
    """测试爬虫基本功能"""
    logger.info("开始测试爬虫基本功能...")
    
    crawler = CS2PlayerCrawler()
    
    # 测试请求功能
    test_url = "https://liquipedia.net/counterstrike/s1mple"
    logger.info(f"测试请求: {test_url}")
    
    response = crawler._make_request(test_url)
    if response:
        logger.info("✓ 请求成功")
    else:
        logger.error("✗ 请求失败")
        return False
    
    # 测试数据解析
    if response:
        player_info = crawler._get_player_info_from_liquipedia(test_url)
        if player_info:
            logger.info(f"✓ 数据解析成功: {player_info.name}")
            logger.info(f"  队伍: {player_info.team}")
            logger.info(f"  国籍: {player_info.nationality}")
            logger.info(f"  年龄: {player_info.age}")
            logger.info(f"  角色: {player_info.role}")
        else:
            logger.error("✗ 数据解析失败")
            return False
    
    return True

def test_famous_players_crawl():
    """测试知名选手爬取"""
    logger.info("开始测试知名选手爬取...")
    
    crawler = CS2PlayerCrawler()
    
    # 只测试前3个选手以节省时间
    test_players = ["s1mple", "ZywOo", "NiKo"]
    
    players = []
    for player_name in test_players:
        logger.info(f"测试爬取: {player_name}")
        player_info = crawler._get_player_info_by_name(player_name)
        
        if player_info:
            players.append(player_info)
            logger.info(f"✓ 成功爬取: {player_info.name}")
        else:
            logger.warning(f"✗ 爬取失败: {player_name}")
    
    logger.info(f"测试结果: 成功爬取 {len(players)} 个选手")
    
    # 测试数据验证
    validator = DataValidator()
    for player in players:
        player_dict = player.to_dict()
        validation_result = validator.validate_player_info(player_dict)
        if validation_result.is_valid:
            logger.info(f"✓ 数据验证通过: {player.name}")
        else:
            logger.warning(f"✗ 数据验证失败: {player.name}")
    
    return len(players) > 0

def test_data_cleaning():
    """测试数据清洗功能"""
    logger.info("开始测试数据清洗功能...")
    
    validator = DataValidator()
    
    # 测试文本清洗
    test_texts = [
        "  s1mple  ",
        "[[Ukraine]]",
        "<b>Natus Vincere</b>",
        "Rifler/AWPer",
        "Entry Fragger"
    ]
    
    for text in test_texts:
        cleaned = validator.clean_text(text)
        logger.info(f"原始: '{text}' -> 清洗后: '{cleaned}'")
    
    # 测试角色标准化
    test_roles = [
        "rifler/awper",
        "entry fragger", 
        "lurker/support",
        "awper",
        "igl",
        "coach"
    ]
    
    for role in test_roles:
        normalized = validator.normalize_role(role)
        logger.info(f"原始角色: '{role}' -> 标准化: '{normalized}'")
    
    # 测试年龄提取
    test_birth_dates = [
        "1997-10-02",
        "Born 1995",
        "1990年",
        "01/01/1992",
        "Invalid date"
    ]
    
    for birth_date in test_birth_dates:
        age = validator.extract_age_from_birth_date(birth_date)
        logger.info(f"出生日期: '{birth_date}' -> 年龄: {age}")
    
    return True

def test_csv_operations():
    """测试CSV操作"""
    logger.info("开始测试CSV操作...")
    
    crawler = CS2PlayerCrawler()
    
    # 创建测试数据
    test_players = [
        PlayerInfo(name="Test Player 1", team="Test Team", nationality="Test Country", age="25", role="Rifler"),
        PlayerInfo(name="Test Player 2", team="Another Team", nationality="Another Country", age="30", role="AWPer"),
    ]
    
    # 测试保存到CSV
    test_filename = "test_players.csv"
    crawler.save_to_csv(test_players, test_filename)
    
    # 检查文件是否创建
    output_path = Path("output") / test_filename
    if output_path.exists():
        logger.info(f"✓ CSV文件创建成功: {output_path}")
        
        # 读取并验证数据
        import csv
        with open(output_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            
            if len(rows) == len(test_players):
                logger.info(f"✓ CSV数据验证成功: {len(rows)} 行数据")
            else:
                logger.error(f"✗ CSV数据验证失败: 期望 {len(test_players)} 行, 实际 {len(rows)} 行")
        
        # 清理测试文件
        output_path.unlink()
        logger.info("✓ 测试文件已清理")
    else:
        logger.error(f"✗ CSV文件创建失败: {output_path}")
        return False
    
    return True

def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行所有测试...")
    
    tests = [
        ("数据验证器", test_data_validator),
        ("爬虫基本功能", test_crawler_basic),
        ("知名选手爬取", test_famous_players_crawl),
        ("数据清洗功能", test_data_cleaning),
        ("CSV操作", test_csv_operations),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"运行测试: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            if result:
                logger.info(f"✓ 测试通过: {test_name} (耗时: {end_time - start_time:.2f}秒)")
                passed += 1
            else:
                logger.error(f"✗ 测试失败: {test_name}")
        except Exception as e:
            logger.error(f"✗ 测试异常: {test_name} - {e}")
    
    # 测试总结
    logger.info(f"\n{'='*50}")
    logger.info("测试总结")
    logger.info(f"{'='*50}")
    logger.info(f"总测试数: {total}")
    logger.info(f"通过测试: {passed}")
    logger.info(f"失败测试: {total - passed}")
    logger.info(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        logger.info("🎉 所有测试通过!")
        return True
    else:
        logger.error("❌ 部分测试失败!")
        return False

def main():
    """主函数"""
    logger.info("CS2选手爬虫测试开始")
    
    # 确保输出目录存在
    Path("output").mkdir(exist_ok=True)
    
    # 运行测试
    success = run_all_tests()
    
    if success:
        logger.info("所有测试完成，爬虫功能正常")
        print("\n✅ 测试完成，爬虫已优化并验证通过!")
        print("📁 输出文件将保存在 'output' 目录")
        print("📋 日志文件: crawler.log, test_crawler.log")
    else:
        logger.error("测试失败，请检查代码")
        print("\n❌ 测试失败，请检查错误日志")
    
    return success

if __name__ == "__main__":
    main() 