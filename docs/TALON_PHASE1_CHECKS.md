# Talon：Phase 1 两项补充复核

目的：完成导师 2026-10-30 编辑清单中的（1）同提示词、同种子完整生成两次并比较 SHA-256；（2）记录 GeoCalib、WildCamera、Grounding DINO tiny、CLIP ViT-L/14 的权重哈希。两项都不是正式标定，不触碰 DOI 前的仪器红线。

## 0. 前置条件

先把本轮新增的 `scripts/check_generation_determinism.py` 和 `tools/hash_instrument_weights.py` 传到 Talon 仓库的相同相对路径。以下命令只在 Talon 的 SSH 会话中运行，不要在 Windows PowerShell 中运行。

```bash
cd ~/work/focal-length-audit
source ~/focal-env/bin/activate
```

## 1. 完整生成链确定性

```bash
python scripts/check_generation_determinism.py
```

脚本用 SDXL 的冻结配置（30 steps、guidance 7.0、fp16、CPU seed 0）完整生成两次。成功时最后一行是：

```text
DETERMINISM CHECK PASSED
```

结果位置：

- `results/determinism/determinism_report.json`：两次哈希、GPU、库版本和是否通过。
- `results/determinism/sdxl_seed0_run1.png`、`sdxl_seed0_run2.png`：两张复核图。

如果显示 `FAILED`，不要改写成通过，也不要反复跑到通过为止；保留报告并记录失败。

## 2. 仪器权重哈希

先确保四种仪器至少加载过一次、权重已下载，然后运行：

```bash
python tools/hash_instrument_weights.py
```

成功时最后一行是：

```text
INSTRUMENT HASH COVERAGE PASSED
```

结果位置：

- `instrument_weight_hashes.txt`：可粘贴/追加到仓库权重哈希记录。
- `instrument_weight_hashes.json`：按仪器类别列出覆盖情况；缺任何一类都会返回非零状态，不会误报通过。

若提示 `MISSING`，说明对应权重尚未下载或不在常见缓存目录。找到权重目录后可显式追加搜索根目录：

```bash
python tools/hash_instrument_weights.py /path/to/weights ~/.cache/huggingface/hub ~/.cache/torch ~/work
```

## 3. 完成后

把下面两个文件的内容发回项目记录，再据实追加到 `docs/protocol.md`，不要手写猜测哈希：

```bash
cat results/determinism/determinism_report.json
cat instrument_weight_hashes.json
```
