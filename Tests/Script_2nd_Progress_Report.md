# Script — 2nd Progress Report (7 min)

Deck: `2nd Progress Report MIRAI Ricardo_Monrreal.pptx` · 11 visible slides · ~920 spoken words (≈130 wpm).

| # | Slide | Time | Ends at |
|---|---|---|---|
| 1 | Cover | 15 s | 0:15 |
| 2 | Hypotheses | 35 s | 0:50 |
| 3 | Updated Gantt Diagram | 30 s | 1:20 |
| 4 | Real-Time Pipeline Design | 45 s | 2:05 |
| 5 | LSL Simulation Results | 60 s | 3:05 |
| 6 | Live AURA Recordings | 60 s | 4:05 |
| 7 | Session Dashboard | 35 s | 4:40 |
| 8 | Pilot Trends | 50 s | 5:30 |
| 9 | Go/NoGo Protocol Design | 45 s | 6:15 |
| 10 | Next Steps | 30 s | 6:45 |
| 11 | References + closing | 15 s | 7:00 |

Checkpoints: **2:05** leaving the pipeline · **4:05** leaving the recordings · **5:30** leaving the trends. If you are late, shorten slide 7 (the dashboard), not 5, 6 or 8.

---

## 1 · Cover — 15 s (0:00 → 0:15)

> Good afternoon. My name is Ricardo Monrreal, and this is my second progress report on my project: a Closed-Loop Neuroadaptive AR Platform for Scrolling.

## 2 · Hypotheses — 35 s (0:15 → 0:50)

> Just as a quick reminder of the main objective of my project and the main task that I need to evaluate before doing the AR platform. The goal is a closed-loop EEG platform that detects when a user slips into cognitive fatigue and loses inhibitory control while scrolling, and answers with AR feedback.
> Before building the AR, I need to test three hypotheses. **H1**: tonic theta and alpha rise more with scrolling. **H2**: after scrolling, frontal theta in NoGo trials drops and commission errors rise. **H3**: both happen at once, tonic up and phasic down, as Arnau and colleagues reported in 2021.

## 3 · Updated Gantt Diagram — 30 s (0:50 → 1:20)

> We are now in week 8, at the red line. Phases 1 and 2 and the LSL simulation are complete. Since week 7, I have been validating the pipeline with real subjects, which is most of what I will show today. This week is the mentor checkpoint, to collect the results and choose the path. Weeks 9 and 10 are for the AR environment and the research synthesis, and week 11 for the final report.

## 4 · Real-Time Pipeline Design — 45 s (1:20 → 2:05)

> This is the real-time pipeline. Everything is run by one program, **sesion_aura_web.py**, the orchestrator: it launches every process, shows the live dashboard and writes the session report.
> The chain reads from left to right. Aura.exe acquires the EEG. check_lsl_stream finds the right stream. realtime_pipeline cleans the signal. spectral_features extracts tonic theta and periodic alpha. calibration compares them with a two-minute baseline. And jitai decides when to intervene.
> In parallel, semaforo_canales checks the electrodes, and behavior_markers sends the block and NoGo markers to step 6.

## 5 · LSL Simulation Results — 60 s (2:05 → 3:05)

> Before putting the headset on anyone, I tested the pipeline by replaying recorded EEG through LSL: synthetic data and two public datasets, ds007537 and EEG-SVRec.
> Each step has a number that proves it. **Transport**: the stream arrives complete, with 48 milliseconds of latency. **Timing**: each window is filtered in 2.6 milliseconds. **Rejection**: after removing artifacts, 99.1 % of the windows stay valid. **Features**: real-time biomarkers match the offline analysis, r = 0.94. **Calibration**: a two-minute baseline turns them into Z-scores.
> Steps 1 to 5 passed. In step 6, the intervention ladder works, but Level 1, the alpha cue, gave 2 to 11 false alarms in 20 minutes with no fatigue at all. And step 7, tuning, could not be done here: synthetic alpha varies two to four times more than real alpha, and the datasets came from other headsets, in clean conditions. They could not tell me how the AURA behaves in our lab. Only real recordings could.

### Study notes for slide 5 (do not read aloud)

What each step means:

| Step | What it checks | File | Proof on the slide |
|---|---|---|---|
| 1 · Transport | The EEG stream arrives over LSL complete: right rate, no gaps, no drift, low latency | `mock_lsl_streamer.py`, `check_lsl_stream.py` | 48 ms latency (p95, 20 min live at 250 Hz) |
| 2 · Timing | Circular buffer + causal filters: a 6-s window is ready every second, fast enough for real time | `realtime_pipeline.py` | 2.6 ms to filter one window |
| 3 · Rejection | Each 6-s window is split into 9 segments of 2 s; a segment is dropped if it exceeds 150 µV peak-to-peak; the window stays valid if it keeps ≥ 1 clean segment | `realtime_pipeline.py` | 99.1 % valid windows (10 min live, synthetic, 250 Hz, outside the 30-s artifact burst; 94.6 % at 50 Hz) |
| 4 · Features | Spectral decomposition (specparam): tonic θ and periodic α per window | `spectral_features.py` | r = 0.94 real time vs offline |
| 5 · Calibration | 2-min baseline, then frozen: every value becomes a Z-score against that person | `calibration.py` | Baseline → Z-scores |
| 6 · Intervention | JITAI ladder: N1 α cue, N2 behaviour (NoGo errors), N3 θ; with hysteresis, persistence and priority 3 > 2 > 1 | `jitai.py` | Works, but N1 fires too often |
| 7 · Tuning | End-to-end run + adjusting N1: α smoothing τ (5 s), threshold (1.5 σ_Z ≈ 3.2 dB) and persistence (≥ 5 s) | `run_simulation.py` | Open → needs real data |

