# Degrid: a desktop application for processing images from SOHO EIT

[![DOI](https://zenodo.org/badge/700892229.svg)](https://doi.org/10.5281/zenodo.19253611) ![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-BSD--2--Clause-green)

**Degrid** is a pyQt6 desktop application for processing images from SOHO EIT. Input files are FITS files level 0. The application removes impulse noise and periodic noise (square/rectangular grid). This script was created as a part of article "Removal of the Mesh Grid in SOHO EIT Solar Images with a Notch Filter" in the Astrophysical Journal Supplement Series. It explains and derives the mathematical calculations contained therein.

---

## ✨ Features

* Load and visualize FITS images
* Image processing pipeline with adjustable parameters
* Save processed outputs to disk

---

## 📦 Requirements

* Python 3.10+
* PyQt6
* matplotlib
* numpy
* scipy
* astropy

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/Romanuccio/Degrid.git
cd Degrid
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install PyQt6 matplotlib numpy scipy astropy
```

---

## ▶️ Usage

Run the application:

```bash
python main.py
```

### Workflow

1. Load a FITS file
2. Adjust processing parameters in the GUI
3. Run the processing pipeline
4. View results in the interface
5. Save processed images

---

## 📁 Required Files

### `P.mat`

The file `P.mat` is required for the application to function correctly.

* It is included in the repository
* Do not remove or rename it
* It is used internally for processing

---

## 📂 Output

Processed images are saved to the configured output directory (see application settings).

---

## 📜 License

This project is licensed under the BSD-2-Clause License.
See the `LICENSE` file for details.

This project includes third-party code.
See `THIRD_PARTY_NOTICES.md` for attribution.

---

## 📖 Citation

If you use Degrid in your research, please cite:

> Byrtus, R., Druckmüllerová, H., Habbal, S., & Satýnek, D. (2026).  
> *Degrid (v0.1.0)*. Zenodo. https://doi.org/10.5281/zenodo.19253611

---

## 🔗 Repository

https://github.com/Romanuccio/Degrid

---

## 👤 Authors

Roman Byrtus, Hana Druckmüllerová, Shadia Habbal, Daniel Satýnek
