from astropy.io import fits
from scipy.io import loadmat
import numpy as np
import matplotlib.pyplot as plt


def median_filter(data, r, R, m, n):
    f = np.empty_like(data)
    k = 0

    while True:
        for i in range(m):
            for j in range(n):
                # edge cases
                if i < r:
                    i_start = 0
                    i_end = i + r + 1
                elif i >= m - r:
                    i_start = i - r
                    i_end = m
                else:
                    i_start = i - r
                    i_end = i + r + 1

                if j < r:
                    j_start = 0
                    j_end = j + r + 1
                elif j >= n - r:
                    j_start = j - r
                    j_end = n
                else:
                    j_start = j - r
                    j_end = j + r + 1

                # median
                filter_submatrix = data[i_start:i_end, j_start:j_end]
                med = np.median(filter_submatrix)

                # R condition
                if data[i, j] / med > R:
                    f[i, j] = med
                    k += 1
                else:
                    f[i, j] = data[i, j]

        cond = k / m / n * 100

        if cond < 0.5:
            return f
        elif cond > 1:
            R += 0.01
            k = 0
        else:
            R += 0.005
            k = 0


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
    for xpower in range(order+1):
        for ypower in range(order - xpower+1):
            coeffs[column] = (
                coeffs[column] * scalex**xpower * scaley**ypower / scalez
            )
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
    for xpower in range(order+1):
        for ypower in range(order - xpower+1):
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

# #filename = "28031999_195.fits"
# r = 2
# R = 1.07
# # median filter parameters
# gamma = 1.7
# # gamma correction parameter
# r1 = 10
# r2 = 15
# t = 1.0
# # frequency filter parameters

def process_image_and_save(filename, r, R, gamma, r1, r2, t):
    # TODO pozor na data v souboru + novy obrazek je 1020x1020
    processed_image = process_image(filename, r, R, gamma, r1, r2, t)
    hdu = fits.PrimaryHDU(processed_image)
    hdu.writeto(filename + "_processed.fits")

def process_image(filename, r, R, gamma, r1, r2, t):
    """Reads and processes an image."""
    with fits.open(filename) as hdul:
        data = hdul[0].data

        # select subset of data
        data = data[2:1022, 2:1022]
        m, n = data.shape
        f = median_filter(data, r, R, m, n)
        F = np.fft.fft2(f)
        F_shift = np.fft.fftshift(F)

        A_shift = np.abs(F_shift)

        # determine local maxima
        tmp = loadmat("P.mat")
        tmp = tmp["P"]
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

        # weight function
        H = A_shift_filtered / A_shift

        # weight function mirrorring
        for i in range(m):
            for j in range(n - i):
                H[m - i - 1, n - j - 1] = H[i, j]

        # Fourier spectrum filtering
        G_shift = F_shift * H

        # inverse Fourier transform
        G = np.fft.ifftshift(G_shift)
        g = np.fft.ifft2(G)
        # g = rescale(np.real(g))
        g = rescale(np.abs(g))
        # gamma correction
        g = gamma_correction(g, gamma)

        return g
        # Visualization
        # subplot(1,2,1), imshow(f), title("Původní snímek")
        # subplot(1,2,2), imshow(g), title("Snímek po odstranění mřížky metodou FFPS")
        # f = gamma_correction(f, gamma)
        # g = gamma_correction(g, gamma)
        # fig, (ax1, ax2) = plt.subplots(1, 2)
        # ax1.imshow(f, cmap="gray")
        # ax2.imshow(g, cmap="gray")
        # plt.show()
        # input()
