import torch
import torch.nn.functional as F


def Cosine_Distance(embedding1, embedding2):
    """
    Calculate cosine distance between two embeddings.
    
    Parameters:
        embedding1 (torch.Tensor): First embedding vector.
        embedding2 (torch.Tensor): Second embedding vector.
        
    Returns:
        float: Cosine distance (1 - cosine similarity).
    """
    similarity = F.cosine_similarity(embedding1, embedding2)
    distance = 1 - similarity.item()
    return distance


def Euclidean_Distance(embedding1, embedding2):
    """
    Calculate Euclidean distance between two embeddings.
    
    Parameters:
        embedding1 (torch.Tensor): First embedding vector.
        embedding2 (torch.Tensor): Second embedding vector.
        
    Returns:
        float: Euclidean distance.
    """
    distance = torch.dist(embedding1, embedding2, p=2)
    return distance.item()


def L1_Distance(embedding1, embedding2):
    """
    Calculate L1 (Manhattan) distance between two embeddings.
    
    Parameters:
        embedding1 (torch.Tensor): First embedding vector.
        embedding2 (torch.Tensor): Second embedding vector.
        
    Returns:
        float: L1 distance.
    """
    distance = torch.dist(embedding1, embedding2, p=1)
    return distance.item()


def findThreshold(model_name="VGG-Face2", distance_metric="euclidean"):
    """
    Return the threshold for face verification based on model and distance metric.
    
    Parameters:
        model_name (str): Name of the face recognition model.
        distance_metric (str): Distance metric used ('cosine', 'euclidean', 'L1').
        
    Returns:
        float: Threshold value for verification.
    """
    # Thresholds based on empirical testing
    thresholds = {
        "VGG-Face2": {
            "cosine": 0.40,
            "euclidean": 0.60,
            "L1": 10.0
        }
    }
    
    if model_name not in thresholds:
        # Default thresholds
        return 0.60 if distance_metric == "euclidean" else 0.40
    
    return thresholds[model_name].get(distance_metric, 0.60)
