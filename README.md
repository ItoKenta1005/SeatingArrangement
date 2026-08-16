# SeatingArrangement

ブロック分け最適化を `python + pulp (CBC)` で解くプロジェクトです。

## ディレクトリ構成

```text
.
├─ docs/
│  └─ desc.txt
├─ input/
│  └─ input.csv
├─ output/
│  ├─ output.csv
│  ├─ block_tag_counts.csv
│  ├─ soft_constraint_scores.csv
│  └─ tag_counts.csv
├─ src/
│  ├─ solve.py
│  └─ tag_count_preprocess.py
├─ requirements.txt
└─ README.md
```

## 起動手順

1. 依存関係を入れる

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. タグ人数の前処理CSVを出力する

```powershell
.\venv\Scripts\python.exe src\tag_count_preprocess.py
```

3. 最適化を実行する

```powershell
.\venv\Scripts\python.exe src\solve.py
```

## 出力

- `output/output.csv`
- `output/block_tag_counts.csv`
- `output/soft_constraint_scores.csv`
- `output/tag_counts.csv`

### 各CSVの内容

- `output/output.csv`: 各ユーザがどのブロックに割り当てられたか
- `output/block_tag_counts.csv`: 各ブロックに各タグの参加者が何人いるか
- `output/soft_constraint_scores.csv`: 最適化された総スコアと、ソフト制約ごとのスコア内訳
- `output/tag_counts.csv`: `input.csv` 全体のタグ別人数集計
