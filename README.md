# OBD Dataset Analysis

차량 주행 중 수집된 OBD, GPS, 가속도 로거 데이터를 정리하고 기초 분석한 저장소입니다. 원본 데이터는 수정하지 않고 `data/`에 보관했으며, 분석 코드는 `code/`, 생성된 표와 피겨는 `results/`에 분리했습니다.

## 데이터 개요

본 데이터셋은 여러 차량/주행 경로에서 기록된 시계열 로그입니다. 각 CSV 행은 기본적으로 다음 3개 필드로 구성됩니다.

| Column | Description |
| --- | --- |
| `Time step(ms)` | 로거 시동 후 경과 시간, millisecond 단위 |
| `PID` | OBD 또는 센서/GPS 항목 식별자 |
| `Value` | 해당 PID의 기록 값 |

분석 대상 CSV는 총 168개이며, 유효 파싱 행은 28,468,179개입니다. 함께 제공된 문서 파일은 DOCX 5개, 산출물 정의 XLSX 1개입니다. 일부 로그에는 깨진 바이트/행이 포함되어 있어 분석 코드에서 원본은 그대로 둔 채 유효 행만 집계하고, 제외된 행 수는 `bad_rows`로 별도 기록했습니다.

## 폴더 구조

```text
.
|-- code/
|   `-- main.py
|-- data/
|   |-- OBD_관련_기술문서/
|   `-- 차량_OBD_데이터셋/
|-- results/
|   |-- figures/
|   |-- dataset_inventory.csv
|   |-- file_summary.csv
|   |-- pid_counts.csv
|   |-- pid_summary.csv
|   `-- route_summary.csv
`-- README.md
```

## 주요 PID

| PID | Description | Rows |
| --- | --- | ---: |
| `20` | Acceleration x; y; z | 2,049,282 |
| `10D` | Vehicle Speed [km/h] | 2,049,273 |
| `10C` | Engine RPM | 2,049,242 |
| `11F` | Runtime since engine start [s] | 2,049,223 |
| `12F` | Fuel level input [%] | 2,049,211 |
| `146` | Ambient temperature [C] | 2,049,209 |
| `149` | Acceleration pedal position D [%] | 2,049,179 |
| `14A` | Acceleration pedal position E [%] | 2,049,173 |
| `A` | GPS Latitude [degree] | 2,011,915 |
| `B` | GPS Longitude [degree] | 2,011,896 |

주요 분석 관점은 차량 속도, 엔진 RPM, 주행 시간, 연료량, 외기 온도, 가속 페달 포지션, GPS 위치의 변화입니다. `PID 20`은 `x;y;z` 형태의 복합 가속도 값이므로 단일 숫자 통계에서는 제외하거나 별도 분해 분석이 필요합니다.

## 대표 피겨

모든 그래프는 scatter plot과 점선 보조선을 함께 사용했으며, 축 레이블은 원본 데이터의 컬럼명 또는 PID 기반 컬럼명을 따릅니다. 글꼴은 Times New Roman으로 설정했습니다.

### Vehicle Speed vs Engine RPM

속도(`PID 10D`)와 엔진 RPM(`PID 10C`) 사이의 관계를 보여줍니다. 정차/저속 구간의 0 RPM 또는 낮은 RPM 구간과, 속도 증가에 따른 RPM 상승 패턴을 함께 확인할 수 있습니다.

![Vehicle Speed vs Engine RPM](results/figures/speed_vs_rpm_scatter.png)

### GPS Route Samples

GPS 위도(`PID A`)와 경도(`PID B`)를 이용해 전체 주행 위치 샘플을 시각화했습니다. 주행 경로의 공간적 분포를 빠르게 확인하기 위한 피겨입니다.

![GPS Route Samples](results/figures/gps_route_scatter.png)

### Vehicle Speed over Time

로거 기준 시간(`Time step(ms)`)에 따른 차량 속도(`PID 10D`) 변화를 보여줍니다. 주행/정차가 반복되는 구간과 속도 분포를 확인할 수 있습니다.

![Vehicle Speed over Time](results/figures/pid_10D_scatter.png)

### Engine RPM over Time

로거 기준 시간(`Time step(ms)`)에 따른 엔진 RPM(`PID 10C`) 변화입니다. 속도 피겨와 함께 보면 주행 상태와 엔진 반응을 비교할 수 있습니다.

![Engine RPM over Time](results/figures/pid_10C_scatter.png)

## 결과 표

| File | Description |
| --- | --- |
| `results/dataset_inventory.csv` | 전체 파일 목록, 확장자, 파일 크기 |
| `results/file_summary.csv` | CSV 파일별 행 수와 파싱 제외 행 수 |
| `results/route_summary.csv` | 날짜, 경로, 차량 단위 요약 |
| `results/pid_counts.csv` | PID별 출현 빈도 |
| `results/pid_summary.csv` | 숫자형 PID의 평균, 표준편차, 최솟값, 최댓값 |

`route_summary.csv` 기준으로 51개의 날짜/경로/차량 조합이 확인됩니다. `OBD_Data_1120 / Route1 / Vehicle4` 구간에서 깨진 행 169,300개가 감지되어 `bad_rows`에 기록되어 있습니다.

## 재현 방법

Python 환경에서 `pandas`, `matplotlib`, `openpyxl`이 필요합니다.

```powershell
python code/main.py --data-dir data --results-dir results
```

스크립트는 원본 파일을 수정하지 않고 `results/` 아래의 표와 `results/figures/` 아래의 피겨를 다시 생성합니다.
