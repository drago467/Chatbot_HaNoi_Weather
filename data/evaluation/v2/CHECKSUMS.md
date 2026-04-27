# Dataset v2 Checksums

> SHA256 hashes cho reproducibility eval. Tất cả file CSV được bổ sung qua PR-B.1..PR-B.8.

## Files

| Path | SHA256 | Bytes | Rows |
|---|---|---|---|
| `data/evaluation/v2/hanoi_weather_eval_v2_500.csv` | `d35772595a67c5c37180c369bdc00a9aa72c3714cd2286f1ab02725b190dd529` | 232,395 | 500 |
| `data/evaluation/hanoi_weather_chatbot_eval_questions.csv` | `391bb53d474aa258f975ba852cc5738e9e9ce069dea47c5b06065fff46a8e673` | 43,775 | 199 |
| `data/evaluation/v2/dataset_v2_batch01.csv` | `53e3f9401929d3748c44c5086aeaa8e28e890fe75e78adbc72cb10f2f7b63e6d` | 27,297 | 48 |
| `data/evaluation/v2/dataset_v2_batch02.csv` | `cda82a9047a9f59b84740bb9424c90bcb351e4076f9f07e887b8711cebe2e902` | 26,896 | 52 |
| `data/evaluation/v2/dataset_v2_batch03.csv` | `854b671f0f93abb389b838b5346ff336cbc96310ee6601d5723200d17f772964` | 26,021 | 50 |
| `data/evaluation/v2/dataset_v2_batch04.csv` | `dc5bc3cdf7f751a7a7c98806c5bc1af573b06cdaaec4d6f9bd25f443ee3e962e` | 25,015 | 50 |
| `data/evaluation/v2/dataset_v2_batch05.csv` | `8ee2648b9eb65dbedbe5274125c43da9e93f8c6cc49979fc60242f8e1040e403` | 25,540 | 50 |
| `data/evaluation/v2/dataset_v2_batch06.csv` | `5bfc33c6717ab971a60e0692b09aa05cacba20b736209491f10579b9e0673cb9` | 26,290 | 51 |

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
sha256sum data/evaluation/v2/hanoi_weather_eval_v2_500.csv
```

Hash phải khớp dòng đầu trong bảng Files.

## Test

```bash
pytest tests/dataset/ -v
```

15/15 PASS sau commit b4a0084 (PR-B.7 batch06) + PR-B.8 merge.
