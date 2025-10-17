## 智慧資源回收系統（YOLO 偵測與自動分類）

本專案結合物件偵測（Ultralytics YOLO）與樹莓派相關硬體，實現自動化垃圾分類與資料蒐集。README 的內容僅根據專案中可直接讀取的程式與設定檔產生，避免任何臆測。

目錄

- 專案摘要
- 主要程式與設定
- 系統功能（驗證自程式）
- 如何執行（範例）
- 輸出與儲存
- 注意事項
- 參考來源
- 改進建議

主要程式與設定（可驗證）

- 主程式：`mainv20.py`（負責影像擷取、YOLO 偵測、分類決策、硬體驅動、資料庫記錄、通知與上傳）。
- 訓練設定檔（範例）：`train8/args.yaml`（例如 model: `yolo11l.pt`、epochs: 1000、batch: 16、imgsz: 640、name: `train8`、save_dir: `runs/detect/train8`）與 `train7/args.yaml`（model: `yolo11s.pt`）。
- 推論模型（程式內被載入的檔案）：範例模型檔名 `bestv6-s歐剉.pt`（在程式中以 YOLO API 載入）。

系統功能（皆可在程式碼中找到實作）

- 即時攝影機擷取影像並進行物件偵測（Ultralytics YOLO）。
- 四類分類：紙容器、塑膠類、金屬類、一般垃圾；程式中含有相對應的類別映射與顯示文字。
- 使用置信度門檻（程式變數 hold = 0.6）決定是否採用偵測結果；在不確定時會提示使用者透過按鈕手動分類。
- 儲存可用於訓練的影像與標註（YOLO 格式），並具自動上傳至 Google Drive 的流程（上傳條件與上傳程式已在程式中定義）。
- 硬體控制：包含 LED、Servo、步進馬達、距離感測器等（使用 gpiozero 等套件）。
- 資料庫紀錄：使用 SQLite（`garbage_data.db`）記錄分類次數與事件紀錄，並能產生整合圖表（`generate_charts()`）。
- 通知機制：LINE Notify（程式中有 token 變數）與 Google Drive 上傳（利用 service account）。

如何執行（範例，針對樹莓派 / Linux 環境）

1) 建議先建立 Python 虛擬環境並安裝依賴（可參考附加的 `requirements.txt`）。

2) 在具備相機與 GPIO 的設備上執行主程式：

```bash
python3 mainv20.py
```

程式會進入監測迴圈，偵測到物品時會觸發分類與資料處理流程。

輸出與儲存（以程式內設定為準，但路徑已省略以保護環境特定資訊）

- 訓練用 images 與 labels（程式會在本地建立並在達到條件時上傳）。
- 臨時偵測影像（程式會保存帶標註的偵測影像以供檢查）。
- 音檔與提示音（程式會呼叫多個音檔來提示使用者或狀態）。
- 資料庫檔案（SQLite），以及可匯出的整合圖表 PNG 檔。

注意事項（已驗證與建議）

- 程式中包含明文憑證或本地檔案路徑（例如 service account 檔案路徑與 LINE token）。強烈建議在公開前改為環境變數或 `.env` 管理，並避免直接上傳憑證。
- 程式多處使用 Linux/樹莓派 路徑與 gpiozero，若在 Windows 測試需調整路徑與硬體相關代碼。
- 本 README 僅列出可在程式與設定檔中直接驗證的資訊；訓練資料集內容、模型內部細節、未顯示的二進位檔案細節不在此推論範圍。

參考來源（專案內可讀檔案）

- `mainv20.py`（主要功能與設定）
- `train8/args.yaml`、`train7/args.yaml`（訓練設定）
- `train8/results.csv`（訓練結果摘要）
- 範例模型檔 `bestv6-s歐剉.pt`（程式中被載入以進行推論）

改進建議（上傳 GitHub 前可做的事）

- 移除或替換程式內明文憑證，改以環境變數或 `config.example` 範本。
- 提供正式的 `requirements.txt`（我會為你生成一份基於程式 import 的建議清單）。
- 將平台相關路徑抽成設定檔，並在 README 中提供具體部署步驟。

----
README 內容已經更新為不顯示絕對路徑，並修正了 Markdown 格式。如果你同意，我接下來會新增 `requirements.txt` 檔案到專案根目錄（我會列出依賴套件與建議版本），然後把 todo list 標記為完成。 
