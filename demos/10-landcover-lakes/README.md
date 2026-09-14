# Land cover, lake names and composite labels

Requested refinements to the previous live `b273fff` preview. The fixed Before
snapshot now contains that actual deployment's 46 verified assets (11.98 MB).
Only Current is rebuilt; the selector retains the camera and view settings.

The pale areas south of Grünau-Siedlung were largely mapped fields that the
renderer did not import. The sampled southwestern region contains 6.37 km² of
farmland, versus 0.66 km² of mapped industry, commerce and farmyards. The eastern
and northern samples also contain extensive agriculture. This is evidence from
the pinned September 1 OSM extract, not a claim that every blank patch is a field.
Leipzig's [official land-use dataset](https://opendata.leipzig.de/de/dataset/flachennutzung-jahreszahlen-kleinraumig)
also distinguishes agriculture from industry, woodland and recreation.

The new rendering adds mapped farmland, orchards/vineyards, scrub, commercial
and industrial land, farmyards, brownfield/construction sites and quarries.
Fields have a muted yellow-green fill and fine parcel boundaries. Unclassified
land keeps the paper colour. The same styling applies to surrounding terrain.

Nearby component names are omitted only after their complete composite name
has been placed. Both requested examples work, along with Anger-Crottendorf,
Reudnitz-Thonberg and Sellerhausen-Stünz: ten redundant labels disappear.
The match requires exact component names, place tags and proximity within 5 km.
Components remain eligible when a composite cannot fit.

Cospudener See, Zwenkauer See and Auensee receive dark blue names. Lake candidates
must be named standing-water polygons of at least five hectares within Leipzig.
Placement searches the visible water area and tries wrapping and vertical text,
while preserving natural glyph proportions and the 2 mm minimum font. Every
label footprint must fit inside the lake, outside islands, away from roads,
railways, other labels, seams and poles. Kulkwitzer See and the other omissions
remain documented in `source-evidence.json`; no safety margin was reduced.

`regional-comparison.jpg` compares seven fixed regions using final text
proportions and the preserved local build of the previous renderer. The
interactive Before snapshot uses the verified live bytes. `source-evidence.json`
records region bounds, land-cover areas,
source IDs, rendered lakes, and all lake/composite omissions. Percentages use
the municipal portion of each region; source categories can overlap. The map's
viewport and sampling are unchanged, and the high-density cap remains 80.

Reproduce the regional evidence with:

```powershell
uv run python scripts/save_landcover_checkpoint.py --before <previous-terrain-build> --after <current-terrain-build> --output demos/10-landcover-lakes
```

The isolated release passes 144 tests. All three styles validate, each with
12 exact A4 print pages, identical city artwork and gore geometry, preserved
city pixels, and continuous wraps/poles (`checkpoint.json`). Build times were
356.16 s terrain, 149.26 s ocean and 140.34 s fog. Context data remains bounded
at 87.67 MB. The complete two-version site is 24.01 MB, including 12.00 MB of
Current assets and 11.98 MB of Before assets (`release-check.json`).

Installed Edge passes the complete browser suite: all three styles and both
modes, Before/Current switching with camera/overlay preservation, failed-load
recovery, mouse controls, mobile layout, touch drag and pinch zoom
(`browser-check.json`, `browser-current.png`). In-app browser setup was unavailable.

Deployed-byte validation is recorded alongside this document when complete.
Physical printing and fit remain a human milestone.
