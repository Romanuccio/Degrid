from astropy.io import fits

filename = 'processed.fits'
with fits.open(filename) as hdul:
    hdul.info()