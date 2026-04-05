## Autoreport v0.4.1 개발 일지

기준 날짜: `2026-04-05`

이번 `v0.4.1`은 `v0.5`로 넘어가기보다 `v0.4` 선 안에서 한 번 더 다듬는 쪽을 선택한 릴리즈였습니다. 이미 `codex/v0.4-master` 위에는 manual template, screenshot-first public flow, browser evidence, guide handoff 같은 변화가 충분히 쌓여 있었지만, 그렇다고 해서 곧바로 새로운 메이저한 제품 표면을 열었다고 말하기에는 아직 이른 상태였습니다. 그래서 이번에는 선을 더 크게 벌리기보다, 지금 실제로 보여 주고 검증한 `v0.4` 흐름을 `0.4.1`이라는 이름으로 묶는 편이 더 정확하다고 봤습니다.

이번 판단에서 중요했던 점은 기능 개수보다 release surface의 성격이었습니다. public 웹은 이제 built-in manual procedure starter를 중심으로 돌아가고, 필요한 스크린샷을 각 slide preview 옆에서 맞춰 넣는 흐름이 핵심이 됐습니다. CLI와 debug 앱은 여전히 더 넓은 contract inspection과 image-backed authoring을 맡고 있지만, public homepage는 그보다 더 좁고 설명 가능한 경로만 보여 주는 쪽이 맞았습니다. 이 상태는 `v0.5`처럼 새로운 제품선을 선언하기보다, `v0.4.x` 안에서 계속 정제해 나갈 성격에 더 가깝습니다.

## 이번 버전에서 묶은 것

- built-in `autoreport_manual` 템플릿을 public 웹 starter, CLI, template flow 전반에서 같은 기준으로 다듬었습니다.
- public 홈페이지가 `Refresh Slide Assets`, aligned upload panel, slide preview를 묶은 screenshot-first manual flow를 기본 동선으로 갖도록 정리했습니다.
- public 웹은 built-in manual upload flow만 허용하고, 그보다 넓은 image-backed draft는 계속 debug 앱과 CLI에 남겨 두는 경계를 다시 분명하게 했습니다.
- `python -m autoreport.web.serve public|debug`와 `run-public.cmd`, `run-debug.cmd`를 통해 로컬 launch 경로도 더 명확하게 정리했습니다.
- Playwright evidence runner와 guide-image promotion 흐름을 release-facing 검증 루프에 올렸고, Gemini/ChatGPT/Claude insert 이미지는 shared static asset으로 handoff에 같이 실리도록 묶었습니다.

## 왜 0.5가 아니라 0.4.1인가

이번에 올라온 변화는 분명 `v0.3.1`보다 큽니다. manual template이 실제 public story의 중심으로 올라왔고, 홈페이지 흐름도 text-only starter 설명에서 screenshot-first manual demo로 바뀌었습니다. 하지만 여기서 바로 `v0.5`를 선언하면, 마치 또 다른 넓은 제품 경계가 이미 확정된 것처럼 보이게 됩니다.

지금은 그 단계보다 한 칸 전입니다. `v0.4` 안에서 public manual flow, guide wording, browser evidence, release handoff를 계속 조정해야 할 여지가 남아 있습니다. 그래서 이번 버전 번호는 "더 큰 선으로 넘어간다"는 의미보다 "지금 검증된 `v0.4` 표면을 한 번 안정적으로 묶는다"는 의미에 더 가깝습니다.

## 현재 상태

이제 `v0.4.1` 기준 상태는 다음처럼 이해하면 됩니다.

- semantic version은 `0.4.1`입니다.
- public 웹은 built-in manual procedure starter를 중심으로 유지합니다.
- screenshot upload와 slide preview는 public manual flow 안에서 함께 동작합니다.
- broader image-backed draft, contract inspection, compiled payload 확인은 계속 debug 앱과 CLI가 맡습니다.
- release-facing guide, release note, development log, handoff source는 `docs/posts/` 기준으로 같이 움직입니다.

## 실제 검증 기준

이번 릴리즈 prep은 아래 검증 기준으로 확인했습니다.

```bash
.\venv\Scripts\python.exe -m unittest tests.test_cli tests.test_validator tests.test_generator tests.test_web_app tests.test_web_debug_app tests.test_web_serve tests.test_autorelease_handoff tests.test_public_web_playwright
.\venv\Scripts\python.exe tests\e2e\run_public_web_playwright.py --version 0.4.1 --promote-guide-image
```

이 검증은 manual built-in contract와 generation path가 계속 맞는지, public 홈페이지가 aligned upload/preview manual flow를 유지하는지, debug 앱과 handoff가 새 release-facing 기준과 계속 맞는지, 그리고 실제 브라우저에서 `autoreport_demo.pptx` download가 다시 관찰되는지를 함께 확인하는 용도입니다.

## 다음 단계

- `v0.4.1` source post와 evidence를 기준으로 `autorelease` handoff를 마무리하기
- public sample deck 같은 외부 배포 자산은 별도 release asset으로 정리하기
- `v0.5`로 바로 넘어가기보다 `v0.4.x` 안에서 manual flow와 문서/evidence 루프를 더 단단하게 다듬기

이번 `v0.4.1`은 새로운 제품선을 과장해서 선언하는 버전이 아니라, 이미 구현하고 검증한 `v0.4` manual flow를 태그 가능한 수준으로 다시 묶는 버전이었습니다. 덕분에 이제 다음 개선도 같은 `v0.4` 선 안에서 더 차분하게 이어 갈 수 있게 됐습니다.
