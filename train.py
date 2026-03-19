import tensorflow as tf
from tensorflow.keras import layers, models
import os
import logging

logging.basicConfig(level=logging.INFO)

DATASET_DIR = "dataset"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

BATCH_SIZE = 32
IMG_HEIGHT = 128
IMG_WIDTH = 128
EPOCHS = 15

def build_model(num_classes):
    """Builds a VGG-style Convolutional Neural Network."""
    model = models.Sequential([
        layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3)),
        layers.Rescaling(1./255),
        
        layers.Conv2D(32, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        
        layers.Conv2D(64, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        
        layers.Conv2D(128, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5), # Prevent overfitting
        layers.Dense(num_classes, activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

def train():
    logging.info("Loading dataset...")
    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE
    )

    class_names = train_ds.class_names
    logging.info(f"Classes detected: {class_names}")

    model = build_model(len(class_names))
    model.summary()

    logging.info("Starting training...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS
    )

    model_path = os.path.join(MODEL_DIR, "pattern_cnn.keras")
    model.save(model_path)
    logging.info(f"Model saved to {model_path}")
    
    # Save class names mapping for inference
    with open(os.path.join(MODEL_DIR, "classes.txt"), "w") as f:
        f.write(",".join(class_names))

if __name__ == "__main__":
    train()
