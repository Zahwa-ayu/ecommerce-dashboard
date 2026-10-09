# E-Commerce Public Dataset Dashboard ✨

Proyek analisis data E-Commerce Public Dataset (Olist) periode Januari 2017 – Agustus 2018 (pesanan `delivered`),
disajikan dalam dashboard interaktif Streamlit.

## Struktur Direktori
```
submission
├───dashboard
| ├───main_data.csv
| └───dashboard.py
├───data
| ├───customers_dataset.csv
| ├───geolocation_dataset.csv
| ├───order_items_dataset.csv
| ├───order_payments_dataset.csv
| ├───order_reviews_dataset.csv
| ├───orders_dataset.csv
| ├───product_category_name_translation.csv
| ├───products_dataset.csv
| └───sellers_dataset.csv
├───notebook.ipynb
├───README.md
├───requirements.txt
└───url.txt
```

## Setup Environment - Anaconda
```
conda create --name main-ds python=3.9
conda activate main-ds
pip install -r requirements.txt
```

## Setup Environment - Shell/Terminal
```
mkdir proyek_analisis_data
cd proyek_analisis_data
pipenv install
pipenv shell
pip install -r requirements.txt
```

## Run streamlit app
```
streamlit run dashboard/dashboard.py
```
Jalankan perintah dari folder utama `submission`. Dashboard akan terbuka di http://localhost:8501.
