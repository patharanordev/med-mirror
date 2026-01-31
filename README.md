# MedMirror Edge Setup

This project is configured to run **Skin Segmentation** and **MedGemma** (optional) on your local edge device (RTX 4080) using Docker Compose.

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have the **NVIDIA Container Toolkit** installed so Docker can access your RTX 4080.
If not, install it:
```bash
# Windows (WSL2) or Linux
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 2. Run the App
Navigate to this directory in your terminal and run:

```bash
docker-compose up --build
```
*   This will download the base images, install PyTorch/Transformers, and start the services.
*   The first run will take time (GBs of downloads).

### 3. Usage
*   **Web Interface**: Open [http://localhost:3000](http://localhost:3000) in your browser.
    *   Click "Start Camera".
    *   Click "Analyze Skin" (or toggle "Auto-Segment Stream").
    *   The backend (port 8000) will download the `segformer` model on the first request. The first request might be slow.
*   **API Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs) to see the backend API.

## 🏗 Architecture

*   **Frontend**: Nginx serving a high-performance HTML5/JS app. Captures video locally to save bandwidth.
*   **Segmentation Service**: Python FastAPI using `transformers` and `segformer_b2_clothes`.
    *   Running on GPU (RTX 4080).
    *   Returns a transparent PNG mask of the detected skin.
*   **MedGemma Service** (Optional):
    *   To enable MedGemma, uncomment the `medgemma` section in `docker-compose.yml`.
    *   You will need to provide your Hugging Face or Kaggle token to download the weights.

## 🔧 Troubleshooting
*   **"Model not loaded"**: Check the docker logs (`docker-compose logs -f segmentation`). It might still be downloading the model.
*   **Camera not working**: Ensure your browser allows camera access to `localhost:3000`. Browsers often block non-HTTPS camera access unless it's localhost.
