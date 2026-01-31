import io
import os
import torch
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
import uvicorn

app = FastAPI(title="Skin Segmentation Service")

# CORS (Allow frontend to communicate)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Model Configuration ---
# Check if a local path is provided via ENV, otherwise fallback to Hub ID
ENV_MODEL_PATH = os.getenv("MODEL_PATH")
HUB_MODEL_ID = "mattmdjaga/segformer_b2_clothes"

# Determine which path to load from
if ENV_MODEL_PATH and os.path.exists(ENV_MODEL_PATH) and os.listdir(ENV_MODEL_PATH):
    print(f"📂 Loading model from local volume: {ENV_MODEL_PATH}")
    MODEL_SOURCE = ENV_MODEL_PATH
else:
    print(f"☁️  Local model not found. Downloading from Hub: {HUB_MODEL_ID}")
    MODEL_SOURCE = HUB_MODEL_ID

if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

model = None
processor = None

try:
    processor = SegformerImageProcessor.from_pretrained(MODEL_SOURCE)
    model = SegformerForSemanticSegmentation.from_pretrained(MODEL_SOURCE).to(DEVICE)
    print(f"✅ Model loaded successfully on {DEVICE}")
except Exception as e:
    print(f"❌ Error loading model: {e}")

# Skin-related labels in the chosen model (11: Face, 12: Leg, 13: Leg, 14: Arm, 15: Arm)
SKIN_LABELS = [11, 12, 13, 14, 15] 

@app.get("/")
def health_check():
    status = "ready" if model else "failed"
    return {
        "status": status, 
        "device": DEVICE, 
        "source": MODEL_SOURCE
    }

@app.post("/segment")
async def segment_skin(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail="Model failed to load.")

    try:
        # 1. Read Image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        # 2. Preprocess
        inputs = processor(images=image, return_tensors="pt").to(DEVICE)

        # 3. Inference
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits 

        # 4. Upsample logits
        upsampled_logits = torch.nn.functional.interpolate(
            logits,
            size=image.size[::-1], 
            mode="bilinear",
            align_corners=False,
        )

        # 5. Get segmentation map
        pred_seg = upsampled_logits.argmax(dim=1)[0] 

        # 6. Create Binary Skin Mask
        mask = torch.zeros_like(pred_seg, dtype=torch.uint8)
        for label_id in SKIN_LABELS:
            mask = mask | (pred_seg == label_id).byte()
        
        mask_np = mask.cpu().numpy() * 255 

        # 7. Calculate real skin area percentage
        total_pixels = mask_np.size
        skin_pixels = np.count_nonzero(mask_np)
        skin_percentage = round((skin_pixels / total_pixels) * 100, 2)

        # 8. Apply mask (Return transparent PNG)
        image_np = np.array(image)
        rgba_image = np.zeros((image_np.shape[0], image_np.shape[1], 4), dtype=np.uint8)
        rgba_image[:, :, :3] = image_np
        rgba_image[:, :, 3] = mask_np # Alpha channel

        result_image = Image.fromarray(rgba_image)

        # 9. Encode image to base64
        img_byte_arr = io.BytesIO()
        result_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        import base64
        image_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        
        # 10. Return JSON with real skin analysis data
        from fastapi.responses import JSONResponse
        return JSONResponse(content={
            "skin_percentage": skin_percentage,
            "image": f"data:image/png;base64,{image_base64}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
