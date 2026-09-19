# Physical test record — pending

Task 13 requires a real print, measurement and assembly. No physical result
has been inferred from the renderer, PDF validation or 3D preview.

## Choose the correct sample

The designated test target is the **184.62 mm old ball**, measured at 580 mm
equatorial circumference. Use `config/test-print-184-62mm-high-density.yaml`.
The regenerated [full test PDF](output/equator-join/test-print-184-62mm-ocean/leipzig-globe-print.pdf)
has one calibration sheet and eight gore pages at 300 PPI / high label density,
using ocean and the current GitHub Pages map settings. Both halves end exactly
at the equator, with no vertical overlap.
The tracked checkpoint 07 sample is historical and still has 10 mm page overlap;
use the regenerated PDF for the current assembly workflow.

The final sphere remains **215 mm diameter**; use the
[production PDF](output/equator-join/production-215mm-ocean/leipzig-globe-print.pdf),
built with `config/production-215mm-ocean.yaml`, for final printing.
The historical checkpoint 05 sample is 215 mm and has per-page rulers; checkpoint
04 samples are 300 mm. Do not use those PDFs to judge the smaller test ball's fit.

Measure the sphere's equatorial circumference in millimetres. Diameter is
circumference divided by π. Set `globe.diameter_mm` to the measured diameter
and regenerate the build if necessary; do not adapt an old PDF with printer
scaling. Keep its Build Report and configuration with these observations.

## Print and assemble

1. Print page 1 and the needed gore pages at **100% / actual size**, with fitting
   disabled in both the PDF viewer and printer driver. Use matching A4 paper.
2. Measure the calibration square between line centres **horizontally and
   vertically** before cutting: each must be 100 mm. Correct the settings if
   either measurement is wrong. Keep printer, paper and settings unchanged for
   all gore pages, including if sent as a separate job. Repeat calibration after
   changing them. A passing square checks scaling; it does not establish paper
   stability, page registration or physical fit.
3. Trim the straight equator edges along the line between the side registration
   crosses: the bottom edge of the upper tile and top edge of the lower tile.
   Place these edges together at the sphere's equator, with no vertical overlap.
   Adjacent gores retain their separate 2 mm side overlap at the equator.
4. Cut the solid gore outlines. The dashed edge is the nominal seam under
   the next gore. Check alignment across both page joins and adjacent gores.
5. Trial-fit the sample on the measured sphere. Record dry fit first, then
   any changes after applying and drying the chosen adhesive.

## Observations to fill in

| Item | Observed value or result |
|---|---|
| Date and tester | Pending |
| Build commit, configuration and report | Pending |
| Sphere equatorial circumference / calculated diameter | Pending |
| Sphere shape deviations or surface constraints | Pending |
| Printer and print-dialog settings | Pending |
| Paper type, thickness and grain direction if known | Pending |
| Calibration square width and height | Pending |
| Page join alignment and any clipping | Pending |
| Dry fit: equator, mid-latitudes and pole tips | Pending |
| Gore overlap: coverage, gaps or excessive bulk | Pending |
| Map continuity at gore seams | Pending |
| Label and fine-road legibility | Pending |
| Adhesive and application method | Pending |
| Fit/alignment after drying; paper stretch or shrinkage | Pending |
| Photos, including ruler and close-up seams | Pending |
| Required corrections or explicit acceptance | Pending |

Only after these observations exist should Task 13 be marked complete, with
any required corrections recorded as follow-up issues. A mathematically
correct sinusoidal projection does not establish how a specific paper and
adhesive will fit a physical sphere.
