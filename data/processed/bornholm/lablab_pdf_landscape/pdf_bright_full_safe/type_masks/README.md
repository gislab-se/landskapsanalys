# Bornholm LABLAB bright type masks

These rasters are helper inputs for QGIS review/vectorization.
They are not final landscape-type data.

## How to use

1. Load one `*_rgb_mask.tif` at a time in QGIS.
2. Use the visible solid colour as a guide for extraction or manual tracing.
3. Compare against the original GIS PDF and descriptive report PDF.
4. Save reviewed polygon layers to a manual GeoPackage.
5. Run `script/bornholm/name_manual_vectorized_landscape_types.R` after the review table is filled.

The `*_binary_mask.tif` files are 1/NoData masks if QGIS Processing polygonize is easier than colour picking.

## Index

 type_id                             type_name bright_hex
    LT01                 Klippigt kustlandskap    #1E5AF0
    LT02                  Sandigt kustlandskap    #18DCEB
    LT03 Jordbruksdominerat sprickdalslandskap    #F07818
    LT04         Skogsklätt sprickdalslandskap    #19D64A
    LT05          Slätt- och jordbrukslandskap    #F2DC10
                                                                                                                                                      rgb_mask
 C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT01_rgb_mask.tif
 C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT02_rgb_mask.tif
 C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT03_rgb_mask.tif
 C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT04_rgb_mask.tif
 C:/tmp/landskapsanalys-v2-multiregion/data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT05_rgb_mask.tif
