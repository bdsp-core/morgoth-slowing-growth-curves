# Held-out centile calibration (review item C198)

Fraction of held-out observations below each model-predicted centile. A calibrated model puts the observed value on the nominal one. Bands are patient-clustered bootstrap 95% CIs.

**internal held-out normals** — max |observed − nominal| = **9.2 points** (median 1.1); 42,631 observations, 1,454 patients.

**external no-slowing (ON-100)** — max |observed − nominal| = **21.0 points** (median 2.3); 1,882 observations, 66 patients.

## Per-stage coverage and discrepancy

| arm | stage | observations | patients | median \|observed − nominal\| | max |
|---|---|---|---|---|---|
**Held-out split.** The norms are fitted on a seeded **3,000**-recording sample of the clean-normal reference; the remaining **7,216** clean-normal recordings (**6,779** patients) are held out and are what this page scores.

| internal held-out normals | W | 42,631 | 1,454 | 0.9 | 5.4 |
| internal held-out normals | N1 | 14,113 | 1,275 | 0.6 | 3.2 |
| internal held-out normals | N2 | 17,820 | 1,086 | 1.1 | 2.6 |
| internal held-out normals | N3 | 4,836 | 420 | 3.7 | 9.2 |
| internal held-out normals | REM | 8,629 | 1,155 | 0.8 | 4.0 |
| external no-slowing (ON-100) | W | 1,882 | 66 | 2.6 | 4.9 |
| external no-slowing (ON-100) | N1 | 837 | 66 | 3.5 | 21.0 |
| external no-slowing (ON-100) | N2 | 835 | 61 | 2.8 | 7.7 |
| external no-slowing (ON-100) | REM | 493 | 59 | 1.8 | 8.1 |

