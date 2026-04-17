  # preventive 보고서 타입 추가 계획

  ## Summary

  - --report-type preventive 를 새로 등록하고, 요약 시트는 현재 default 와 동일하게 유지한다.
  - DetailRow 에 description, inspection_command, is_service_affect, action_content 를 추가한다. 누락 시 기본값은 모두 "" 로 처리한다.
  - preventive 의 상세 시트는 호스트별 점검항목 1개당 1개 블록 테이블로 렌더링하고, 각 블록에 application_type_name, application_name, application_version 행을 추가한다.

  ## Key Changes

  - 데이터 모델
      - DetailRow.__init__ / DetailRow.from_mapping / mock 생성부에 새 4개 필드를 추가한다.
      - 기존 application_type_name, application_name, application_version, message 는 그대로 유지하고 preventive 상세 시트에서 모두 출력한다.
  - 보고서 타입 등록
      - PreventiveInspectionReportGenerator 를 추가하고 alias 는 preventive 로 등록한다.
      - 요약 시트 생성 로직은 공용 helper 또는 재사용 메서드로 분리해 default 와 preventive 가 동일한 요약 결과를 만든다.
  - preventive 상세 시트 레이아웃
      - A1 의 요약으로 돌아가기 링크 유지
      - A2 호스트 제목, A3 개요 요약 줄 유지
      - 첫 점검항목 블록은 5행부터 시작
      - 점검항목 1개 = 10개 내용 행 + 2개 빈 행 간격으로 구성한다. 다음 블록 시작 행은 이전 블록 시작 행 + 12
      - 호스트 내 점검항목 순서는 API 응답 순서를 그대로 유지
      - 상세 시트는 기존 표 헤더와 auto_filter 없이 블록만 배치
      - freeze_panes 는 A5
      - 상세 데이터가 없으면 A5:H5 병합 셀에 상세 데이터가 없습니다. 표시
  - 블록 행 배치
      - 1행: A=유형, B:C=type_name, D=영역, E:F=area_name, G=구분, H=category_name
      - 2행: A=애플리케이션유형, B:C=application_type_name, D=애플리케이션명, E:F=application_name, G=버전, H=application_version
      - 3행: A=점검결과, B:D=result_status, E=중요도, F:H=format_importance(importance)
      - 4행: A=점검항목, B:H=inspection_item_name
      - 5행: A=명령어, B:H=inspection_command
      - 6행: A=상세, B:H=raw_output
      - 7행: A=메세지, B:H=message
      - 8행: A=설명, B:H=description
      - 9행: A=서비스 영향 유/무, B:H=is_service_affect
      - 10행: A=조치내역, B:H=action_content

  ## Style / Behavior

  - 결과 색상과 중요도 색상 매핑은 현재 default 구현을 그대로 재사용한다.
  - 라벨 셀은 현재 section 스타일, 값 셀은 현재 value/body 스타일을 재사용한다.
  - 상태/중요도 셀을 제외한 값 셀은 블록 단위 홀짝 배경색을 교차 적용한다.
  - 모든 값 셀은 줄바꿈 허용 + 상단 정렬을 사용한다.
  - raw_output, message, description, action_content 는 데이터가 많이 보이도록 동적 높이 행으로 처리한다.
      - 기준: 줄 수와 문자열 길이(대략 80자당 1줄)를 함께 반영
      - 최소 높이 36, 최대 높이 180
  - 나머지 짧은 행은 높이 24 로 고정한다.

  ## Test Plan

  - DetailRow.from_mapping 이 새 4개 필드를 파싱하고, 누락 시 "" 로 채우는지 테스트한다.
  - get_report_generator("preventive") 가 새 generator 를 반환하는지 테스트한다.
      - A1, A2, A3 가 유지되는지
      - 2행에 application_type_name, application_name, application_version 이 지정한 셀 구조로 들어가는지
      - 기존 결과/중요도 행이 3행으로 밀리는지
      - 블록 간 공백이 2행인지
      - 결과/중요도 색상이 기존 규칙대로 적용되는지
      - 긴 raw_output / description / action_content 에서 행 높이가 증가하는지
      - 상세 데이터가 없을 때 A5:H5 안내 문구가 출력되는지
  - 기존 default / inspection 테스트는 그대로 통과해야 한다.

  ## Assumptions

  - preventive 도 현재와 동일한 summary/detail API 를 사용한다.
  - 새 4개 필드는 상세 API 응답에 없을 수 있으므로 빈 문자열 기본값으로 처리한다.
  - application_* 행 라벨은 애플리케이션유형, 애플리케이션명, 버전 으로 고정한다.
  - 새 블록형 상세 레이아웃은 preventive 에만 적용하고, 기존 타입의 상세 표 레이아웃은 변경하지 않는다.