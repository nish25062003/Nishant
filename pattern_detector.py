import tensorflow as tf
import numpy as np
import os
from PIL import Image

class PatternDetector:
    def __init__(self, model_path="models/pattern_cnn.keras", classes_path="models/classes.txt"):
        self.model = None
        self.class_names = []
        
        if os.path.exists(model_path):
            self.model = tf.keras.models.load_model(model_path)
            with open(classes_path, "r") as f:
                self.class_names = f.read().split(",")
        else:
            print("Warning: Model not found. Please run train.py first.")

    def predict(self, image_path):
        if self.model is None:
            return "Model not loaded", 0.0
            
        img = tf.keras.utils.load_img(image_path, target_size=(128, 128))
        img_array = tf.keras.utils.img_to_array(img)
        img_array = tf.expand_dims(img_array, 0) # Create batch axis

        predictions = self.model.predict(img_array, verbose=0)
        score = tf.nn.softmax(predictions[0])
        
        predicted_class = self.class_names[np.argmax(score)]
        confidence = 100 * np.max(score)
        
        return predicted_class, confidence