| stage | feature | arm | nominal | observed | 95% CI |
|---|---|---|---|---|---|
| W | relative delta | internal held-out normals | 3 | 2.08 | 1.7–2.51 |
| W | relative delta | internal held-out normals | 10 | 9.61 | 8.67–10.66 |
| W | relative delta | internal held-out normals | 25 | 25.76 | 24.31–27.57 |
| W | relative delta | internal held-out normals | 50 | 50.77 | 49.02–52.77 |
| W | relative delta | internal held-out normals | 75 | 73.68 | 72.14–75.31 |
| W | relative delta | internal held-out normals | 90 | 89.17 | 88.18–90.15 |
| W | relative delta | internal held-out normals | 97 | 97.43 | 97.0–97.86 |
| W | relative delta | external no-slowing (ON-100) | 3 | 1.17 | 0.05–2.98 |
| W | relative delta | external no-slowing (ON-100) | 10 | 7.07 | 3.62–12.07 |
| W | relative delta | external no-slowing (ON-100) | 25 | 20.09 | 14.06–27.36 |
| W | relative delta | external no-slowing (ON-100) | 50 | 45.16 | 37.81–52.88 |
| W | relative delta | external no-slowing (ON-100) | 75 | 70.78 | 63.21–76.98 |
| W | relative delta | external no-slowing (ON-100) | 90 | 87.67 | 83.02–91.64 |
| W | relative delta | external no-slowing (ON-100) | 97 | 96.6 | 94.44–98.26 |
| W | log TAR | internal held-out normals | 3 | 1.71 | 1.2–2.24 |
| W | log TAR | internal held-out normals | 10 | 8.69 | 7.46–9.96 |
| W | log TAR | internal held-out normals | 25 | 24.95 | 23.04–26.87 |
| W | log TAR | internal held-out normals | 50 | 50.3 | 48.09–52.54 |
| W | log TAR | internal held-out normals | 75 | 74.79 | 72.97–76.54 |
| W | log TAR | internal held-out normals | 90 | 90.22 | 89.19–91.04 |
| W | log TAR | internal held-out normals | 97 | 98.45 | 98.17–98.72 |
| W | log TAR | external no-slowing (ON-100) | 3 | 0.43 | 0.06–0.98 |
| W | log TAR | external no-slowing (ON-100) | 10 | 5.1 | 2.22–8.75 |
| W | log TAR | external no-slowing (ON-100) | 25 | 21.31 | 13.39–28.47 |
| W | log TAR | external no-slowing (ON-100) | 50 | 48.67 | 38.41–58.81 |
| W | log TAR | external no-slowing (ON-100) | 75 | 70.24 | 61.47–78.46 |
| W | log TAR | external no-slowing (ON-100) | 90 | 85.92 | 79.62–91.96 |
| W | log TAR | external no-slowing (ON-100) | 97 | 95.75 | 92.64–98.28 |
| W | log DAR | internal held-out normals | 3 | 0.32 | 0.23–0.41 |
| W | log DAR | internal held-out normals | 10 | 4.61 | 3.98–5.32 |
| W | log DAR | internal held-out normals | 25 | 21.94 | 20.43–23.68 |
| W | log DAR | internal held-out normals | 50 | 48.59 | 46.63–50.7 |
| W | log DAR | internal held-out normals | 75 | 73.43 | 72.01–75.11 |
| W | log DAR | internal held-out normals | 90 | 88.88 | 87.86–89.93 |
| W | log DAR | internal held-out normals | 97 | 97.09 | 96.69–97.43 |
| W | log DAR | external no-slowing (ON-100) | 3 | 1.28 | 0.06–3.31 |
| W | log DAR | external no-slowing (ON-100) | 10 | 5.31 | 2.12–9.34 |
| W | log DAR | external no-slowing (ON-100) | 25 | 20.83 | 14.48–28.06 |
| W | log DAR | external no-slowing (ON-100) | 50 | 50.16 | 41.79–58.7 |
| W | log DAR | external no-slowing (ON-100) | 75 | 72.69 | 64.73–79.84 |
| W | log DAR | external no-slowing (ON-100) | 90 | 89.74 | 85.97–93.56 |
| W | log DAR | external no-slowing (ON-100) | 97 | 98.14 | 96.88–99.18 |
| N1 | relative delta | internal held-out normals | 3 | 2.78 | 2.27–3.27 |
| N1 | relative delta | internal held-out normals | 10 | 9.45 | 8.53–10.39 |
| N1 | relative delta | internal held-out normals | 25 | 24.97 | 23.45–26.53 |
| N1 | relative delta | internal held-out normals | 50 | 49.22 | 47.45–51.09 |
| N1 | relative delta | internal held-out normals | 75 | 73.43 | 71.86–74.97 |
| N1 | relative delta | internal held-out normals | 90 | 89.24 | 87.94–90.42 |
| N1 | relative delta | internal held-out normals | 97 | 96.45 | 95.47–97.29 |
| N1 | relative delta | external no-slowing (ON-100) | 3 | 8.84 | 1.23–19.69 |
| N1 | relative delta | external no-slowing (ON-100) | 10 | 16.85 | 6.79–28.63 |
| N1 | relative delta | external no-slowing (ON-100) | 25 | 30.23 | 19.17–43.08 |
| N1 | relative delta | external no-slowing (ON-100) | 50 | 51.37 | 40.49–61.94 |
| N1 | relative delta | external no-slowing (ON-100) | 75 | 75.15 | 65.71–83.14 |
| N1 | relative delta | external no-slowing (ON-100) | 90 | 89.61 | 84.01–93.76 |
| N1 | relative delta | external no-slowing (ON-100) | 97 | 97.49 | 95.99–98.76 |
| N1 | log TAR | internal held-out normals | 3 | 2.86 | 2.31–3.45 |
| N1 | log TAR | internal held-out normals | 10 | 8.83 | 7.77–9.91 |
| N1 | log TAR | internal held-out normals | 25 | 23.47 | 21.71–25.5 |
| N1 | log TAR | internal held-out normals | 50 | 48.76 | 46.31–51.06 |
| N1 | log TAR | internal held-out normals | 75 | 74.56 | 72.34–76.81 |
| N1 | log TAR | internal held-out normals | 90 | 90.0 | 88.29–91.73 |
| N1 | log TAR | internal held-out normals | 97 | 96.78 | 95.84–97.83 |
| N1 | log TAR | external no-slowing (ON-100) | 3 | 2.03 | 0.63–4.51 |
| N1 | log TAR | external no-slowing (ON-100) | 10 | 6.45 | 3.57–10.62 |
| N1 | log TAR | external no-slowing (ON-100) | 25 | 20.55 | 13.76–29.24 |
| N1 | log TAR | external no-slowing (ON-100) | 50 | 38.23 | 28.24–51.55 |
| N1 | log TAR | external no-slowing (ON-100) | 75 | 54.0 | 40.91–70.29 |
| N1 | log TAR | external no-slowing (ON-100) | 90 | 85.07 | 74.21–93.54 |
| N1 | log TAR | external no-slowing (ON-100) | 97 | 95.34 | 89.73–98.72 |
| N1 | log DAR | internal held-out normals | 3 | 2.39 | 1.86–2.9 |
| N1 | log DAR | internal held-out normals | 10 | 8.47 | 7.48–9.75 |
| N1 | log DAR | internal held-out normals | 25 | 22.99 | 21.24–24.71 |
| N1 | log DAR | internal held-out normals | 50 | 46.82 | 44.47–49.14 |
| N1 | log DAR | internal held-out normals | 75 | 73.22 | 71.22–75.39 |
| N1 | log DAR | internal held-out normals | 90 | 89.51 | 88.01–90.88 |
| N1 | log DAR | internal held-out normals | 97 | 96.38 | 95.37–97.27 |
| N1 | log DAR | external no-slowing (ON-100) | 3 | 8.24 | 1.71–18.6 |
| N1 | log DAR | external no-slowing (ON-100) | 10 | 15.89 | 6.75–28.18 |
| N1 | log DAR | external no-slowing (ON-100) | 25 | 31.3 | 19.84–43.56 |
| N1 | log DAR | external no-slowing (ON-100) | 50 | 50.9 | 38.33–63.41 |
| N1 | log DAR | external no-slowing (ON-100) | 75 | 73.48 | 62.18–82.87 |
| N1 | log DAR | external no-slowing (ON-100) | 90 | 90.8 | 85.85–94.67 |
| N1 | log DAR | external no-slowing (ON-100) | 97 | 98.09 | 96.78–99.07 |
| N2 | relative delta | internal held-out normals | 3 | 2.86 | 2.1–3.62 |
| N2 | relative delta | internal held-out normals | 10 | 8.52 | 7.26–9.75 |
| N2 | relative delta | internal held-out normals | 25 | 22.36 | 20.51–24.09 |
| N2 | relative delta | internal held-out normals | 50 | 48.11 | 45.9–50.55 |
| N2 | relative delta | internal held-out normals | 75 | 74.93 | 73.0–77.02 |
| N2 | relative delta | internal held-out normals | 90 | 90.45 | 89.16–91.66 |
| N2 | relative delta | internal held-out normals | 97 | 97.37 | 96.64–97.96 |
| N2 | relative delta | external no-slowing (ON-100) | 3 | 3.35 | 1.74–5.65 |
| N2 | relative delta | external no-slowing (ON-100) | 10 | 14.49 | 9.08–22.47 |
| N2 | relative delta | external no-slowing (ON-100) | 25 | 31.5 | 23.35–42.48 |
| N2 | relative delta | external no-slowing (ON-100) | 50 | 57.72 | 48.86–67.71 |
| N2 | relative delta | external no-slowing (ON-100) | 75 | 81.08 | 73.99–87.41 |
| N2 | relative delta | external no-slowing (ON-100) | 90 | 95.33 | 90.74–98.66 |
| N2 | relative delta | external no-slowing (ON-100) | 97 | 98.8 | 96.96–99.89 |
| N2 | log TAR | internal held-out normals | 3 | 5.06 | 3.87–6.25 |
| N2 | log TAR | internal held-out normals | 10 | 11.89 | 10.4–13.69 |
| N2 | log TAR | internal held-out normals | 25 | 25.38 | 23.44–27.59 |
| N2 | log TAR | internal held-out normals | 50 | 48.78 | 46.4–51.17 |
| N2 | log TAR | internal held-out normals | 75 | 75.31 | 73.28–77.29 |
| N2 | log TAR | internal held-out normals | 90 | 91.64 | 90.36–92.85 |
| N2 | log TAR | internal held-out normals | 97 | 98.06 | 97.5–98.55 |
| N2 | log TAR | external no-slowing (ON-100) | 3 | 5.75 | 2.19–9.65 |
| N2 | log TAR | external no-slowing (ON-100) | 10 | 12.57 | 7.37–18.02 |
| N2 | log TAR | external no-slowing (ON-100) | 25 | 27.07 | 18.2–35.95 |
| N2 | log TAR | external no-slowing (ON-100) | 50 | 47.9 | 36.06–58.61 |
| N2 | log TAR | external no-slowing (ON-100) | 75 | 76.17 | 64.37–85.32 |
| N2 | log TAR | external no-slowing (ON-100) | 90 | 89.34 | 80.38–95.85 |
| N2 | log TAR | external no-slowing (ON-100) | 97 | 97.84 | 94.24–99.66 |
| N2 | log DAR | internal held-out normals | 3 | 3.27 | 2.52–4.13 |
| N2 | log DAR | internal held-out normals | 10 | 9.44 | 8.15–10.79 |
| N2 | log DAR | internal held-out normals | 25 | 22.9 | 20.81–24.82 |
| N2 | log DAR | internal held-out normals | 50 | 47.96 | 45.41–50.25 |
| N2 | log DAR | internal held-out normals | 75 | 74.42 | 72.13–76.6 |
| N2 | log DAR | internal held-out normals | 90 | 89.2 | 87.64–90.58 |
| N2 | log DAR | internal held-out normals | 97 | 95.92 | 95.05–96.77 |
| N2 | log DAR | external no-slowing (ON-100) | 3 | 8.38 | 4.49–13.12 |
| N2 | log DAR | external no-slowing (ON-100) | 10 | 17.37 | 10.82–25.4 |
| N2 | log DAR | external no-slowing (ON-100) | 25 | 31.26 | 22.97–40.17 |
| N2 | log DAR | external no-slowing (ON-100) | 50 | 57.72 | 48.37–67.14 |
| N2 | log DAR | external no-slowing (ON-100) | 75 | 82.63 | 73.37–90.39 |
| N2 | log DAR | external no-slowing (ON-100) | 90 | 91.26 | 82.74–97.63 |
| N2 | log DAR | external no-slowing (ON-100) | 97 | 95.57 | 89.0–99.67 |
| N3 | relative delta | internal held-out normals | 3 | 0.97 | 0.5–1.48 |
| N3 | relative delta | internal held-out normals | 10 | 4.86 | 3.57–6.82 |
| N3 | relative delta | internal held-out normals | 25 | 20.41 | 17.36–24.1 |
| N3 | relative delta | internal held-out normals | 50 | 56.74 | 52.44–61.22 |
| N3 | relative delta | internal held-out normals | 75 | 84.24 | 80.38–87.64 |
| N3 | relative delta | internal held-out normals | 90 | 94.56 | 91.6–96.83 |
| N3 | relative delta | internal held-out normals | 97 | 98.14 | 96.25–99.46 |
| N3 | log TAR | internal held-out normals | 3 | 6.2 | 4.62–8.32 |
| N3 | log TAR | internal held-out normals | 10 | 14.41 | 11.61–17.69 |
| N3 | log TAR | internal held-out normals | 25 | 28.72 | 24.67–33.18 |
| N3 | log TAR | internal held-out normals | 50 | 52.38 | 48.15–57.43 |
| N3 | log TAR | internal held-out normals | 75 | 76.92 | 72.88–81.01 |
| N3 | log TAR | internal held-out normals | 90 | 92.97 | 90.97–94.92 |
| N3 | log TAR | internal held-out normals | 97 | 98.22 | 97.21–98.93 |
| N3 | log DAR | internal held-out normals | 3 | 3.45 | 2.31–4.53 |
| N3 | log DAR | internal held-out normals | 10 | 12.1 | 9.76–14.34 |
| N3 | log DAR | internal held-out normals | 25 | 30.46 | 26.56–34.41 |
| N3 | log DAR | internal held-out normals | 50 | 56.7 | 51.57–61.12 |
| N3 | log DAR | internal held-out normals | 75 | 80.27 | 76.53–83.26 |
| N3 | log DAR | internal held-out normals | 90 | 94.35 | 92.67–95.93 |
| N3 | log DAR | internal held-out normals | 97 | 98.88 | 98.22–99.4 |
| REM | relative delta | internal held-out normals | 3 | 2.76 | 2.25–3.4 |
| REM | relative delta | internal held-out normals | 10 | 9.13 | 8.1–10.38 |
| REM | relative delta | internal held-out normals | 25 | 23.02 | 21.03–25.14 |
| REM | relative delta | internal held-out normals | 50 | 46.04 | 43.6–48.87 |
| REM | relative delta | internal held-out normals | 75 | 72.53 | 70.33–74.8 |
| REM | relative delta | internal held-out normals | 90 | 89.27 | 87.77–90.75 |
| REM | relative delta | internal held-out normals | 97 | 97.09 | 96.44–97.72 |
| REM | relative delta | external no-slowing (ON-100) | 3 | 5.07 | 1.28–8.52 |
| REM | relative delta | external no-slowing (ON-100) | 10 | 15.21 | 9.72–20.37 |
| REM | relative delta | external no-slowing (ON-100) | 25 | 32.66 | 22.41–41.24 |
| REM | relative delta | external no-slowing (ON-100) | 50 | 57.2 | 46.14–67.84 |
| REM | relative delta | external no-slowing (ON-100) | 75 | 78.7 | 70.32–86.32 |
| REM | relative delta | external no-slowing (ON-100) | 90 | 90.87 | 85.04–95.0 |
| REM | relative delta | external no-slowing (ON-100) | 97 | 98.38 | 96.56–99.76 |
| REM | log TAR | internal held-out normals | 3 | 2.84 | 2.34–3.52 |
| REM | log TAR | internal held-out normals | 10 | 9.7 | 8.44–11.07 |
| REM | log TAR | internal held-out normals | 25 | 23.92 | 22.04–26.15 |
| REM | log TAR | internal held-out normals | 50 | 46.62 | 43.68–49.32 |
| REM | log TAR | internal held-out normals | 75 | 73.88 | 70.94–76.54 |
| REM | log TAR | internal held-out normals | 90 | 90.71 | 88.65–92.62 |
| REM | log TAR | internal held-out normals | 97 | 97.09 | 95.71–98.14 |
| REM | log TAR | external no-slowing (ON-100) | 3 | 2.84 | 0.21–6.17 |
| REM | log TAR | external no-slowing (ON-100) | 10 | 9.74 | 4.44–15.19 |
| REM | log TAR | external no-slowing (ON-100) | 25 | 23.33 | 15.62–32.12 |
| REM | log TAR | external no-slowing (ON-100) | 50 | 48.07 | 38.14–60.67 |
| REM | log TAR | external no-slowing (ON-100) | 75 | 71.6 | 62.6–81.7 |
| REM | log TAR | external no-slowing (ON-100) | 90 | 88.24 | 80.78–95.04 |
| REM | log TAR | external no-slowing (ON-100) | 97 | 96.55 | 92.77–98.9 |
| REM | log DAR | internal held-out normals | 3 | 3.07 | 2.47–3.78 |
| REM | log DAR | internal held-out normals | 10 | 9.5 | 8.26–10.81 |
| REM | log DAR | internal held-out normals | 25 | 23.15 | 21.11–25.34 |
| REM | log DAR | internal held-out normals | 50 | 46.65 | 44.15–48.96 |
| REM | log DAR | internal held-out normals | 75 | 72.11 | 69.67–74.51 |
| REM | log DAR | internal held-out normals | 90 | 89.15 | 87.32–90.85 |
| REM | log DAR | internal held-out normals | 97 | 96.72 | 95.96–97.43 |
| REM | log DAR | external no-slowing (ON-100) | 3 | 5.07 | 1.22–8.8 |
| REM | log DAR | external no-slowing (ON-100) | 10 | 18.05 | 9.74–26.93 |
| REM | log DAR | external no-slowing (ON-100) | 25 | 31.24 | 21.22–40.81 |
| REM | log DAR | external no-slowing (ON-100) | 50 | 51.32 | 41.28–60.72 |
| REM | log DAR | external no-slowing (ON-100) | 75 | 75.86 | 67.04–83.84 |
| REM | log DAR | external no-slowing (ON-100) | 90 | 91.08 | 84.54–95.55 |
| REM | log DAR | external no-slowing (ON-100) | 97 | 96.75 | 91.59–99.47 |
