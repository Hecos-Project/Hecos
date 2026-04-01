# Python Environment Setup

### 1. Create a Virtual Environment (Optional but recommended)
```bash
python -m venv venv
```

### 2. Activate the Environment
- **Windows:**
  ```bash
  venv\Scripts\activate
  ```
- **Linux/macOS:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: `psutil` is required for the Single-Instance locking mechanism introduced in v0.9.9.*

### 4. Optional: Development Dependencies
```bash
pip install -r requirements.txt --extra-index-url https://pypi.org/simple
```
