# Dataset Checksums

> SHA256 hashes cho reproducibility eval. Source batches `dataset_v2_batch0[1-6].csv` đã archive vào `_archived/eval_v2_drop/` sau khi merge xong file 500 cuối.

## Files

| Path | SHA256 | Bytes | Rows |
|---|---|---|---|
| `data/evaluation/eval_dataset_500.csv` | `d35772595a67c5c37180c369bdc00a9aa72c3714cd2286f1ab02725b190dd529` | 232,395 | 500 |
| `data/evaluation/hanoi_weather_chatbot_eval_questions.csv` | `391bb53d474aa258f975ba852cc5738e9e9ce069dea47c5b06065fff46a8e673` | 43,775 | 199 |

## Coverage matrix

| Metric | Value |
|---|---|
| Total in matrix | 485 / 485 (100%) |
| Cells `ok` (≥ target) | 130 / 130 non-smalltalk |
| Cells `empty` (deferred) | 5 (smalltalk × district/ward, không cần location) |
| Câu legacy non-POI | 184 |
| Câu legacy POI (`expected_clarification=True`) | 15 |
| Câu mới (`source=v2_new`) | 301 |
| **Grand total** | **500** |

## Compose breakdown

- 6 batches × ~50 câu = 301 câu mới
- Edge cases (abstain / clarification / compositional / anaphoric): ~25 câu
- Paraphrases (telex, văn nói, ward swap, multi-aspect): ~28 câu
- Direct fills: ~248 câu

## Verify

```bash
sha256sum data/evaluation/eval_dataset_500.csv
```

Hash phải khớp dòng đầu trong bảng Files.

## Test

```bash
pytest tests/dataset/ -v
```

15/15 PASS sau commit b4a0084 (PR-B.7 batch06) + PR-B.8 merge.
