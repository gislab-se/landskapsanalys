# Bornholm LABLAB PDF bright full-area class raster

- Source GIS PDF: `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Bornholm/PDF GIS/Landskapstyper Bornholm.pdf`
- Descriptive report PDF: `C:/gislab/landskapsanalys/data/Landskapstyper Bornholm.pdf`
- Output folder: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe`
- PDF CRS: `3006`, SWEREF99 TM
- Raster size: 1754 x 2481
- Max RGB distance: 0.18
- Brightness filter: 0.12 to 0.98
- Modal fill applied: FALSE
- Classified pixel share after mask/fill: 0.3684
- Landmask note: Applied landmask with 250 m buffer: C:/tmp/landskapsanalys-v2-multiregion/docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_landmask_wgs84.geojson

## Status

This is a helper product for QGIS review, not a final landscape-type layer.
Bornholm's GIS PDF uses transparent landscape fills over orthophoto/imagery, so colour classification is inherently approximate.
Use the bright RGB raster and per-type masks to support manual extraction and visual correction in QGIS.

## Best file for QGIS colour picking

- `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_bright_rgb.tif`

## Other outputs

- Clean class raster: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_clean_class.tif`
- Raw class raster: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_raw_class.tif`
- Unknown flag raster: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_unknown_flag.tif`
- RGB distance raster: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_rgb_distance.tif`
- Polygon GeoPackage: `not written by default; run with WRITE_FULL_POLYGONS=1`
- Palette CSV: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_palette.csv`
- Source colour sample CSV: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_source_samples.csv`
- Summary CSV: `C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_summary.csv`

## Bright palette

 type_id                             type_name bright_hex
    LT01                 Klippigt kustlandskap    #1E5AF0
    LT02                  Sandigt kustlandskap    #18DCEB
    LT03 Jordbruksdominerat sprickdalslandskap    #F07818
    LT04         Skogsklätt sprickdalslandskap    #19D64A
    LT05          Slätt- och jordbrukslandskap    #F2DC10

## Summary

 type_id                             type_name bright_hex n_pixels
    LT01                 Klippigt kustlandskap    #1E5AF0    47494
    LT02                  Sandigt kustlandskap    #18DCEB   343299
    LT03 Jordbruksdominerat sprickdalslandskap    #F07818   666649
    LT04         Skogsklätt sprickdalslandskap    #19D64A   219469
    LT05          Slätt- och jordbrukslandskap    #F2DC10   326158
 approx_area_km2
        18.02054
       130.25714
       252.94507
        83.27261
       123.75337
