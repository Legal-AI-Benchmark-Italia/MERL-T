from transformers import AutoTokenizer, AutoModelForTokenClassification

# Pre-trained Italian BERT model
model_name = "dbmdz/bert-base-italian-xxl-cased"

# Download and save tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

# Save to your models directory
model_path = "/home/ec2-user/MERL-T/src/data_lab/ner-giuridico/models"
tokenizer.save_pretrained(model_path)
model.save_pretrained(model_path)

print(f"Model and tokenizer saved to {model_path}")