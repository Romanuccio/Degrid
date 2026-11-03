from astropy.io import fits
from scipy.io import loadmat
from PyQt6.QtCore import QThread
import numpy as np
from scipy import ndimage
from pathlib import Path
import re

epsilon = 1e-9


def _p_mat_path():
    """P.mat next to the working directory, else the one bundled by PyInstaller."""
    import sys
    local = Path.cwd() / "P.mat"
    if local.exists():
        return local
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "P.mat"

def _degrid_version():
    try:
        from importlib.metadata import version
        return version("degrid")
    except Exception:
        return "unknown"


_DG_RULE = "-" * 60
_DG_TITLE = "Degrid processing settings (github.com/Romanuccio/Degrid)"
_DG_PARAMS = {
    "r": ("DGMEDR", "Median filter: half-size r (window 2r+1 px)"),
    "R": ("DGMEDR0", "Median filter: initial ratio threshold R"),
    "n": ("DGNOISE", "Median filter: stop below n % replaced (0=off)"),
    "r1": ("DGR1", "Frequency filter: radius r1"),
    "r2": ("DGR2", "Frequency filter: radius r2"),
    "t": ("DGT", "Frequency filter: parameter t"),
}


def add_settings_to_header(header, mode, source, **params):
    """Append a block with the processing settings to the FITS header.

    The block (framed by COMMENT rules) holds DG* keywords and is followed by a
    one-line HISTORY summary. An older Degrid block, e.g. from re-processing a
    Degrid output, is replaced rather than duplicated.
    """
    from datetime import datetime, timezone

    # drop a previous Degrid block
    for key in [k for k in header.keys() if k.startswith("DG")]:
        header.remove(key, ignore_missing=True, remove_all=True)
    if "COMMENT" in header:
        old = [c for c in header["COMMENT"] if c not in (_DG_RULE, _DG_TITLE)]
        header.remove("COMMENT", remove_all=True)
        for c in old:
            header.add_comment(c)

    version = _degrid_version()
    cards = [
        ("DGVER", version, "Degrid version"),
        ("DGDATE", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
         "Processing date (UTC)"),
        ("DGMODE", mode, "Mode: degrid | noise_only"),
        ("DGSRC", Path(source).name, "Input file"),
    ]
    cards += [(_DG_PARAMS[k][0], v, _DG_PARAMS[k][1]) for k, v in params.items()]

    header.append(("COMMENT", _DG_RULE), end=True)
    header.append(("COMMENT", _DG_TITLE), end=True)
    header.append(("COMMENT", _DG_RULE), end=True)
    for card in cards:
        header.append(card, end=True)
    header.append(("COMMENT", _DG_RULE), end=True)

    settings = ", ".join(f"{k}={v}" for k, v in params.items())
    header.add_history(f"Degrid {version} ({mode}): {settings}")
    return header


class ImageProcessorThread(QThread):
    def __init__(self, r, R, r1, r2, t, filename, n, noise_only=False):
        super().__init__()
        self.noise_only = noise_only
        self.r = r
        self.R = R
        self.r1 = r1
        self.r2 = r2
        self.t = t
        self.n = n
        self.filename = filename
        self.saved_filepath = ''

    def set_file(self, filename):
        self.filename = filename

    def run(self):
        if self.noise_only:
            self.saved_filepath = noise_only_and_save(
                self.filename, self.r, self.R, self.n
            )
            return
        self.saved_filepath = process_image_and_save(
            self.filename, self.r, self.R, self.r1, self.r2, self.t, self.n
        )



