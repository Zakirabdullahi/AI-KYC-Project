import cv2 as cv
import numpy as np
import torch
from PIL import Image
from torchvision import transforms


def get_image(filename):
    """
    Load an image from file and convert to RGB numpy array.
    
    Parameters:
        filename (str): Path to the image file.
        
    Returns:
        np.ndarray: RGB image as numpy array.
    """
    img = Image.open(filename)
    img = img.convert('RGB')
    return np.array(img)


def extract_face(image, mtcnn, padding=0):
    """
    Extract face from image using MTCNN detector.
    
    Parameters:
        image (np.ndarray): RGB image as numpy array.
        mtcnn (MTCNN): MTCNN face detector instance.
        padding (int): Padding around detected face box.
        
    Returns:
        tuple: (face_image, bounding_box, landmarks)
            - face_image: Cropped face as numpy array or None if no face detected
            - bounding_box: [x1, y1, x2, y2] coordinates or None
            - landmarks: Facial landmarks or None
    """
    # Detect faces
    boxes, probs, landmarks = mtcnn.detect(image, landmarks=True)
    
    if boxes is None or len(boxes) == 0:
        return None, None, None
    
    # Get the first (most confident) face
    box = boxes[0]
    landmark = landmarks[0] if landmarks is not None else None
    
    # Add padding to bounding box
    x1, y1, x2, y2 = map(int, box)
    h, w = image.shape[:2]
    
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)
    
    # Crop face
    face = image[y1:y2, x1:x2]
    
    return face, [x1, y1, x2, y2], landmark


def face_transform(face, model_name="VGG-Face2", device="cpu"):
    """
    Transform face image for model input.
    
    Parameters:
        face (np.ndarray): Face image as numpy array.
        model_name (str): Name of the model.
        device (str): Device to use ('cpu' or 'cuda').
        
    Returns:
        torch.Tensor: Transformed face tensor ready for model input.
    """
    # Convert to PIL Image if numpy array
    if isinstance(face, np.ndarray):
        face = Image.fromarray(face)
    
    # Define transformation
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])
    
    # Apply transformation
    face_tensor = transform(face)
    face_tensor = face_tensor.unsqueeze(0)  # Add batch dimension
    
    return face_tensor.to(device)
