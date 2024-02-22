from astropy.io import fits
from scipy.io import loadmat
import numpy as np
import matplotlib.pyplot as plt# Visualization
from FFPS import rescale, gamma_correction

filename = "28031999_195.fits"
second_filename = "processed.fits"

with fits.open(filename) as hdul:
    data = hdul[0].data
    # data = gamma_correction(rescale(data), 1.7)
    # subplot(1,2,1), imshow(f), title("Původní snímek")
    # subplot(1,2,2), imshow(g), title("Snímek po odstranění mřížky metodou FFPS")
    fig, (ax1, ax2) = plt.subplots(1, 2)
    ax1.imshow(data, cmap="gray")
    with fits.open(second_filename) as hdul2:
        data2 = hdul2[0].data
        ax2.imshow(data2, cmap="gray")
    
    plt.show()