def median_filter(data, r, R_init, n, max_iter=100):
    """
    Iteratively adjusts R until the percentage of changed pixels stabilizes.
    Optimized using vectorization.
    """
    data = data.astype(np.float64)
    W, H = data.shape
    total_pixels = W * H
    
    R = R_init
    # prev_change_pct = 100.0
    
    for _ in range(max_iter):
        # 1. Calculate Median (Vectorized)
        window_size = 2 * r + 1
        med_filtered = ndimage.median_filter(data, size=window_size, mode='reflect')
        
        # 2. Calculate Mask
        ratio = data / (med_filtered + epsilon)
        mask = ratio > R
        
        # 3. Apply Update
        f = data.copy()
        f[mask] = med_filtered[mask]
        
        # 4. Calculate Change Percentage
        num_changed = np.count_nonzero(mask)
        change_pct = (num_changed / total_pixels) * 100
            
        # Adjust R based on logic similar to your original code
        if change_pct < n:
            # Too few changes? Maybe R is too high, or we are done.
            return f
        elif change_pct > 1.0:
            # Too many changes? Increase R to make condition stricter.
            R += 0.01
        else:
            # In between? Slight increase.
            R += 0.005
            
        # prev_change_pct = change_pct

    return f


def rescale(f):
    L_min = np.min(f)
    L_max = np.max(f)
    g = (f - L_min) / (L_max - L_min)
    return g


def gamma_correction(f, gamma):
    f = rescale(f)
    g = f ** (1 / gamma)
    return g


def fit2dPolySVD(x, y, z, order):
    # source: WHITEHEAD, R. 2D polynomial fitting with SVD. MATLAB Central File Exchange [online]. 2011 [cit. 2023-02-28].
    # Dostupné z: https://www.mathworks.com/matlabcentral/fileexchange/31636-2d-polynomial-fitting-with-svd
    # Fit a polynomial f(x,y) so that it provides a best fit
    # to the data z.
    # Uses SVD which is robust even if the data is degenerate.  Will always
    # produce a least-squares best fit to the data even if the data is
    # overspecified or underspecified.
    # x, y, z are column vectors specifying the points to be fitted.
    # The three vectors must be the same length.
    # Order is the order of the polynomial to fit.
    # Coeffs returns the coefficients of the polynomial.  These are in
    # increasing power of y for each increasing power of x, e.g. for order 2:
    # zbar = coeffs(1) + coeffs(2).*y + coeffs(3).*y^2 + coeffs(4).*x +
    # coeffs(5).*x.*y + coeffs(6).*x^2
    # Use eval2dPoly to evaluate the polynomial.
    if x.ndim > 1 or y.ndim > 1 or z.ndim > 1:
        if np.min(x.shape) > 1 or np.min(y.shape) > 1 or np.min(z.shape) > 1:
            print("Inputs of fit2dPolySVD must be column vectors")
            return

    if len(x) != len(y) or len(z) != len(x):
        print("Inputs vectors of fit2dPolySVD must be the same length")
        return

    numVals = len(x)

    # scale to prevent precision problems
    scalex = 1.0 / max(abs(x))
    scaley = 1.0 / max(abs(y))
    scalez = 1.0 / max(abs(z))
    xs = x * scalex
    ys = y * scaley
    zs = z * scalez

    # number of combinations of coefficients in resulting polynomial
    numCoeffs = (order + 2) * (order + 1) / 2
    numCoeffs = int(numCoeffs)

    # Form array to process with SVD
    A = np.zeros((numVals, numCoeffs))

    column = 0
    for xpower in range(order + 1):
        for ypower in range(order - xpower + 1):
            A[:, column] = xs**xpower * ys**ypower
            column += 1

    # Perform SVD
    [u, s, v] = np.linalg.svd(A)
    v = v.conj().T
    # pseudo-inverse of diagonal matrix s
    eps = np.finfo(np.double).eps
    sigma = eps ** (1 / order)  # minimum value considered non-zero
    ### qqs = np.diag(s)
    qqs = s
    qqs[abs(qqs) >= sigma] = 1.0 / qqs[abs(qqs) >= sigma]
    qqs[abs(qqs) < sigma] = 0
    qqs = np.diag(qqs)
    if numVals > numCoeffs:
        # add empty rows
        qqs = np.append(qqs, np.zeros((numVals - numCoeffs, len(qqs))), axis=0)

    # calculate solution
    coeffs = np.dot(np.dot(v, qqs.transpose()), np.dot(u, zs))

    # scale the coefficients so they are correct for the unscaled data
    column = 0
    for xpower in range(order + 1):
        for ypower in range(order - xpower + 1):
            coeffs[column] = coeffs[column] * scalex**xpower * scaley**ypower / scalez
            column += 1

    return coeffs


