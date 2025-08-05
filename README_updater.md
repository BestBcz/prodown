# CS2选手信息更新器

这个程序专门用于更新 `players.csv` 文件中已有选手的最新信息。

## 功能特点

- ✅ 只更新 `players.csv` 文件中已存在的选手
- ✅ 从 Liquipedia 获取最新信息
- ✅ 保持与原始CSV格式一致
- ✅ 生成详细的更新报告
- ✅ 支持限制更新数量（用于测试）
- ✅ 智能角色标准化处理
- ✅ 角色信息增强（HLTV + 本地数据库）

## 使用方法

### 1. 更新所有选手
```bash
python players_updater.py
```

### 2. 只更新前N个选手（用于测试）
```bash
python players_updater.py 5  # 只更新前5个选手
python players_updater.py 10 # 只更新前10个选手
```

## 输出文件

- `output/updated_players.csv` - 更新后的选手信息
- `output/update_report.txt` - 更新统计报告
- `players_updater.log` - 详细日志文件

## 输出格式

更新后的CSV文件包含以下字段：
- 姓名
- 队伍
- 国籍
- 年龄
- 游戏内位置

## 角色标准化

程序会自动将以下角色进行标准化处理：

- **Streamer** → Free Agent
- **Broadcast Analyst** → Free Agent  
- **In-game leader** → Rifler
- **Assistant Coach** → Coach
- **Entry Fragger** → Rifler
- **Rifler/AWPer** → Rifler
- **Manager** → Free Agent
- **Analyst** → Free Agent

## 角色信息增强

当从Liquipedia获取的角色信息为"未知位置"时，程序会：

1. **尝试从HLTV获取**：访问HLTV选手页面，分析武器使用和角色描述
2. **使用本地数据库**：如果HLTV访问失败，使用内置的知名选手角色数据库
3. **智能匹配**：根据选手姓名自动匹配对应的角色信息

## 注意事项

1. 程序会自动读取 `players.csv` 文件
2. 每个选手的请求间隔为1秒，避免对服务器造成压力
3. 如果某个选手信息获取失败，会在日志中记录
4. 建议先用小数量测试，确认无误后再更新全部选手
5. 角色信息会自动进行标准化处理
6. HLTV可能有访问限制，程序会自动使用本地数据库作为备选

## 示例输出

```
CS2选手信息更新报告
==================
原始选手数: 211
成功更新数: 200
更新成功率: 94.8%

数据完整性:
- 有年龄信息的选手: 180 (90.0%)
- 有队伍信息的选手: 195 (97.5%)
- 有角色信息的选手: 185 (92.5%)
``` 