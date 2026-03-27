# Degrid

**Degrid** is a PyQt6 desktop application for processing and visualizing FITS (Flexible Image Transport System) images, designed for astronomy workflows.

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

If you use Degrid in your research, please cite it using the metadata in `CITATION.cff`.

---

## 🔗 Repository

https://github.com/Romanuccio/Degrid

---

## ⚠️ Notes

* This is the first public release (`v0.1.0`)
* The application is under active development
* Interface and features may change in future versions

---

## 👤 Authors

Roman Byrtus, Hana Druckmüllerová, Shadia Habbal, Daniel Satýnek
