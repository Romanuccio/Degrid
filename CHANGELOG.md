# Changelog

## Unreleased
- Fixed degridding to match the original MATLAB implementation; processed images differ slightly from 0.2.0 and the grid is suppressed noticeably better:
  - grid peak positions from P.mat are now refined to the local maximum within 10 px (the search never ran) and read as 1-based MATLAB indices
  - the weight function is mirrored through the zero frequency correctly (it was one pixel off), so the filtered image is real
- Degrid output (`*_processed.fits`) now keeps the original FITS header (WCS, observation metadata), with CRPIX shifted for the crop
- Fixed the application closing when r was changed (e.g. r = 3), when gamma was 0 and on any processing error; errors are now shown in a dialog
- Invalid (red) parameters block processing instead of being silently ignored
- Median filter is much faster (identical output)

## 0.2.0 - 2026-11-22
- Added noise-only mode
- Processing settings are now stored in the FITS header (DGVER keyword, framed COMMENT block and HISTORY entry)
- Median filter is skipped when n = 0; added parameter input for n
- Added Nathalia Alzate as an author

## 0.1.0 - 2026-03-27
- First public release of Degrid
- PyQt6 GUI for loading, previewing, and processing FITS files
- Adjustable processing parameters
- Export of processed images