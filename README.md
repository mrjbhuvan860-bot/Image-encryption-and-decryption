# 🔐 Image Encryption & Decryption

> A Django web application that protects images using AES-256 and Fernet encryption — with one-time-use keys and cloud-backed secure storage.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)](https://djangoproject.com)
[![Supabase](https://img.shields.io/badge/Supabase-Auth%20%26%20Storage-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyCryptodome](https://img.shields.io/badge/Crypto-PyCryptodome-orange)](https://pycryptodome.readthedocs.io)

---

## Overview

Image Encryption & Decryption is a full-stack Django web application that lets authenticated users encrypt and decrypt image files directly in their browser. It offers two distinct encryption modes: a **Default mode** that rewrites pixel data with AES-256-CBC ciphertext (producing a valid but visually randomized PNG), and a **Full mode** that encrypts the entire file as an opaque binary blob using Fernet (AES-128-CBC + HMAC-SHA256).

Encrypted files are stored in Supabase Storage; the cryptographic keys are **never stored server-side** — they are returned to the user immediately after encryption and consumed (and invalidated) on first use during decryption.

---

## Key Features

- **Two encryption modes** — AES-256-CBC pixel-level encryption (Default) and Fernet full-file encryption (Full).
- **One-time-use keys** — each key is cryptographically tied to a file ID; the key is permanently invalidated the moment decryption succeeds.
- **Zero server-side key storage** — keys exist only in the user's hands, never in a database.
- **Supabase integration** — Supabase Auth for user accounts and Supabase Storage as a private encrypted-file bucket.
- **Secure file handling** — UUID-based temporary filenames, strict MIME/extension validation, and automatic cleanup after processing.
- **Inline decrypted preview** — decrypted images are served as base64 data URLs so the plaintext file never touches the server's filesystem.
- **Authenticated access control** — all encryption/decryption routes are protected by a `supabase_login_required` decorator backed by session cookies.

---

## Tech Stack

| Layer            | Technology                              |
|------------------|-----------------------------------------|
| Web framework    | Django 5.1                              |
| Image processing | Pillow ≥ 10                             |
| Symmetric crypto | PyCryptodome ≥ 3.20 (AES-256-CBC)       |
| Authenticated encryption | `cryptography` ≥ 42 — Fernet   |
| Auth & Storage   | Supabase (Python client ≥ 2.0)          |
| Config           | python-dotenv ≥ 1.0                     |
| Database         | SQLite (sessions only — no user models) |
| Frontend         | Django Templates, vanilla CSS & JS      |

---

## Project Structure

```
Image-encryption-and-decryption/
├── manage.py                        # Django management entry point
├── requirements.txt                 # Python dependencies
├── db.sqlite3                       # SQLite DB (sessions only)
│
├── config/
│   ├── settings.py                  # Project settings (env-driven)
│   ├── urls.py                      # Root URL dispatcher
│   └── wsgi.py                      # WSGI entry point
│
├── apps/
│   ├── accounts/                    # Authentication (Supabase-backed)
│   │   ├── views.py                 # Signup, login, logout, profile
│   │   ├── forms.py                 # LoginForm, SignupForm
│   │   ├── decorators.py            # supabase_login_required
│   │   ├── supabase_client.py       # Supabase client factory
│   │   └── urls.py
│   │
│   ├── core/                        # Landing page & dashboard
│   │   ├── views.py
│   │   └── urls.py
│   │
│   └── crypto_tools/                # Encryption / decryption engine
│       ├── views.py                 # encrypt_view, decrypt_view
│       ├── forms.py                 # EncryptForm, DecryptForm
│       ├── urls.py
│       └── services/
│           ├── default_encryptor.py # AES-256-CBC pixel encryption
│           ├── default_decryptor.py # AES-256-CBC pixel decryption
│           ├── full_encryptor.py    # Fernet full-file encryption
│           ├── full_decryptor.py    # Fernet full-file decryption
│           ├── key_manager.py       # Key serialisation / deserialisation
│           ├── file_handler.py      # Upload validation & temp I/O
│           └── supabase_storage.py  # Bucket upload, signed URLs, deletion
│
├── templates/
│   ├── base.html
│   ├── accounts/                    # login.html, signup.html, profile.html
│   ├── core/                        # landing.html, dashboard.html
│   └── crypto_tools/                # encrypt.html, decrypt.html
│
├── static/
│   ├── css/main.css
│   └── js/app.js
│
└── test_crypto.py                   # Round-trip validation tests
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- A [Supabase](https://supabase.com) project with:
  - Email/password authentication enabled
  - A private storage bucket named `encrypted-files` (created automatically on first use)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/shadowwmonarch/Image-encryption-and-decryption.git
cd Image-encryption-and-decryption

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables (see below)
cp .env.example .env            # edit .env with your values

# 5. Apply database migrations (required for Django session framework)
python manage.py migrate

# 6. Collect static files (production only)
python manage.py collectstatic --noinput

# 7. Start the development server
python manage.py runserver
```

### Environment Variables

Create a `.env` file in the project root with the following keys:

```dotenv
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Upload limits
MAX_UPLOAD_SIZE_MB=10
```

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django cryptographic signing key — keep secret in production |
| `DJANGO_DEBUG` | Set to `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Public anon key (used for client-side auth) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (used server-side for storage operations) |
| `MAX_UPLOAD_SIZE_MB` | Maximum image upload size in megabytes (default: 10) |

---

## Usage

### Encrypt an image

1. Log in or create an account at `/accounts/signup/`.
2. Navigate to **Encrypt** (`/tools/encrypt/`).
3. Upload a `.png`, `.jpg`, `.jpeg`, or `.bmp` image (max 10 MB).
4. Choose an encryption mode:
   - **Default** — produces an encrypted PNG (pixel noise); suitable when you want to preview the "scrambled" image.
   - **Full Protection** — produces a binary `.enc` file; no image metadata is preserved.
5. Click **Encrypt**. A signed download URL and a one-time decryption key are displayed.
6. **Save the key immediately** — it cannot be recovered from the server.

### Decrypt an image

1. Navigate to **Decrypt** (`/tools/decrypt/`).
2. Upload the encrypted `.png` or `.enc` file you received.
3. Paste the decryption key into the key field.
4. Click **Decrypt**. The original image is displayed inline and available for download.
5. The key is **permanently invalidated** on successful decryption.

### Run the test suite

```bash
python test_crypto.py
```

The test script performs full round-trip validation for both encryption modes and the key manager:

```
============================================================
TEST: Key Manager                         ✓ ALL TESTS PASSED
TEST: Default Encryption Mode (AES-256-CBC)  ✓ ALL TESTS PASSED
TEST: Full Encryption Mode (Fernet)          ✓ ALL TESTS PASSED
============================================================
ALL TESTS PASSED ✓
```

---

## API Reference

There is no public REST API. The application exposes the following URL routes:

| Method | URL | Auth required | Description |
|--------|-----|:---:|-------------|
| `GET` | `/` | No | Public landing page |
| `GET` | `/dashboard/` | Yes | User dashboard |
| `GET / POST` | `/accounts/signup/` | No | Register a new account |
| `GET / POST` | `/accounts/login/` | No | Log in |
| `GET` | `/accounts/logout/` | Yes | Log out (clears session) |
| `GET` | `/accounts/profile/` | Yes | View account details |
| `GET / POST` | `/tools/encrypt/` | Yes | Upload & encrypt an image |
| `GET / POST` | `/tools/decrypt/` | Yes | Upload & decrypt a file |

### Service functions

| Module | Function | Description |
|--------|----------|-------------|
| `default_encryptor` | `encrypt_image(image_path)` | AES-256-CBC pixel encryption; uploads PNG to Supabase; returns signed URL + key string |
| `default_decryptor` | `decrypt_image(path, key_string)` | Reverses pixel encryption; returns image bytes |
| `full_encryptor` | `encrypt_file(file_path)` | Fernet full-file encryption; uploads `.enc` to Supabase; returns signed URL + key string |
| `full_decryptor` | `decrypt_file(path, key_string)` | Reverses Fernet encryption; returns original file bytes |
| `key_manager` | `serialize_key(data)` / `deserialize_key(s)` | Base64url JSON key serialisation |
| `key_manager` | `detect_mode(key_string)` | Returns `"default"` or `"full"` from a key string |

---

## Contributing

Contributions are welcome. Please follow the guidelines below.

### Branch naming

```
feature/<short-description>
fix/<short-description>
docs/<short-description>
refactor/<short-description>
```

### Workflow

```bash
# 1. Fork the repository and clone your fork
git clone https://github.com/<your-username>/Image-encryption-and-decryption.git

# 2. Create a feature branch from main
git checkout -b feature/your-feature-name

# 3. Make your changes; ensure existing tests still pass
python test_crypto.py

# 4. Commit with a clear message
git commit -m "feat: add support for GIF encryption"

# 5. Push and open a Pull Request against main
git push origin feature/your-feature-name
```

### Pull Request checklist

- [ ] `test_crypto.py` passes without errors.
- [ ] New behaviour is covered by an update to `test_crypto.py` where applicable.
- [ ] No secrets or credentials are committed.
- [ ] Code follows the existing style (docstrings, type hints where present).

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
