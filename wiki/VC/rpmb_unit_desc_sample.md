# Test Spec: RPMB Unit Descriptor Retrieval & Field Validation

## Verification Criterion (VC)
驗證 UFS 主機端 API 介面 `get_rpmb_unit_descriptor` 能否正確從 UFS 裝置讀取 RPMB (Replay Protected Memory Block) 的硬體配置描述符，並確認關鍵欄位（如 LUN 使能、區域大小、PSA 敏感度、記憶體類型等）的資料完整性與格式正確性。此測試主要針對 `RPMBUnitDescriptor410` 結構體的各個 Byte/Quad 欄位進行讀取與日誌輸出驗證，確保韌體回報的 RPMB 硬體資源分配（Region 0-3, AdvRPMB, RPMBPurge）與邏輯區塊計數符合規格定義。

## Test Case (TC) Checkpoints
1. [RPMB_Desc_Read_and_Parse_Check]：
   - 動作：呼叫 `api.get_rpmb_unit_descriptor()` 取得 RPMB 單元描述符物件，並將其強轉為 `api.RPMBUnitDescriptor410` 類型。隨後透過 `printout_rpmb_unit_desc` 函數逐一讀取並記錄以下欄位數值：
     - `b0_length`: 描述符長度。
     - `b1_descriptor_idn`: 描述符 ID。
     - `b2_unit_index`: RPMB 單元索引。
     - `b3_lu_enable`: LUN 使能狀態。
     - `b4_boot_lun_id`: 開機 LUN ID。
     - `b5_lu_write_protect`: LUN 寫入保護狀態。
     - `b6_lu_queue_depth`: LUN 佇列深度。
     - `b7_psa_sensitive`: PSA (Power State Awareness) 敏感度。
     - `b8_memory_type`: 記憶體類型。
     - `b9_rpmb_region_enable`: 檢查 Bit 1-5 分別對應 region0, region1, region2, region3, AdvRPMB, RPMBPurge 的使能狀態。
     - `b10_logical_block_size`: 邏輯區塊大小。
     - `q11_logical_block_count`: 邏輯區塊總數。
     - `b19-b22`: 分別為 Region 0-3 的大小。
     - `b23_provisioning_type`: 預設配置類型。
     - `q24_phy_mem_resource_count`: 實體記憶體資源計數。
   - 預期結果：API 呼叫成功回傳非空物件；日誌中應完整輸出上述所有欄位的十六進位或十進位數值；`b9_rpmb_region_enable` 的布林檢查邏輯應正確映射出對應的 region 名稱字串（例如若 Bit 1 為 1，則輸出包含 'region0'）；無例外錯誤拋出，代表韌體能正確解析並回報 RPMB 硬體描述符結構。