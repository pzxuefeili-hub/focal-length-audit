# Smoke Test 执行清单（4060 主机 · Windows · 2026-09-29 版）

> 目标：今晚睡前启动，跑通 Phase 1 退出门——三个模型各生成 1 张 + GeoCalib 各标定 1 次。
> 全程文件放 **D 盘**（C 盘只剩 37GB，装不下 45GB 权重）。
> 每完成一步在方框打勾；卡在哪一步，把报错原样发给 Kimi Work。

## 第 1 步：安装 Python 3.12（约 5 分钟）

- [ ] 打开 https://www.python.org/downloads/ → 点黄色 **Download Python 3.12.x** 按钮
- [ ] 运行安装包，**先勾选** "Add python.exe to PATH"，再点 **"Customize installation"**
- [ ] 下一步到 "Advanced Options"，**安装路径改成 `D:\Python312`**，点 Install
- [ ] 装完**关闭并重新打开** PowerShell，验证：
      ```powershell
      D:\Python312\python.exe --version
      ```
      显示 `Python 3.12.x` 即成功（注意：一定要带完整路径运行，不要只敲 `python`，因为系统里还有别的 Python 会被优先命中）

## 第 2 步：创建虚拟环境（1 分钟）

```powershell
D:\Python312\python.exe -m venv D:\focal-env
D:\focal-env\Scripts\Activate.ps1
```

- [ ] 激活成功标志：PowerShell 行首出现 `(focal-env)`
- [ ] 如果报错"禁止运行脚本"，先执行：
      ```powershell
      Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
      ```
      再重新激活

## 第 3 步：把下载缓存指向 D 盘（关键，防止 C 盘撑爆）

```powershell
$env:HF_HOME = "D:\hf-cache"
```

- [ ] 执行完即可（每次新开 PowerShell 都要重新执行这一条，或一次性 `setx HF_HOME "D:\hf-cache"` 后重开窗口）

## 第 4 步：让 pip 能找到 git（装 GeoCalib 用）

```powershell
$env:PATH += ";D:\KimiData\daimon-bundle\runtime\git\cmd"
git --version
```

- [ ] 显示 `git version 2.47...` 即成功

## 第 5 步：安装 PyTorch（CUDA 版，约 10 分钟）

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

- [ ] 装完验证（必须在激活的 (focal-env) 里）：
      ```powershell
      python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
      ```
      第二项显示 `True` 即成功；显示 `False` 说明装成 CPU 版了，停下来找我

## 第 6 步：安装项目依赖（约 5 分钟）

```powershell
cd "D:\KimiData\kimi\tasks\2026-09-29\17-25-10-76e8df1f\focal-length-audit"
pip install -r requirements.txt
```

- [ ] 安装过程中如果某个包卡住超过 5 分钟，按 `Ctrl + C` 中断后重跑一次

## 第 7 步：安装 GeoCalib（2 分钟）

```powershell
git clone https://github.com/cvg/GeoCalib D:\GeoCalib
pip install -e D:\GeoCalib
python -c "import geocalib; print('geocalib OK')"
```

- [ ] 显示 `geocalib OK` 即成功

## 第 8 步：启动冒烟测试（睡前执行，约 45GB 下载 + 生成）

```powershell
python scripts\smoke_test.py
```

- [ ] 首次运行会自动下载三个模型的权重（合计约 45GB，走 D 盘缓存）——**睡前启动，挂着下载**
- [ ] 每个模型生成成功会打印 `-> smoke_<模型>_seed0.png (xx.xs)`
- [ ] 标定成功会打印 `vFoV median = xx.xx°`（参考：50mm 全画幅 ≈ 27°）
- [ ] 全部通过后结尾显示 `SMOKE TEST PASSED`

## 第 9 步：记录结果（明早，10 分钟）

- [ ] 把三个模型的"推理秒数 + vFoV 中位数 + 散布"填进 `docs/protocol.md` 第 14 节的记录表
- [ ] 截图保存终端输出
- [ ] 提交并推送：
      ```powershell
      git add docs/protocol.md
      git commit -m "Smoke test results"
      git push
      ```

## 常见问题速查

| 现象 | 处理 |
|---|---|
| `python` 命令命中了别的 Python | 一律用 `D:\Python312\python.exe` 完整路径，或确认已激活 `(focal-env)` |
| CUDA out of memory | 脚本已启用 CPU offload；若仍失败，记下是哪个模型，发我 |
| 下载中断 | 直接重跑同一命令，HuggingFace 会断点续传 |
| `torch.cuda.is_available()` 为 False | PyTorch 装成了 CPU 版：重装第 5 步，确认命令里有 `--index-url` |
| GeoCalib 标定值离谱（如 3° 或 179°） | 可能是 vFoV 读取兼容问题，把终端输出发我 |
| M4 Pro 那台 Mac | 同款脚本直接跑（自动走 MPS），第 5 步去掉 `--index-url` 参数装普通版 torch 即可 |

## 提醒

- SD3.5 Medium 是 gated 模型，首次下载前需要到 https://huggingface.co/stabilityai/stable-diffusion-3.5-medium 登录并点 "Accept terms"（用你的 Hugging Face 账号，免费）。如果脚本在 SD3.5 处报 401/403 错误，就是这个原因。
- Hugging Face 账号免费注册：https://huggingface.co/join
