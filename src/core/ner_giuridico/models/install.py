from transformers import AutoTokenizer, AutoModelForTokenClassification
from pathlib import Path
import sys

# Pre-trained Italian BERT model
model_name = "dbmdz/bert-base-italian-xxl-cased"

# Download and save tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

# Determine the directory of the current script
script_dir = Path(__file__).resolve().parent

# Save to the script's directory (or a subdirectory if preferred)
model_path = script_dir # Salva direttamente nella cartella 'models'
# Alternatively, save in a subdirectory of the script's dir:
# model_path = script_dir / "downloaded_model"

# Create the directory if it doesn't exist
model_path.mkdir(parents=True, exist_ok=True)

try:
    tokenizer.save_pretrained(model_path)
    model.save_pretrained(model_path)
    print(f"Model and tokenizer saved to {model_path}")
except Exception as e:
    print(f"Error saving model/tokenizer to {model_path}: {e}", file=sys.stderr)