# 영역
STORAGE

# 세부 점검 항목
아카이브/변경 로그 파일시스템 사용률

# 점검 내용
Oracle 아카이브/변경 로그가 저장되는 Windows 볼륨 사용률을 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); 
$path = 'D:\ORAARCH'; $driveLetter = (Get-Item $path).PSDrive.Name;  Get-Volume -DriveLetter $driveLetter |
Select-Object DriveLetter, FileSystemLabel, SizeRemaining, Size
```

# 출력 결과
```text
DriveLetter FileSystemLabel SizeRemaining         Size
----------- --------------- -------------         ----
          D Data             211585671168 384973139968
```

# 설명
- 아카이브 로그 저장 볼륨이 가득 차면 로그 스위치와 백업 작업에 직접 영향이 갈 수 있습니다.
- 엔진 볼륨과 분리되어 있는지, 여유 공간이 충분한지 함께 확인합니다.

# 환경별 치환 값
- `ORACLE_ARCHIVE_PATH`: 현재값 `D:\ORAARCH`
- 명령어 치환 위치: `D:\ORAARCH`

# 임계치
- `max_archive_use_percent`: `80.0`
- `min_archive_avail_percent`: `20.0`

# 판단기준
- **정상**: 로그 보관 볼륨 사용률이 기준 이하입니다.
- **불량**: 로그 보관 볼륨 공간이 부족합니다.
