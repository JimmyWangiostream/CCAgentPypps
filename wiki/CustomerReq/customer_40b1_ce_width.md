# CustomerReq — Get_Best_Bfea_Scan (0xB1/0x40) 欄位規格裁決

日期:2026-07-05(工程師轉述客戶規格,對話裁決)

## 規則定義

- **Get_Best_Bfea_Scan (VU 0xB1 / func 0x40)**:
  - transfer_length = 0x1000,Data-In,回傳 4096 bytes
  - byte[12~15] 帶 VB(little-endian,呼叫端給值)
  - **byte[16~19] 帶 CE(little-endian,4 bytes,呼叫端給值)** ← 裁決重點:
    CE 欄位寬度為 4 bytes(16~19),非 2 bytes
