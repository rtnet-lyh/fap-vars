# 영역
STORAGE

# 세부 점검 항목
DB 엔진 파일시스템 사용률

# 점검 내용
Oracle 엔진 경로가 위치한 Windows 볼륨의 남은 공간과 전체 크기를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); 
$path = 'D:\app\oracle'; $driveLetter = (Get-Item $path).PSDrive.Name;  Get-Volume -DriveLetter $driveLetter |
Select-Object DriveLetter, FileSystemLabel, SizeRemaining, Size
```

# 출력 결과
```text
DriveLetter FileSystemLabel SizeRemaining         Size
----------- --------------- -------------         ----
          D Data             211585671168 384973139968
```

# 설명
- Linux `df -h` 대신 Windows `Get-Volume` 기준으로 볼륨 사용량을 확인합니다.
- DB 엔진 경로가 어느 드라이브에 올라가 있는지와 남은 공간이 충분한지를 함께 봅니다.

# 환경별 치환 값
- `ORACLE_BASE_PATH`: 현재값 `D:\app\oracle`
- 명령어 치환 위치: `D:\app\oracle`

# 임계치
- `max_filesystem_use_percent`: `80.0`
- `min_filesystem_avail_percent`: `20.0`

# 판단기준
- **정상**: 엔진 볼륨 사용률이 80% 이하이고 남은 공간이 충분합니다.
- **불량**: 사용률이 높거나 남은 공간이 부족합니다.
