"""Image processing and embedding generation for .ima files."""

import os
import pydicom
import numpy as np
from typing import List
from PIL import Image
from sentence_transformers import SentenceTransformer

class ImaProcessor:
    def __init__(self):
        self.model = SentenceTransformer('clip-ViT-B-32')

    def generate_embedding(self, img: Image) -> List[float]:
        try:
            embedding = self.model.encode(img, convert_to_tensor=True)
        except Exception as e:
            print(f"Generate embedding failed: {e}")
        return embedding.tolist()

    def export_to_image(self, img: Image, filename: str, input_dir, output_dir, output_format="png"):
        output_filename = os.path.splitext(filename)[0] + f".{output_format}"
        output_path = os.path.join(output_dir if output_dir else input_dir, output_filename)
        img.save(output_path)


    def process_ima(self, filepath, to_img: bool=False, output_format="png", output_dir=None):
        """Read and process .ima file, producing either a embedding vector or extract the image inside 

        Args:
            img (PIL.Image, optional):
            filepath (str, optional): path to .ima file. Defaults to None.
            to_img (bool, optional): extract image inside or not. Defaults to False.
            output_format (str, optional): format of the extracted image. Defaults to "png".
            output_dir (str, optional): export image into an output directory. Defaults to None.

        Returns:
            List[float]: embedding vector of the input image
        """
        try:
            input_dir, filename = filepath.rsplit("/", 1)
            ds = pydicom.dcmread(filepath)
            img_array = ds.pixel_array
            img_min, img_max = img_array.min(), img_array.max()
            if img_max != img_min:
                img_norm = ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
            else:
                img_norm = np.zeros_like(img_array, dtype=np.uint8)
            img = Image.fromarray(img_norm)
                
            if to_img:
                self.export_to_image(img, filename, input_dir, output_dir, output_format)

            code = self.generate_embedding(img)    
            return code
        
        except Exception as e:
            print(f"Process {filename} failed: {e}!")