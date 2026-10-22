# Signal Processing Notes

Educational DSP pipeline (not clinically validated):

```text
ADC samples
  → DC removal / high-pass (~20 Hz)
  → low-pass (~400 Hz)  ⇒ experimental heart-sound band
  → moving-average noise smoothing
  → RMS + peak + variance + band-energy quality score
  → envelope extraction
  → peak / event detection
  → interval filtering (40–180 BPM configurable)
  → averaged / smoothed prototype BPM
```

## Signal quality labels

Derived from RMS, peak, clipping ratio, noise floor proxy, and 20–400 Hz energy ratio:

`No Signal` · `Poor` · `Fair` · `Good` · `Excellent`

If quality is insufficient: BPM displays `--` and **Insufficient signal**.

## Disclaimer

Prototype estimate – not clinically validated.  
CardioSense does **not** diagnose heart disease, murmurs, arrhythmia, or lung disease.
