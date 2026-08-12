import sys
import json
from os.path import join, dirname, abspath
from tqdm import tqdm
sys.path.insert(0, '../')

from web_agent_site.engine.engine import load_products

# 显式指向全量数据文件，不再依赖 utils.py 里写死的 _1000 小样本默认值
FULL_FILE_PATH = join(dirname(abspath(__file__)), '..', 'data', 'items_shuffle.json')
all_products, *_ = load_products(filepath=FULL_FILE_PATH)


docs = []
for p in tqdm(all_products, total=len(all_products)):
    option_texts = []
    options = p.get('options', {})
    for option_name, option_contents in options.items():
        option_contents_text = ', '.join(option_contents)
        option_texts.append(f'{option_name}: {option_contents_text}')
    option_text = ', and '.join(option_texts)

    doc = dict()
    doc['id'] = p['asin']
    doc['contents'] = ' '.join([
        p['Title'],
        p['Description'],
        p['BulletPoints'][0],
        option_text,
    ]).lower()
    doc['product'] = p
    docs.append(doc)


with open('./resources_100/documents.jsonl', 'w+') as f:
    for doc in docs[:100]:
        f.write(json.dumps(doc) + '\n')

with open('./resources/documents.jsonl', 'w+') as f:
    for doc in docs:
        f.write(json.dumps(doc) + '\n')

with open('./resources_1k/documents.jsonl', 'w+') as f:
    for doc in docs[:1000]:
        f.write(json.dumps(doc) + '\n')

with open('./resources_100k/documents.jsonl', 'w+') as f:
    for doc in docs[:100000]:
        f.write(json.dumps(doc) + '\n')
