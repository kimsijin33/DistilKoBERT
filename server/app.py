import time
import argparse

import torch
from flask import Flask, jsonify, request, render_template

from distilkobert import get_distilkobert_model, get_tokenizer, get_nsmc_model


MODEL_CLASSES = {
    'nsmc': {
        'model': get_nsmc_model,
        'tokenizer': get_tokenizer
    }
}


app = Flask(__name__)
tokenizer = None
model = None
args = None


def init_model():
    global tokenizer, model
    model = MODEL_CLASSES[args.model_type]['model'](no_cuda=args.no_cuda)
    tokenizer = MODEL_CLASSES[args.model_type]['tokenizer']()
    model.eval()


def convert_texts_to_tensors(texts, max_seq_len, add_special_tokens, no_cuda=False):
    input_ids = []
    attention_mask = []
    for text in texts:
        input_id = tokenizer.encode(text, add_special_tokens=add_special_tokens)
        input_id = input_id[:max_seq_len]

        attention_id = [1] * len(input_id)

        # Zero padding
        padding_length = max_seq_len - len(input_id)
        input_id = input_id + ([tokenizer.pad_token_id] * padding_length)
        attention_id = attention_id + ([0] * padding_length)

        input_ids.append(input_id)
        attention_mask.append(attention_id)

    # Change list to torch tensor
    device = "cuda" if torch.cuda.is_available() and not no_cuda else "cpu"

    input_ids = torch.tensor(input_ids, dtype=torch.long).to(device)
    attention_mask = torch.tensor(attention_mask, dtype=torch.long).to(device)
    return input_ids, attention_mask


@app.route("/predict", methods=["POST", "GET"])
def predict():
    # Prediction
    text = request.args.get('text')
    max_seq_len = int(request.args.get('max_seq_len'))

    texts = [text]

    input_ids, attention_mask = convert_texts_to_tensors(texts, max_seq_len, args.add_special_tokens)
    outputs = model(input_ids, attention_mask, None)
    logits = outputs[0]

    preds = logits.detach().cpu().tolist()
    preds = [0 if pred[0] > pred[1] else 1 for pred in preds]

    return """
    <h3>"{}" : {}</h3>
    """.format(texts[0], "Positive" if preds[0] == 1 else "Negative")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--port_num", type=int, default=12345, help="Port Number")
    parser.add_argument("-m", "--model_type", type=str, default="nsmc",
                        help="Model type selected in the list: " + ", ".join(MODEL_CLASSES.keys()))
    parser.add_argument("-s", "--add_special_tokens", action="store_true", help="Whether to add CLS and SEP token on each texts automatically")
    parser.add_argument("-n", "--no_cuda", action="store_true", help="Avoid using CUDA when available")
    args = parser.parse_args()

    print("Initializing the {} model...".format(args.model_type))
    init_model()

    app.run(host="0.0.0.0", debug=False, port=args.port_num)
