import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from config import VALIDATION_RULES, DATA_CLEANING

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """数据验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_data: Dict[str, Any]

class DataValidator:
    """数据验证和清洗工具类"""
    
    def __init__(self):
        self.validation_rules = VALIDATION_RULES
        self.cleaning_rules = DATA_CLEANING
    
    def validate_player_info(self, player_data: Dict[str, Any]) -> ValidationResult:
        """验证选手信息"""
        errors = []
        warnings = []
        cleaned_data = player_data.copy()
        
        # 验证姓名
        name = player_data.get('name', '')
        if not name or len(name.strip()) < self.validation_rules['min_name_length']:
            errors.append(f"姓名无效: {name}")
        elif len(name) > self.validation_rules['max_name_length']:
            warnings.append(f"姓名过长: {name}")
            cleaned_data['name'] = name[:self.validation_rules['max_name_length']]
        
        # 验证年龄
        age = player_data.get('age', '')
        if age != "未知年龄":
            try:
                age_int = int(age)
                if age_int < self.validation_rules['min_age'] or age_int > self.validation_rules['max_age']:
                    warnings.append(f"年龄异常: {age}")
                    cleaned_data['age'] = "未知年龄"
            except (ValueError, TypeError):
                errors.append(f"年龄格式无效: {age}")
                cleaned_data['age'] = "未知年龄"
        
        # 验证角色
        role = player_data.get('role', '')
        if role and role.lower() not in self.validation_rules['valid_roles']:
            warnings.append(f"角色无效: {role}")
            cleaned_data['role'] = "未知位置"
        
        # 验证国籍
        nationality = player_data.get('nationality', '')
        if nationality and nationality.lower() not in self.validation_rules['valid_nationalities']:
            warnings.append(f"国籍可能无效: {nationality}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data
        )
    
    def clean_text(self, text: str) -> str:
        """清理文本数据"""
        if not text:
            return ""
        
        # 移除HTML标签
        if self.cleaning_rules['remove_html_tags']:
            text = re.sub(r'<[^>]+>', '', text)
        
        # 移除Wiki链接标记
        if self.cleaning_rules['remove_wiki_links']:
            text = re.sub(r'\[\[|\]\]', '', text)
        
        # 标准化空白字符
        if self.cleaning_rules['normalize_whitespace']:
            text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除引号
        if self.cleaning_rules['strip_quotes']:
            text = text.strip('"\'')
        
        return text
    
    def normalize_role(self, role: str) -> str:
        """标准化角色名称"""
        if not role:
            return "未知位置"
        
        role_lower = role.lower()
        
        # 应用角色映射
        if self.cleaning_rules['normalize_roles']:
            for old_role, new_role in self.cleaning_rules['role_mapping'].items():
                if old_role.lower() in role_lower:
                    return new_role
        
        # 如果没有匹配的映射，返回原始角色
        return role
    
    def extract_age_from_birth_date(self, birth_date: str) -> str:
        """从出生日期提取年龄"""
        if not birth_date:
            return "未知年龄"
        
        try:
            # 匹配年份模式
            year_patterns = [
                r'(\d{4})',  # 标准4位年份
                r'born\s+(\d{4})',  # born 1995
                r'(\d{4})\s*年',  # 1995年
                r'(\d{4})-\d{2}-\d{2}',  # 1995-01-01
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            ]
            
            for pattern in year_patterns:
                match = re.search(pattern, birth_date, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 1:
                        birth_year = int(match.group(1))
                    else:
                        birth_year = int(match.group(3))  # 对于MM/DD/YYYY格式
                    
                    from datetime import datetime
                    current_year = datetime.now().year
                    age = current_year - birth_year
                    
                    if self.validation_rules['min_age'] <= age <= self.validation_rules['max_age']:
                        return str(age)
            
            return "未知年龄"
        except (ValueError, TypeError) as e:
            logger.warning(f"年龄解析失败: {birth_date} - {e}")
            return "未知年龄"
    
    def validate_and_clean_player_data(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证并清洗选手数据"""
        # 首先清理文本数据
        cleaned_data = {}
        for key, value in player_data.items():
            if isinstance(value, str):
                cleaned_data[key] = self.clean_text(value)
            else:
                cleaned_data[key] = value
        
        # 标准化角色
        if 'role' in cleaned_data:
            cleaned_data['role'] = self.normalize_role(cleaned_data['role'])
        
        # 验证数据
        validation_result = self.validate_player_info(cleaned_data)
        
        # 记录警告
        for warning in validation_result.warnings:
            logger.warning(warning)
        
        # 记录错误
        for error in validation_result.errors:
            logger.error(error)
        
        return validation_result.cleaned_data
    
    def batch_validate(self, players_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量验证选手数据"""
        validated_players = []
        invalid_count = 0
        
        for player_data in players_data:
            validated_data = self.validate_and_clean_player_data(player_data)
            
            # 检查是否有效
            validation_result = self.validate_player_info(validated_data)
            if validation_result.is_valid:
                validated_players.append(validated_data)
            else:
                invalid_count += 1
                logger.warning(f"跳过无效选手数据: {player_data.get('name', 'Unknown')}")
        
        logger.info(f"批量验证完成: {len(validated_players)} 个有效数据, {invalid_count} 个无效数据")
        return validated_players
    
    def generate_validation_report(self, players_data: List[Dict[str, Any]]) -> str:
        """生成数据验证报告"""
        total_count = len(players_data)
        valid_count = 0
        invalid_count = 0
        warning_count = 0
        
        # 统计信息
        age_stats = {'valid': 0, 'invalid': 0, 'unknown': 0}
        role_stats = {'valid': 0, 'invalid': 0, 'unknown': 0}
        nationality_stats = {}
        
        for player_data in players_data:
            validation_result = self.validate_player_info(player_data)
            
            if validation_result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1
            
            warning_count += len(validation_result.warnings)
            
            # 统计年龄
            age = player_data.get('age', '')
            if age == "未知年龄":
                age_stats['unknown'] += 1
            elif age and age.isdigit():
                age_int = int(age)
                if self.validation_rules['min_age'] <= age_int <= self.validation_rules['max_age']:
                    age_stats['valid'] += 1
                else:
                    age_stats['invalid'] += 1
            
            # 统计角色
            role = player_data.get('role', '')
            if role == "未知位置":
                role_stats['unknown'] += 1
            elif role and role.lower() in self.validation_rules['valid_roles']:
                role_stats['valid'] += 1
            else:
                role_stats['invalid'] += 1
            
            # 统计国籍
            nationality = player_data.get('nationality', '')
            if nationality:
                nationality_stats[nationality] = nationality_stats.get(nationality, 0) + 1
        
        # 生成报告
        report = f"""
数据验证报告
============
总数据量: {total_count}
有效数据: {valid_count} ({valid_count/total_count*100:.1f}%)
无效数据: {invalid_count} ({invalid_count/total_count*100:.1f}%)
警告数量: {warning_count}

年龄统计:
- 有效年龄: {age_stats['valid']} ({age_stats['valid']/total_count*100:.1f}%)
- 无效年龄: {age_stats['invalid']} ({age_stats['invalid']/total_count*100:.1f}%)
- 未知年龄: {age_stats['unknown']} ({age_stats['unknown']/total_count*100:.1f}%)

角色统计:
- 有效角色: {role_stats['valid']} ({role_stats['valid']/total_count*100:.1f}%)
- 无效角色: {role_stats['invalid']} ({role_stats['invalid']/total_count*100:.1f}%)
- 未知角色: {role_stats['unknown']} ({role_stats['unknown']/total_count*100:.1f}%)

国籍分布 (Top 10):
"""
        
        # 按数量排序国籍
        sorted_nationalities = sorted(nationality_stats.items(), key=lambda x: x[1], reverse=True)
        for nationality, count in sorted_nationalities[:10]:
            report += f"- {nationality}: {count} ({count/total_count*100:.1f}%)\n"
        
        return report 