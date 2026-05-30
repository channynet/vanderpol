"""External ECG and guideline data manifest."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalDataset:
    name: str
    role: str
    url: str
    phase: str
    required_for_stage: str


EXTERNAL_DATASETS: tuple[ExternalDataset, ...] = (
    ExternalDataset(
        name="MIT-BIH Arrhythmia Database",
        role="R-peak, RR, QRS, and arrhythmia morphology validation.",
        url="https://physionet.org/content/mitdb/1.0.0/",
        phase="Phase 1 and Phase 3",
        required_for_stage="Needed before real ECG feature validation.",
    ),
    ExternalDataset(
        name="Creighton University Ventricular Tachyarrhythmia Database",
        role="VT, ventricular flutter, and VF-like waveform validation.",
        url="https://physionet.org/content/cudb/1.0.0/",
        phase="Phase 1 and Phase 3",
        required_for_stage="Needed before VT/VF realism claims.",
    ),
    ExternalDataset(
        name="PhysioNet/CinC Challenge 2015",
        role="Noisy ICU arrhythmia alarm and false-alarm robustness.",
        url="https://physionet.org/content/challenge-2015/1.0.0/",
        phase="Phase 3 and Phase 5",
        required_for_stage="Needed before noise/generalization experiments.",
    ),
    ExternalDataset(
        name="PTB-XL",
        role="Optional large-scale 12-lead pretraining for learned ECG encoder.",
        url="https://physionet.org/content/ptb-xl/1.0.3/",
        phase="Phase 3 extension",
        required_for_stage="Optional until learned encoder pretraining begins.",
    ),
    ExternalDataset(
        name="AHA ACLS tachyarrhythmia guidance",
        role="Rule baseline and threshold anchors.",
        url="https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines/adult-advanced-life-support/",
        phase="Phase 1, Phase 4, and reporting",
        required_for_stage="Needed before formal ACLS baseline claims.",
    ),
    ExternalDataset(
        name="ICD/ATP and resonant-drift literature",
        role="Treatment probability, safety, and energy calibration anchors.",
        url="https://pubmed.ncbi.nlm.nih.gov/",
        phase="Phase 2 calibration",
        required_for_stage="Needed before non-toy treatment calibration.",
    ),
)
