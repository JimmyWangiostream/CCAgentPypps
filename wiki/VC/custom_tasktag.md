# Test Spec: UFS Host Controller Task Tag Allocation & Queueing Logic Verification

## Verification Criterion (VC)
驗證 UFS 主機端控制器（Host Controller）在發送 Write10 命令序列時，對 Task Tag（任務標籤）分配機制的行為：Case 01 確認當未手動指定 Task Tag 時，控制器是否自動遞增（Auto-increment）生成唯一的 8-bit Task Tag；Case 02 確認當手動指定 Task Tag 時，控制器是否嚴格使用指定的 8-bit 值（0xAB, 0xCD, 0xFE）並覆蓋自動遞增邏輯；Case 03 確認整個命令序列（共 7 個 Write10）在發送後，Host 端能否正確追蹤每個命令對應的 Task Tag 狀態，確保無衝突且符合 UFS 協議規範。

## Test Case (TC) Checkpoints
1. [Auto_Increment_TaskTag_Check]：
   - 動作：初始化一個 Write10 命令物件，設定 LUN=0, LBA=0, Length=1, FUA=1。在 `b3_tasktag` 欄位保持預設值（通常為 0 或未定義）的情況下，連續四次呼叫 `ExecuteCMD.enqueue(w)` 將該命令物件加入發送佇列，最後呼叫 `ExecuteCMD.send()` 發送所有佇列中的命令。
   - 預期結果：Host 控制器應自動為這四個命令分配遞增的 Task Tag（例如從某個初始值開始，如 0x00, 0x01, 0x02, 0x03 或基於當前活躍任務計數器）。這驗證了 UFS 協議中 Host 端自動管理 Task Tag 的基本功能，確保每個命令在傳輸層具有唯一標識。

2. [Manual_TaskTag_Assignment_Check]：
   - 動作：在自動遞增測試後，重置或繼續使用同一個 Write10 命令物件。分別執行以下操作：
     a. 將 `w.upiu.b3_tasktag` 設為 `0xAB`，並 `enqueue`。
     b. 將 `w.upiu.b3_tasktag` 設為 `0xCD`，並 `enqueue`。
     c. 將 `w.upiu.b3_tasktag` 設為 `0xFE`，並 `enqueue`。
     最後呼叫 `ExecuteCMD.send()` 發送這三個手動指定 Task Tag 的命令。
   - 預期結果：Host 控制器必須嚴格使用指定的 8-bit 值（0xAB, 0xCD, 0xFE）作為這三個命令的 Task Tag，不得進行自動遞增或修改。這驗證了 Host 端手動覆蓋 Task Tag 的機制，確保在需要特定標籤匹配或除錯時，控制器能精確執行。

3. [Sequence_Integrity_and_No_Collision_Check]：
   - 動作：分析整個 `step1` 流程中發送的總命令序列（4 個自動遞增 + 3 個手動指定，共 7 個 Write10 命令）。檢查 Host 端發出的 UPIU 請求單元（UPIU Request Unit）中，每個命令的 `b3_tasktag` 欄位數值。
   - 預期結果：
     - 前四個命令的 Task Tag 應為連續遞增的整數序列（具體起始值取決於 Host 驅動實現，但必須互不相同且符合遞增邏輯）。
     - 後三個命令的 Task Tag 必須精確等於 0xAB, 0xCD, 0xFE。
     - 整個序列中不得出現 Task Tag 衝突（即沒有兩個命令擁有相同的 Task Tag，除非協議允許且驅動明確處理，但在本測試情境下應視為唯一標識）。
     - 這驗證了 Host 驅動在混合使用自動與手動 Task Tag 分配時的邏輯正確性，確保 UFS 傳輸層能正確關聯命令與響應。