# Test Spec: UFS Unmap Logical Block Release Verification

## Verification Criterion (VC)
驗證 UFS 主機端 Unmap 指令對邏輯區塊地址 (LBA) 空間釋放後的讀取行為與資料完整性：Case 01 確認被 Unmap 的 LBA 0 在讀取時返回全零資料（代表邏輯區塊已釋放且無有效資料）；Case 02 確認未被 Unmap 的 LBA 1 仍保留原始寫入的 data1 資料；Case 03 確認位於 Unmap 範圍之外的 LBA 3 保留原始寫入的 data2 資料。此測試旨在驗證控制器在處理 Unmap 請求後，正確地將指定 LBA 標記為無效並返回預設零值，同時不影響其他有效 LBA 的資料一致性。

## Test Case (TC) Checkpoints
1. [Unmap_LBA0_ReadZero_Check]：
   - 動作：首先透過 Write10 指令向 LUN 0 寫入 3 個 4KB 區塊（LBA 0-2），資料內容為 data1（首尾字節分別為 0x66, 0x77，其餘為 0x5B）；接著寫入 1 個 4KB 區塊（LBA 3），資料內容為 data2（首尾字節分別為 0x88, 0x99，其餘為 0xAB）。隨後發送 Unmap 指令，指定釋放 LUN 0 的 LBA 0，長度為 1（即釋放 LBA 0）。最後發送 Read10 指令讀取 LBA 0、LBA 1 與 LBA 3 的資料，並分別比對讀回資料。
   - 預期結果：讀取 LBA 0 的 4KB 資料必須完全等於 bytearray([0x00] * 4096)，代表 Unmap 操作成功將該邏輯區塊標記為未分配，讀取時返回預設零值；讀取 LBA 1 的資料必須等於 data1，證明 Unmap 未波及相鄰的有效區塊；讀取 LBA 3 的資料必須等於 data2，證明非連續區塊的資料完整性未受影響。

2. [Data_Integrity_After_Unmap_Check]：
   - 動作：基於上述寫入與 Unmap 流程，針對未被 Unmap 指令影響的 LBA 1 與 LBA 3 進行資料比對。LBA 1 位於被 Unmap 的 LBA 0 之後，LBA 3 位於被 Unmap 範圍之外。
   - 預期結果：LBA 1 的讀回資料必須精確匹配初始寫入的 data1（bytearray([0x5B] * 4096) 且 data1[0]=0x66, data1[-1]=0x77）；LBA 3 的讀回資料必須精確匹配初始寫入的 data2（bytearray([0xAB] * 4096) 且 data2[0]=0x88, data2[-1]=0x99）。此結果驗證了 Unmap 指令僅針對指定 LBA 範圍生效，未造成資料損壞或錯誤的資料遷移。