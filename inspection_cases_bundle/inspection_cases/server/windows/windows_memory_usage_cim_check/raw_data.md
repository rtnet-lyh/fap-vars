# 영역
MEMORY

# 세부 점검 항목
메모리 및 스왑 사용률

# 점검 내용
물리 메모리 총량/사용량/여유량과 PageFile 기반 스왑 사용률을 함께 점검합니다.

# 구분
필수

# 명령어
```powershell
$os=Get-CimInstance Win32_OperatingSystem;$pf=Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue;$mt=[double]$os.TotalVisibleMemorySize*1KB;$mf=[double]$os.FreePhysicalMemory*1KB;$mu=$mt-$mf;$pt=([double](($pf|Measure-Object -Property AllocatedBaseSize -Sum).Sum))*1MB;$pu=([double](($pf|Measure-Object -Property CurrentUsage -Sum).Sum))*1MB;if(-not $pt){$pt=0};if(-not $pu){$pu=0};$pfree=[Math]::Max($pt-$pu,0);'MEM total={0:N2}GiB used={1:N2}GiB free={2:N2}GiB usage={3:N2}% | SWAP total={4:N2}GiB used={5:N2}GiB free={6:N2}GiB' -f ($mt/1GB),($mu/1GB),($mf/1GB),(($mu/$mt)*100),($pt/1GB),($pu/1GB),($pfree/1GB)
```

# 출력 결과
```text
MEM total=15.73GiB used=6.92GiB free=8.81GiB usage=44.00% | SWAP total=2.00GiB used=0.10GiB free=1.90GiB
```

# 설명
- 메모리 사용률, 메모리 여유율, 스왑 사용률을 각각 계산해 종합 판정합니다.
- 메모리는 정상인데 스왑이 과도하게 쓰이는 상황도 분리해서 감지합니다.

# 임계치
- `max_memory_usage_percent`: `80.0`
- `min_memory_free_percent`: `20.0`
- `max_swap_usage_percent`: `50.0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 메모리 사용률과 스왑 사용률이 낮고 메모리 여유율이 충분합니다.
- **경고**: 메모리 사용률 과다, 여유율 부족, 스왑 사용률 과다 중 하나라도 발생합니다.


