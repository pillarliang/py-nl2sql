import json
from collections import defaultdict

# 读取 JSON 文件内容
with open('./mini_dev_mysql.json', 'r') as file:
    data = json.load(file)

# 根据 difficulty 字段将数据分类
difficulty_dict = defaultdict(list)

for item in data:
    difficulty = item.get('difficulty', 'unknown')
    difficulty_dict[difficulty].append(item)

# 将分类后的数据分别写入以 difficulty 值命名的文件中
for difficulty, items in difficulty_dict.items():
    filename = f'{difficulty}.json'
    with open(filename, 'w') as file:
        json.dump(items, file, indent=4)
