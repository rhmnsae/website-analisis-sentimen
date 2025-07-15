# IndoBERT Sentiment Analysis Model

Proyek ini menggunakan model **IndoBERT** untuk melakukan analisis sentimen pada data teks berbahasa Indonesia, khususnya untuk analisis opini publik di media sosial.

## 📄 Deskripsi
Model IndoBERT ini dapat digunakan untuk berbagai keperluan pemrosesan bahasa alami (NLP) seperti:
- Analisis Sentimen
- Klasifikasi Teks
- Pemahaman Teks Bahasa Indonesia

Model ini dilatih menggunakan dataset bahasa Indonesia dan cocok untuk penelitian maupun pengembangan sistem berbasis bahasa Indonesia.

---

## 📥 Download Model IndoBERT
Anda dapat mengunduh model IndoBERT yang digunakan dalam proyek ini melalui tautan berikut:

➡️ [Download IndoBERT (Google Drive)](https://drive.google.com/drive/folders/1YC3_2SEF4XJIwLGFkDqzTha-9SVs5QGw)
➡️ [Hunggingface)](https://huggingface.co/rhmnsae/indobert_saepl)

---

## 🚀 Cara Penggunaan

Contoh kode sederhana untuk memuat model ini:

```python
from transformers import AutoTokenizer, AutoModel

tokenizer = AutoTokenizer.from_pretrained("indobert-model-directory/")
model = AutoModel.from_pretrained("indobert-model-directory/")
