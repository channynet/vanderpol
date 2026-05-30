# v001 Figure Guide

자세한 figure별 해석은 아래 파일에 정리했다.

- `outputs/versioned_runs/v001_full_pipeline/process_visualizations/FIGURE_GUIDE_KO.md`

핵심 결론:

- 전체 파이프라인은 정상 동작했다.
- scenario별 best algorithm이 다르므로 selector 문제는 의미가 있다.
- 현재 LinUCB selector는 fixed-action baseline보다는 좋지만 ACLS-rule baseline보다 낮다.
- 가장 큰 약점은 decision boundary collapse와 noise robustness다.
- 다음 개선은 실제 ECG 기반 리듬 현실화, noise-aware 학습, adaptive option 개선이다.