def eval2dPoly(x, y, coeffs):
    # source: WHITEHEAD, R. 2D polynomial fitting with SVD. MATLAB Central File Exchange [online]. 2011 [cit. 2023-02-28]. Dostupné z: https://www.mathworks.com/matlabcentral/fileexchange/31636-2d-polynomial-fitting-with-svd
    # Given the coefficients of a polynomial as returned by fit2dPolySVD,
    # calculates the values z for input values (x,y).
    # x, y are column vectors specifying the points to be calculated.
    # The vectors must be the same length.
    # Coeffs is the coefficients array returned by fit2dPolySVD.

    if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
        if x.ndim > 1 or y.ndim > 1:
            if np.min(x.shape) > 1 or np.min(y.shape) > 1:
                print("Inputs of fit2dPolySVD must be column vectors")
                return

        if len(x) != len(y):
            print("Inputs vectors of fit2dPolySVD must be the same length")
            return

        numVals = len(x)

    numVals = 1
    order = int(0.5 * (np.sqrt(8 * len(coeffs) + 1) - 3))

    zbar = np.zeros(numVals)
    column = 0
    for xpower in range(order + 1):
        for ypower in range(order - xpower + 1):
            zbar += coeffs[column] * x**xpower * y**ypower
            column += 1

    return zbar


def frequency_filter(A_shift, P, r1, r2, t):
    [m, n] = A_shift.shape
    A_shift_filtered = np.copy(A_shift)
    polynomial_order = 2

    for i in range(P.shape[0]):
        sx = P[i, 0]
        sy = P[i, 1]
        x = y = z = xx = yy = np.empty((0, 1), int)
        mean = 0
        p = 0

        for j in range(m):
            for k in range(n):
                if (j - sx) ** 2 + (k - sy) ** 2 <= r1**2:
                    mean += A_shift[j, k]
                    p += 1
                    x = np.append(x, j)
                    y = np.append(y, k)
                    z = np.append(z, A_shift[j, k])
        mean /= p

        # thresholding
        ## positions xx yy are replaced
        ## x y z are used for the fit
        for j in range(m):
            for k in range(n):
                if (j - sx) ** 2 + (k - sy) ** 2 <= r1**2 and A_shift[j, k] >= t * mean:
                    xx = np.append(xx, j)
                    yy = np.append(yy, k)
                elif (j - sx) ** 2 + (k - sy) ** 2 <= r2**2:
                    x = np.append(x, j)
                    y = np.append(y, k)
                    z = np.append(z, A_shift[j, k])

        # neighbourhood approximation
        f = fit2dPolySVD(x, y, z, polynomial_order)
        # calculate amplitudes
        for j in range(len(xx)):
            A_shift_filtered[xx[j], yy[j]] = eval2dPoly(xx[j], yy[j], f)[0]

    return A_shift_filtered


def remove_impulse_noise(data, r, R, n, crop=True):
    """Impulse noise removal only (no degridding, no rescaling).

    Uses exactly the same steps as the beginning of `process_image`: crop of the
    2 edge rows/columns (only for 1024x1024 input) and `median_filter`.
    Output is float64 in the original intensity units.
    """
    if crop and data.shape == (1024, 1024):
        data = data[2:1022, 2:1022]
    data = data.astype(np.float64)
    if n != 0.:
        return median_filter(data, r=r, R_init=R, n=n)
    return data


