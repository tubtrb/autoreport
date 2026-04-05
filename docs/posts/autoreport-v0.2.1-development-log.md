## Autoreport v0.2.1 개발 일지

기준 날짜: `2026-03-28`

이번 `v0.2.1` 작업은 `v0.1.0`에서 만든 CLI 기반 weekly report 생성기를 바탕으로, 더 많은 사용자가 직접 만져볼 수 있는 공개 진입면을 만드는 데 집중한 기록입니다. 핵심은 새로운 생성 엔진을 만드는 것이 아니라, 기존의 검증과 PPTX 생성 파이프라인을 웹에서도 자연스럽게 꺼내는 일이었습니다.

## 이번 버전에서 정리한 일

- YAML 텍스트를 바로 받아 처리하는 웹 경로를 추가했습니다.
- CLI와 같은 코어 파이프라인을 웹 데모에서도 재사용하도록 맞췄습니다.
- 공개 데모 화면을 영문 기준으로 정리해 해외 유입에도 바로 설명이 되도록 다듬었습니다.
- `Load Example`과 `Generate PPTX`만으로 흐름이 이해되도록 화면 구조를 단순화했습니다.
- 기능 단위 검사를 쉽게 하기 위해 `docs/architecture/` 아래에 설계도 문서를 추가했습니다.
- 릴리즈 직전 검증과 문서 자산 수집 흐름을 같이 다룰 수 있도록 정리했습니다.

## 왜 웹 데모를 먼저 붙였는가

현재 Autoreport의 코어는 이미 동작합니다. 다만 기존 진입점은 CLI와 YAML 파일 중심이어서, 기능을 바로 체험하기에는 진입 장벽이 있었습니다. 그래서 이번에는 기능을 크게 넓히기보다, 지금 있는 엔진을 더 쉽게 보여주는 쪽으로 방향을 잡았습니다.

웹 데모는 새로운 제품을 따로 만든 것이 아니라, 같은 검증과 생성 흐름을 브라우저에서 만날 수 있게 한 공개 창구에 가깝습니다. 그래서 `v0.2.1`은 화면 작업처럼 보이지만 실제로는 제품 입구를 정리하는 버전이라고 보는 편이 맞습니다.

## 영문 웹 데모로 바꾼 이유

문서와 공개 페이지가 같이 움직이기 시작하면, 한국어만으로는 소개 범위가 금방 좁아집니다. 특히 릴리즈 노트와 사용 가이드를 영어로 가져가려면, 데모 화면도 같은 톤으로 설명되는 편이 자연스럽습니다.

이번 정리에서는 웹 데모 문구를 영어로 바꾸면서, 홈페이지에서 처음 보이는 메시지와 상태 패널, 버튼 텍스트가 문서와 직접 연결되도록 맞췄습니다. 이제 가이드에서 설명하는 버튼 이름과 실제 화면이 바로 이어질 수 있습니다.

## 기능 단위 검사를 위한 설계도 정리

웹 데모가 붙고 문서 범위가 넓어지면서, 이제는 코드가 실제로 어떤 흐름으로 설계되어 있는지 다시 읽어내는 일이 더 중요해졌습니다. GUI가 없는 상태에서는 특히 더 그렇습니다. 단순히 코드를 열어보는 것만으로는 CLI, 웹 데모, 검증, PPTX 생성이 어디서 합류하고 어디서 갈라지는지 한 번에 잡히지 않기 때문입니다.

그래서 이번에는 `docs/architecture/` 아래에 현재 코어를 설명하는 문서를 같이 정리했습니다. 시스템 개요, CLI 시퀀스, 웹 데모 시퀀스, generation flow, 오류 맵, 기능별 테스트 맵, 입력 계약을 각각 나눠 정리해두었고, 나중에 기능 단위 검사를 할 때도 이 문서들을 바로 기준점으로 삼을 수 있게 만들었습니다.

이 작업은 새로운 기능을 하나 더 붙인 것이라기보다, 지금의 `Autoreport`를 더 읽기 쉽고 점검하기 쉬운 상태로 만드는 정리 작업에 가깝습니다.

### 현재 구조 한눈에 보기

아래 그림은 현재 `Autoreport`의 코어 구조를 한 장으로 요약한 것입니다. CLI와 웹 데모가 서로 다른 진입점을 가지지만, 결국 같은 검증과 PPTX 생성 경로로 합류한다는 점이 핵심입니다.

![Autoreport system overview diagram](devlog-image-v0.2.1/system-overview-1.png)

### 기능별 검사 기준

기능 단위 검사를 할 때는 화면보다 테스트의 책임 범위를 먼저 보는 편이 더 빠를 때가 많습니다. 그래서 각 기능이 어떤 테스트 모듈과 연결되는지도 따로 정리해두었습니다.

