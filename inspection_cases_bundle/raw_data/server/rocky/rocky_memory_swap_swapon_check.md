# 영역
MEMORY

# 세부 점검항목
Paging Space

# 점검 내용
사용 가능한 가상 메모리 사용률 확인(해당 수치가 높은 경우 메모리의 부족 판단시 사용)

# 구분
필수

# 명령어
swapon -s

# 출력 결과
Filename                                Type            Size    Used    Priority
/dev/sda3                               partition       1048572 0       -1
/dev/sdb3                               partition       1048572 128     -2
/var/swap/swapfile1                     file            2097148 4096    -3
/var/swap/swapfile2                     file            2097148 0       -4

# 설명
본 항목은 swapon -s 명령 결과를 기준으로 시스템의 스왑 사용 현황을 점검한다.
스왑 사용량은 물리 메모리 부족 여부를 간접적으로 판단할 수 있는 지표이다.
스왑 사용률이 낮거나 사용되지 않으면 일반적으로 메모리 상태가 양호한 것으로 본다.
반대로 스왑 사용률이 높으면 메모리 압박 또는 성능 저하 가능성이 있으므로 주의가 필요하다. 사용률을 기준으로 양호, 불량을 판단한다.

# 임계치
메모리 사용률, max_swap_usage_percent, min_swap_size_gb

# 판단기준
각 메모리의 사용률이 50% 초과