def noise_only_and_save(filename, r, R, n):
    with fits.open(filename) as hdul:
        data = hdul[0].data
        header = hdul[0].header.copy()

    cropped = data.shape == (1024, 1024)  # remove_impulse_noise crops only these
    processed_image = remove_impulse_noise(data, r, R, n)

    if cropped:
        # the crop drops 2 pixels at the start of each axis, so the reference
        # pixel (primary and any alternate WCS: CRPIX1, CRPIX1A, ...) moves by 2
        for key in list(header.keys()):
            if re.fullmatch(r"CRPIX[12][A-Z]?", key):
                header[key] = header[key] - 2

    # drop keywords describing the original data layout; astropy sets them anew
    for key in ("BSCALE", "BZERO", "BLANK", "DATAMIN", "DATAMAX"):
        header.remove(key, ignore_missing=True, remove_all=True)
    add_settings_to_header(header, "noise_only", filename, r=r, R=R, n=n)
    if cropped:
        header.add_history("Degrid: edges cropped 2:1022 (CRPIX shifted by -2), grid kept")
    else:
        header.add_history("Degrid: no crop, grid kept")
    hdu = fits.PrimaryHDU(processed_image, header=header)

    directory_path = Path.joinpath(Path.cwd(), Path("ProcessedImages"))
    directory_path.mkdir(exist_ok=True)
    save_filepath = directory_path.joinpath(Path(filename).stem + "_noiseonly.fits")
    hdu.writeto(save_filepath, overwrite=True, output_verify="silentfix")
    return save_filepath


def process_image_and_save(filename, r, R, r1, r2, t, n):
    processed_image = process_image(filename, r, R, r1, r2, t, n)
    hdu = fits.PrimaryHDU(processed_image)
    add_settings_to_header(
        hdu.header, "degrid", filename, r=r, R=R, n=n, r1=r1, r2=r2, t=t
    )
    # make folder for processed files if it does not exist
    directory_path = Path.joinpath(Path.cwd(), Path("ProcessedImages"))
    directory_path.mkdir(exist_ok=True)
    filename = Path(filename).stem
    
    save_filepath = directory_path.joinpath(filename + "_processed.fits")
    hdu.writeto(save_filepath, overwrite=True)
    return save_filepath


def process_image(filename, r, R, r1, r2, t, n):
    """Reads and processes an image."""
    with fits.open(filename) as hdul:
        data = hdul[0].data

        # select subset of data
        data = data[2:1022, 2:1022]

        if (n != 0.):
            f = median_filter(data, r=r, R_init=R, n=n)
        else:
            f = data

        F = np.fft.fft2(f)
        F_shift = np.fft.fftshift(F)

        A_shift = np.abs(F_shift)

        # determine local maxima
        tmp = loadmat(_p_mat_path())["P"].astype(np.int32)
        P = np.empty((0, 2), int)
        for i in range(tmp.shape[0]):
            sx = tmp[i, 0]
            sy = tmp[i, 1]
            value = A_shift[sx, sy]
            a = sx
            b = sy
            for j in range(-10, 11):
                for k in range(-10, 11):
                    if (j - sx) ** 2 + (k - sy) ** 2 < 100 and A_shift[j, k] > value:
                        value = A_shift[j, k]
                        a = j
                        b = k
            P = np.append(P, np.array([[a, b]]), axis=0)

        # Filtering
        A_shift_filtered = frequency_filter(A_shift, P, r1, r2, t)

        # weight function (H_p in article)
        H = A_shift_filtered / (A_shift + epsilon)

        # weight function mirrorring
        N = H.shape[0]

        if N % 2 == 0:
            W = H + H[::-1, ::-1] - 1

            # ξ = 0 or η = 0
            W[0, :] = H[0, :]
            W[:, 0] = H[:, 0]

        else:
            W = H + H[::-1, ::-1] - 1

        # Fourier spectrum filtering
        G_shift = F_shift * W

        # inverse Fourier transform
        G = np.fft.ifftshift(G_shift)
        g = np.fft.ifft2(G)
        g = rescale(np.abs(g))

        return g