Why the simulation could not fully verify the pipeline:
- **Synthetic data**: the effects are injected by me, and its alpha fluctuates ~2 dB on its own (σ 2.2–4.4 dB vs 1.03 dB in real EEG). Tuning N1 on it would tune to noise that does not exist in people. On real EEG (ds007537 sub-01) N1 fired only 2 times in ~15 min: the synthetic data is pessimistic.
- **Public datasets**: other headsets, other montages, already clean files. No 60 Hz from our room, no gel drying, no electrodes lifting, no cable failures.
- **Replay is not live**: nothing goes wrong with a file. The problems of a real session only appear with a real person and the AURA (next slide).

## 6 · Live AURA Recordings — 60 s (3:05 → 4:05)

> And that is exactly what happened. From the very first test, the pipeline that passed the simulation failed with real AURA signals, because it had been tuned to synthetic data and clean datasets.
> The chart shows the percentage of valid windows in seven tests. They are pipeline-tuning tests, not study data, and every failure produced a fix. In T1, 60 hertz noise shared by all channels rejected everything, so I added a common average reference. In T2 and T4, electrodes lifted and the gel dried, so now the bad channel is left out of that average. In T3, a noisy Fz, right where we measure theta, rejected every window, so I built an electrode traffic light. In T6, a cable failed mid-session, and we kept the clean first 17 minutes.
> The latest test reached 99 % valid windows, with no signal lost.

## 7 · Session Dashboard — 35 s (4:05 → 4:40)

> To run these sessions, I built a session dashboard: a live web monitor, updated every second. It runs the protocol timeline and shows valid windows, electrode quality, theta and alpha against the baseline, and the interventions. At the end, it writes the report. It is only for the researcher. The participant never sees it: they get the Go/NoGo screen and, later, the AR.

## 8 · Pilot Trends — 50 s (4:40 → 5:30) — speak slowly

> With four usable sessions, I can only show directions. This is exploratory, not a hypothesis test.
> Blink rate, our control measure, is the most consistent: it drops at scroll onset in 4 of 4 sessions and goes up again afterwards in 3 of 3. Tonic theta shows a slight decrease during scrolling in all four, which is the opposite of what H1 predicts. Periodic alpha shows no pattern yet, between plus 1.1 and minus 1.2 dB.
> And H2 and H3 cannot be tested without a Go/NoGo task. That is why the Go/NoGo is the next piece.

## 9 · Go/NoGo Protocol Design — 45 s (5:30 → 6:15)

> The design is simple. The participant uses a lab phone, the same one for everyone, with a web app served by the lab PC over the same Wi-Fi, so there is nothing to install. A normal video means tap; a video with a red border, the NoGo, means do not tap.
> The task is done twice: three minutes before and three minutes after 45 minutes of scrolling. JITAI interventions only run during scrolling; in the Go/NoGo blocks we only measure, while the EEG keeps recording.
> The dashboard timestamps every tap, syncs it with the EEG and keeps one table per participant: commission errors, omissions and mean reaction time, before and after. Smartphone Go/NoGo tasks have already been validated, for example by Perzl and colleagues in 2024.

## 10 · Next Steps — 30 s (6:15 → 6:45)

> Next steps. First, build the Go/NoGo screen and the in-feed NoGo cards. Second, tune the intervention triggers on the sessions I already recorded, starting with Level 1. And third, run the pilot comparing scrolling against a documentary, to test H1 to H3.

## 11 · References + closing — 15 s (6:45 → 7:00)

> These are the references I used. Thank you for your attention; I am happy to take any questions.

---

## Q&A backup (not timed)

- **"Is the theta/blink result significant?"** No. 4 of 4 in the same direction gives p = 0.125 with a sign test. That's why I call it a direction, not a result.
- **"Why a phone and not the PC?"** Same device type as the scrolling, the same lab phone for everyone, taps timestamped on the phone and synced with the EEG; precedent: Perzl et al. (2024). Commission errors are the main measure; RT is secondary.
- **"Where does the 48 ms come from?"** From the 20-min live benchmark at 250 Hz (step 7's end-to-end run), p95 latency; the limit was 500 ms.
- **"Why 2–11 false alarms?"** 6 synthetic sessions of 20 min without injected alpha at 250 Hz: 2, 4, 11, 4, 3, 5 (at 50 Hz: 0–9).

## To check on the slides

- Slide 2: "thonic" → **tonic**.
- Slide 10: confirm the order of items 2 and 3 (the script assumes 2 = tune triggers, 3 = pilot).

---

## Change log

Changes you ask for go here, newest first.

| Date | Slide | Change |
|---|---|---|
| 2026-11-13 | 5 | Rejection tag: "20.2 / 20.5 blinks/min vs eye-tracker" → "99.1 % valid windows · 10 min live" (slide, notes and script) |
| 2026-11-13 | — | First version of the script |
