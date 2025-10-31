"""
🎧 Deepfake Audio Detector — FastAPI Server
Author: Victor 😎
Description:
Upload an audio file via HTTP request and detect whether it's a
human or AI-generated voice using a pre-trained CNN model.
"""

import io
import numpy as np
import librosa
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tensorflow as tf
from tensorflow.keras.models import load_model

# ------------------------------------------------------------
# Initialize FastAPI app
# ------------------------------------------------------------
app = FastAPI(
    title="🎧 Deepfake Audio Detector API",
    description="An API for detecting AI-generated vs human voices using a CNN model.",
    version="1.0"
)

# ------------------------------------------------------------
# Enable CORS (so your frontend can talk to this API)
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to your frontend domain for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# Load pre-trained CNN model
# ------------------------------------------------------------
print("🔁 Loading model...")
try:
    model = load_model("Promodel.keras")
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None


# ------------------------------------------------------------
# Convert audio bytes -> Mel Spectrogram
# ------------------------------------------------------------
def audio_to_spectrogram(file_bytes: bytes):
    try:
        # Load the audio file into memory
        y, sr = librosa.load(io.BytesIO(file_bytes), sr=None)
        
        # Generate Mel spectrogram
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
        S_DB = librosa.power_to_db(S, ref=np.max)
        
        # Resize to match model input shape
        S_DB = np.resize(S_DB, (128, 128))
        
        # Normalize between 0–1
        S_DB = (S_DB - S_DB.min()) / (S_DB.max() - S_DB.min())
        return S_DB
    except Exception as e:
        print(f"⚠️ Error processing file: {e}")
        return None


# ------------------------------------------------------------
# API route for predictions
# ------------------------------------------------------------
@app.post("/predict/")
async def predict_audio(file: UploadFile = File(...)):
    if model is None:
        return JSONResponse(status_code=500, content={"error": "Model not loaded on server."})
    
    try:
        # Read the uploaded audio file
        file_bytes = await file.read()
        
        # Convert to mel spectrogram
        spectrogram = audio_to_spectrogram(file_bytes)
        if spectrogram is None:
            return JSONResponse(status_code=400, content={"error": "Could not process audio file."})
        
        # Add batch and channel dimensions for CNN
        spectrogram = spectrogram[np.newaxis, ..., np.newaxis]
        
        # Run prediction
        pred = model.predict(spectrogram)[0][0]
        
        # Interpret result
        if pred < 0.5:
            label = "HUMAN"
            confidence = (1 - pred) * 100
        else:
            label = "AI-GENERATED"
            confidence = pred * 100
        
        return {
            "prediction": label,
            "confidence": round(float(confidence), 2)
        }

    except Exception as e:
        print(f"❌ Prediction error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ------------------------------------------------------------
# Root endpoint
# ------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "🎧 Deepfake Audio Detector API is running!"}


# ------------------------------------------------------------
# Run server (if run directly)
# ------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
