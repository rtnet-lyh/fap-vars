# 영역
FILESYSTEM

# 세부 점검 항목
NTFS inode 유사 사용률

# 점검 내용
fsutil ntfsinfo 결과를 바탕으로 MFT 사용량을 계산해 NTFS의 inode 유사 사용률을 추정합니다.

# 구분
권고

# 명령어
```powershell
Get-CimInstance Win32_Volume | Where-Object { $_.DriveType -eq 3 -and $_.DriveLetter -and $_.FileSystem -eq 'NTFS' } | ForEach-Object { $t=(fsutil fsinfo ntfsinfo $_.DriveLetter 2>$null | Out-String); $m=[regex]::Match($t,'Mft Valid Data Length\\s*:\\s*0x([0-9A-Fa-f]+)').Groups[1].Value; $fr=[regex]::Match($t,'Bytes Per FileRecord Segment\\s*:\\s*([0-9]+)').Groups[1].Value; $bpc=[regex]::Match($t,'Bytes Per Cluster\\s*:\\s*([0-9]+)').Groups[1].Value; $zs=[regex]::Match($t,'Mft Zone Start\\s*:\\s*0x([0-9A-Fa-f]+)').Groups[1].Value; $ze=[regex]::Match($t,'Mft Zone End\\s*:\\s*0x([0-9A-Fa-f]+)').Groups[1].Value; $used=$(if($m -and $fr){[int64](([convert]::ToInt64($m,16))/[int64]$fr)}else{$null}); $total=$(if($zs -and $ze -and $bpc -and $fr){[int64]((([convert]::ToInt64($ze,16)-[convert]::ToInt64($zs,16))*[int64]$bpc)/[int64]$fr)}else{$null}); [pscustomobject]@{Filesystem=$_.FileSystem; 'Inodes(approx)'=$total; 'IUsed(approx)'=$used; 'IFree(approx)'=$(if($total -ne $null -and $used -ne $null){$total-$used}else{$null}); 'IUse%(approx)'=$(if($total -gt 0 -and $used -ne $null){[math]::Round(($used/$total)*100,2)}else{$null}); 'Mounted on'=$_.Name.TrimEnd('\\')} } | Format-Table -Auto
```

# 출력 결과
```text
Filesystem  Inodes(approx)  IUsed(approx)  IFree(approx)  IUse%(approx)  Mounted on
NTFS        786432          15220          771212         1.94           C:\
```

# 설명
- Linux의 inode와 완전히 동일하지는 않지만 NTFS MFT 사용량 관점에서 파일 레코드 소진 위험을 추정합니다.
- 계산 가능한 NTFS 볼륨만 대상으로 하며 계산 불가 시 대상 아님으로 처리될 수 있습니다.

# 임계치
- `max_iuse_percent`: `80.0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 모든 측정 가능 볼륨의 `IUse%`가 임계치 이하입니다.
- **대상 아님**: inode 유사 사용률 계산이 불가능한 환경입니다.
- **경고**: 하나 이상의 볼륨에서 inode 유사 사용률이 임계치를 초과합니다.


