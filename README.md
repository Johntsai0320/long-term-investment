# 25年加速版 Master IPS 投資執行憲法（V1 檢核 × V2 修正定案版）

本儲存庫包含 **25 年加速版 Master IPS 投資執行憲法** 之 **三體系馬可夫（3-Regime Markov）＋ Student-t 肥尾（`df=7`）10,000 條路徑蒙地卡羅模擬程式、完整數據集與可執行定案文件**。

---

## 核心修訂方向（V2 修正定案版）

1. **全額剛性生活費底線（Layer 1）**：每年實質 **77.0 萬元**（Year-0 購買力 **6.42 萬元／月**），**100% 連動台灣 CPI 足額發放**，永久取消原版（V1）減薪、凍漲與通膨折扣（購買力縮水 ≥20% 機率自 `69.3%` 降至 `0.0%`；基準 30 年破產率自 V1 剛性實測 `40.97%` 壓降至 **`1.17%`**）。
2. **愛爾蘭 UCITS 雙券商架構**：海外 ETF 全面升級為倫敦 LSE 美元掛牌愛爾蘭 UCITS（`VALU`、`FWRA`、`CBU7`、`TIP5`、`IB01`），根除 **40% 美國遺產稅曝險**並將美股股利預扣減半至 **15%**、美債／TIPS 預扣降為 **0%**，全組加權內扣僅 **~0.11%**。台股留存國泰定期定額與基金平台，並切分「`≤ 250 萬實質`原型 `0050 ETF` 質押底倉」＋「`0050 連結基金 A 不配息`」。
3. **購買力連動階梯 × 退休就緒閘門**：累積期採台灣 CPI 連動 **3.0 → 7.0 → 10.0 萬元／月**（25 年累計實質 2,295 萬／預估名目 ~3,066 萬），退休啟動檢核生活實質資本 ≥ **2,750 萬**（含 150 萬獨立醫療池 ≥ 2,900 萬，最長遞延 +4 年）；退休非現金採 **45% 股 / 55% 防禦債**（存續期 4.11 年）＋ **3.0 年雙幣現金池**，模組 R 四大紅線違規率全數 **0.00%**。

---

## 儲存庫檔案索引

| 檔案 | 說明 |
| :--- | :--- |
| [Master_IPS_V2_修正定案版.md](Master_IPS_V2_修正定案版.md) | 修正定案版 V2 完整投資執行憲法（Markdown 全文） |
| [25年加速版_Master_IPS_投資執行憲法_修正定案版.docx](25年加速版_Master_IPS_投資執行憲法_修正定案版.docx) | 直接可執行之正式 Word 排版憲法文件 |
| [ips_monte_carlo_v2.py](ips_monte_carlo_v2.py) | V2 七大情境 × 10,000 條路徑蒙地卡羅主模擬引擎 |
| [simulation_v2_results.json](simulation_v2_results.json) | V2 七大壓力情境完整 55 年模擬分位數與統計結果 |
| [ips_monte_carlo.py](ips_monte_carlo.py) | V1 原版結構基準及剛性對照蒙地卡羅引擎 |
| [simulation_results.json](simulation_results.json) | V1 全情境基準及剛性破產壓力測試原始結果 |
| [generate_v2_docx.py](generate_v2_docx.py) | 依據 JSON 實證數據自動編排並生成 V2 `.docx` 之腳本 |

---

## 重現模擬與重新產出文件

需安裝 Python 套件 `numpy`、`python-docx`：

```bash
# 執行 V1 基準模擬
python3 ips_monte_carlo.py

# 執行 V2 修正定案版 7 大情境模擬（seed=20261116, N=10,000）
python3 ips_monte_carlo_v2.py

# 重新生成 V2 Word (.docx) 憲法文件
python3 generate_v2_docx.py
```
