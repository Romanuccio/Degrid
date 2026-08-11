from astropy.io import fits
from scipy.io import loadmat
from PyQt6.QtCore import QThread
import numpy as np
from scipy import ndimage
from pathlib import Path

epsilon = 1e-9

class ImageProcessorThread(QThread):
    def __init__(self, r, R, r1, r2, t, filename):
        super().__init__()
        self.r = r
        self.R = R
        self.r1 = r1
        self.r2 = r2
        self.t = t
        self.filename = filename
        self.saved_filepath = ''

    def set_file(self, filename):
        self.filename = filename

    def run(self):
        self.saved_filepath = process_image_and_save(
            self.filename, self.r, self.R, self.r1, self.r2, self.t
        )



def median_filter(data, r, R_init, max_iter=50, tol_change=0.5):
    """
    Iteratively adjusts R until the percentage of changed pixels stabilizes.
    Optimized using vectorization.
    """
    data = data.astype(np.float64)
    m, n = data.shape
    total_pixels = m * n
    
    R = R_init
    prev_change_pct = 100.0
    
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
        
        # 5. Convergence Logic
        if abs(change_pct - prev_change_pct) < tol_change:
            return f
            
        # Adjust R based on logic similar to your original code
        if change_pct < 0.5:
            # Too few changes? Maybe R is too high, or we are done.
            return f
        elif change_pct > 1.0:
            # Too many changes? Increase R to make condition stricter.
            R += 0.01
        else:
            # In between? Slight increase.
            R += 0.005
            
        prev_change_pct = change_pct

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


def process_image_and_save(filename, r, R, r1, r2, t):
    processed_image = process_image(filename, r, R, r1, r2, t)
    hdu = fits.PrimaryHDU(processed_image)
    # make folder for processed files if it does not exist
    directory_path = Path.joinpath(Path.cwd(), Path("ProcessedImages"))
    directory_path.mkdir(exist_ok=True)
    filename = Path(filename).stem
    
    save_filepath = directory_path.joinpath(filename + "_processed.fits")
    hdu.writeto(save_filepath, overwrite=True)
    return save_filepath


def process_image(filename, r, R, r1, r2, t):
    """Reads and processes an image."""
    with fits.open(filename) as hdul:
        data = hdul[0].data

        # select subset of data
        data = data[2:1022, 2:1022]
        
        f = median_filter(data, r=r, R_init=R)
        F = np.fft.fft2(f)
        F_shift = np.fft.fftshift(F)

        A_shift = np.abs(F_shift)

        # determine local maxima
        tmp = loadmat("P.mat")["P"].astype(np.int32)
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
