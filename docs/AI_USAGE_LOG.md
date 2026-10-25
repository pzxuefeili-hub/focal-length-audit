# AI Assistance Log

Required by the project AI-use policy: record every substantive use of AI
(coding help, debugging, literature search support, language editing).
30 seconds per entry; the summary goes into the report's AI-use statement.
Raw blind-rating records are **never** pasted into AI tools.

| Entry ID | Phase | Tool and version | Purpose | Prompt summary | What you kept | How you verified it | Disclosure needed |
|---|---|---|---|---|---|---|---|
| 1 | Phase 1 | Kimi Work (Kimi Work desktop agent) | Repo bootstrap | Asked to reconstruct the project repo (structure, README, requirements, smoke test, protocol draft) from the prior chat history | Directory skeleton, README, requirements.txt, scripts/smoke_test.py, docs/protocol.md v1 | **Found 6 deviations vs. blueprint in v1** (focal levels, outcome definition, gate criteria, matrix numbers, stats details, compression rule); corrected in v2 | Yes — coding assistance + protocol drafting assistance |
| 2 | Phase 1 | Kimi Work (Kimi Work desktop agent) | Protocol alignment | Supplied instructor blueprint; asked to align protocol.md to it line by line | docs/protocol.md v2 — outcome definitions, RQ decision rules, frozen configs, scene texts, matrix (5,888), instrument procedures, gates | Pending — **investigator must read v2 against the blueprint once more before freezing**; every number in v2 traces to a blueprint line | Yes — protocol drafting assistance |

## Notes

- AI may write code, debug, polish text, and analyze data provided by the investigator.
- AI must never fabricate data or results; every AI-produced number/claim is verified by the investigator.
- Verify every AI-suggested citation, number, and code change yourself before use.

## 2026-10-25 条目：焦段生成对照实验的方差问题与两个候选方案

- **观察**：试运行中发现，提示词仅焦段从句变化时（如 24mm → 105mm），即使场景文本相同，生成图像的背景与构图仍有明显漂移（此前未固定 seed 的样张漂移更剧烈）。固定 seed 可消除"完全无关"的输出差异，但焦段从句改变 prompt 嵌入后，场景仍会部分重构成，影响逐焦段直接对比。
- **分析**：预注册的冻结 seed 阶梯（Phase 4/5 主线）保持有效，测量的是模型原生焦段依从性；漂移残差需要通过设计补充来控制。
- **候选方案（待导师批准后进入 protocol 修正案）**：
  1. **锚定阶梯（anchored ladder）**：24mm 底图 → 逐级作为下一焦段的 img2json/img2img 初始化（固定 strength、固定 seed），测量模型在有视觉锚定时对焦段重渲染的"抵抗度"
  2. **固定底板 + 局部重绘（rung D-prime）**：扩展已批准的 rung D 机制（strength 0.3 img2img），背景板逐像素固定，仅对锥桶区域按焦段从句 inpainting；零背景方差，测量物体层面焦段渲染
- **待定设计问题**：Arm 2 合成图的真值读法——(a) 一致性测试（物体与背景透视是否自洽）或 (b) 以底板焦段为参照；倾向 (a)，待导师裁定
- **配套措施**：所有 arm 的相邻焦段对计算 CLIP/LPIPS 相似度，场景漂移量作为协变量写入 sidecar JSON 并随结果报告
- **合规声明**：以上两 arm 在获得导师书面批准前不生成任何正式数据；已预注册的冻结 seed 阶梯不受影响，按原计划执行
