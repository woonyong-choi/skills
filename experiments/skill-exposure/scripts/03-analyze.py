"""공개 집계의 정밀도·재현율을 대조하고 README 차트 입력을 만든다."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'control': '대조', 'flat': 'H-flat', 'tree': 'H-tree', 'hybrid': 'H-hybrid'}

# cost: time O(n), heap O(n), stack O(1), io 2
# vars: n = 집계 JSON 크기
# basis: estimate
def main() -> None:
    summary = json.loads((ROOT / 'data/aggregates.json').read_text())
    rows = []
    for name, condition in summary['conditions'].items():
        model, structure = name.split('/')
        counts = condition['counts']
        metrics = condition['metrics']
        for key, denominator in (('precision', counts['tp'] + counts['fp']), ('recall', counts['tp'] + counts['fn'])):
            if abs(metrics[key]['value'] - counts['tp'] / denominator) >= 1e-12:
                raise ValueError(f'{name}: {key} does not match counts')
        if model != 'gpt-5.6-luna':
            continue
        row = {'label': LABELS[structure]}
        for key in ('precision', 'recall'):
            value = metrics[key]
            row[key] = 100 * value['value']
            row[key + '.low'], row[key + '.high'] = [100 * bound for bound in value['ci95_cluster']]
        rows.append(row)
    summary['chart'] = rows
    (ROOT / 'results').mkdir(exist_ok=True)
    (ROOT / 'results/summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    main()
