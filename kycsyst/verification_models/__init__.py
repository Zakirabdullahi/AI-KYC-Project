import torch
import torch.nn as nn
from torchvision import models


class VGGFace2(nn.Module):
    """
    VGGFace2 model for face verification.
    Uses a pre-trained ResNet50 backbone for face embeddings.
    """
    
    def __init__(self, embedding_size=512):
        """
        Initialize VGGFace2 model.
        
        Parameters:
            embedding_size (int): Size of face embeddings.
        """
        super(VGGFace2, self).__init__()
        
        # Use ResNet50 as backbone
        self.backbone = models.resnet50(pretrained=True)
        
        # Modify final layer for face embeddings
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Linear(num_features, embedding_size)
        
        self._device = None
    
    def forward(self, x):
        """
        Forward pass to get face embeddings.
        
        Parameters:
            x (torch.Tensor): Input face images.
            
        Returns:
            torch.Tensor: Face embeddings.
        """
        embeddings = self.backbone(x)
        # Normalize embeddings
        embeddings = nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings
    
    def device(self):
        """
        Get the device the model is on.
        
        Returns:
            torch.device: Device (cpu or cuda).
        """
        if self._device is None:
            self._device = next(self.parameters()).device
        return self._device
    
    @staticmethod
    def load_model(device="cpu", pretrained=True):
        """
        Load VGGFace2 model.
        
        Parameters:
            device (str or torch.device): Device to load model on.
            pretrained (bool): Whether to use pretrained weights.
            
        Returns:
            VGGFace2: Loaded model.
        """
        model = VGGFace2()
        model = model.to(device)
        model._device = device if isinstance(device, torch.device) else torch.device(device)
        model.eval()
        
        return model