![Autoreport feature-to-test map](devlog-image-v0.2.1/feature-test-map-1.png)

## 검증과 문서 작업을 같이 묶은 이유

이번 작업을 하면서 분명해진 점은, 릴리즈 문서를 쓰는 일과 릴리즈를 검증하는 일이 생각보다 강하게 연결되어 있다는 점입니다. 실제로 문서를 쓰다 보면 결국 아래 질문을 다시 확인하게 됩니다.

- 지금 이 흐름이 정말 되는가
- 어떤 화면을 캡처해야 설명이 정확한가
- 이 문장은 테스트나 실제 브라우저 결과로 뒷받침되는가

그래서 이번 브랜치에서는 릴리즈 직전 검증과 증거 수집 흐름도 같이 정리했습니다. 문서를 나중에 꾸미기보다, 검증하는 순간 바로 자료를 모아두는 쪽이 훨씬 효율적이기 때문입니다.

## 실제 검증 기록

이번에는 단순히 “동작했다”고 적는 대신, 실제로 어떤 명령을 썼고 어떤 결과를 확인했는지도 같이 남겼습니다. 릴리즈 직전에는 이런 기록이 있어야 문서의 신뢰도가 더 높아집니다.

### 1. 웹 계약 테스트

```bash
.\venv\Scripts\python.exe -m unittest tests.test_web_app
```

```text
......
----------------------------------------------------------------------
Ran 6 tests in 0.078s

OK
```

웹 데모의 기본 계약은 여기서 다시 확인했습니다. 홈페이지 렌더링, `/healthz`, `/api/generate` 성공 경로, `400/422/500` 오류 응답까지 모두 현재 기준으로 통과했습니다.

### 2. 코어 회귀 테스트

```bash
.\venv\Scripts\python.exe -m unittest tests.test_cli tests.test_loader tests.test_validator tests.test_generator tests.test_pptx_writer tests.test_web_app
```

```text
.................................
----------------------------------------------------------------------
Ran 33 tests in 0.320s

OK
```

즉 웹 데모만 통과한 것이 아니라, CLI, YAML 로더, validator, generation, PPTX writer, 웹 앱까지 현재 브랜치 기준 핵심 계약이 함께 유지되고 있음을 다시 확인했습니다.

### 3. 실제 브라우저 smoke test

서버를 띄운 뒤, 실제 브라우저에서 데모를 열고 예제를 불러와 `.pptx` 다운로드까지 확인했습니다.

```bash
.\venv\Scripts\python.exe -m uvicorn autoreport.web.app:app --host 127.0.0.1 --port 8000
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/healthz
npx --yes @playwright/cli -s=v021verify3 open http://127.0.0.1:8000/ --browser chrome
npx --yes @playwright/cli -s=v021verify3 snapshot
npx --yes @playwright/cli -s=v021verify3 click e16
npx --yes @playwright/cli -s=v021verify3 click e26
npx --yes @playwright/cli -s=v021verify4 open http://127.0.0.1:8000/ --browser msedge
npx --yes @playwright/cli -s=v021verify4 snapshot
```

```text
{"status":"ok"}
Page URL: http://127.0.0.1:8000/
Page Title: Autoreport Demo
Downloaded file weekly_report.pptx to ".playwright-cli\\weekly-report.pptx"
Generation complete. Your download should begin shortly.
```

여기서 `e16`, `e26`은 해당 Playwright 스냅샷 세션에서 잡힌 버튼 ref입니다. 중요한 점은 `chrome`에서 실제 다운로드 이벤트가 발생했고, `msedge`에서도 같은 URL과 타이틀로 홈페이지 로드가 재확인됐다는 점입니다.

### 실제 성공 화면

최종적으로는 아래처럼 상태 패널이 성공 상태로 바뀌고, `weekly_report.pptx` 다운로드가 시작되는 흐름을 확인했습니다.

![Autoreport demo success state after PPTX generation](devlog-image-v0.2.1/generation-success.png)

즉 `v0.2.1`은 단순히 공개 데모를 붙인 상태를 넘어서, 문서와 릴리즈 준비를 같이 진행할 수 있는 기준점까지 올라온 셈입니다.

## 다음 단계

다음은 기능 확장보다는 공개 흐름을 더 매끄럽게 만드는 쪽에 가깝습니다.

- WordPress 게시 흐름 정리
- 공개용 PPTX 샘플과 이미지 자산 업로드
- 릴리즈 노트와 사용 가이드의 반복 생성 절차 정리
- 이후 버전에서 richer layout과 branding 대응 검토

`v0.2.1`은 웹 화면 하나를 추가한 기록이 아니라, Autoreport를 실제 외부 사용자에게 설명하고 보여줄 수 있는 형태로 정돈하기 시작한 버전입니다.
