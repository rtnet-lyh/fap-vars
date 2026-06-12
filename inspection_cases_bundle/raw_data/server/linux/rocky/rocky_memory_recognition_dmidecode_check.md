# 영역
MEMORY

# 세부 점검항목
메모리 상태 확인

# 점검 내용
할당된 메모리의 정상 인식여부확인

# 구분
필수

# 명령어
```bash
dmidecode -t memory
```

# 출력 결과
```text
# dmidecode 3.6
Getting SMBIOS data from sysfs.
SMBIOS 2.8 present.

Handle 0x0000, DMI type 16, 23 bytes
Physical Memory Array
        Location: System Board Or Motherboard
        Use: System Memory
        Error Correction Type: Multi-bit ECC
        Maximum Capacity: 1536 GB
        Error Information Handle: Not Provided
        Number Of Devices: 24

Handle 0x0002, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: 72 bits
        Data Width: 64 bits
        Size: 8 GB
        Form Factor: DIMM
        Set: None
        Locator: DIMM000
        Bank Locator: _Node0_Channel0_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)
        Speed: 2133 MT/s
        Manufacturer: Hynix
        Serial Number: 0x713429E1
        Asset Tag: Unknown
        Part Number: HMA41GR7MFR8N-TF
        Rank: 2
        Configured Memory Speed: 1867 MT/s
        Minimum Voltage: 1.2 V
        Maximum Voltage: 1.2 V
        Configured Voltage: 1.2 V

Handle 0x0003, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM001
        Bank Locator: _Node0_Channel0_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0004, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM002
        Bank Locator: _Node0_Channel0_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0005, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM010
        Bank Locator: _Node0_Channel1_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0006, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM011
        Bank Locator: _Node0_Channel1_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0007, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM012
        Bank Locator: _Node0_Channel1_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0008, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM020
        Bank Locator: _Node0_Channel2_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0009, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM021
        Bank Locator: _Node0_Channel2_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x000A, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM022
        Bank Locator: _Node0_Channel2_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x000B, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM030
        Bank Locator: _Node0_Channel3_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x000C, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM031
        Bank Locator: _Node0_Channel3_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x000D, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM032
        Bank Locator: _Node0_Channel3_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x000E, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM100
        Bank Locator: _Node1_Channel0_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x000F, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM101
        Bank Locator: _Node1_Channel0_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0010, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM102
        Bank Locator: _Node1_Channel0_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0011, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM110
        Bank Locator: _Node1_Channel1_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0012, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM111
        Bank Locator: _Node1_Channel1_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0013, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM112
        Bank Locator: _Node1_Channel1_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0014, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: 72 bits
        Data Width: 64 bits
        Size: 8 GB
        Form Factor: DIMM
        Set: None
        Locator: DIMM120
        Bank Locator: _Node1_Channel2_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)
        Speed: 2133 MT/s
        Manufacturer: Hynix
        Serial Number: 0x713429EB
        Asset Tag: NO DIMM
        Part Number: HMA41GR7MFR8N-TF
        Rank: 2
        Configured Memory Speed: 1867 MT/s
        Minimum Voltage: 1.2 V
        Maximum Voltage: 1.2 V
        Configured Voltage: 1.2 V

Handle 0x0015, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM121
        Bank Locator: _Node1_Channel2_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0016, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM122
        Bank Locator: _Node1_Channel2_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0017, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM130
        Bank Locator: _Node1_Channel3_Dimm0
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0018, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM131
        Bank Locator: _Node1_Channel3_Dimm1
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)

Handle 0x0019, DMI type 17, 40 bytes
Memory Device
        Array Handle: 0x0000
        Error Information Handle: Not Provided
        Total Width: Unknown
        Data Width: Unknown
        Size: No Module Installed
        Form Factor: DIMM
        Set: None
        Locator: DIMM132
        Bank Locator: _Node1_Channel3_Dimm2
        Type: DRAM
        Type Detail: Synchronous Registered (Buffered)
```

# 설명
- application credential에서 become 정보를 읽어 sudo로 `dmidecode -t memory`를 root 권한으로 실행한다.
- SSH 연결 실패나 명령 실행 실패면 즉시 실패로 반환한다.
- 출력에서 `Memory Device` 블록을 찾아 슬롯별 `Size`, `Locator`, 제조사, 속도 정보를 파싱한다.
- `Size: No Module Installed`는 제외하고, 실제 장착된 DIMM만 골라 개수와 총 메모리 용량을 계산한다.
- 장착 메모리가 1개 이상이고 총 용량이 0보다 크면 정상, 아니면 메모리 미인식으로 실패한다.

# 임계치
없음

# 판단기준
- **양호**: 실제 장착된 DIMM이 1개 이상 확인되고, 장착 메모리 총 용량이 0보다 큰 상태
- **실패**: 장착된 DIMM을 확인할 수 없거나 총 메모리 용량이 0으로 계산되어 메모리 인식 이상이 의심되는 상태
- **확인 필요**: SSH 연결, sudo 권한, `dmidecode` 실행 실패 또는 출력 파싱 실패로 메모리 장착 정보를 확인할 수 없는 상태
