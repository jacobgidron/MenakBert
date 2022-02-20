import torch
from transformers import AutoTokenizer, AutoModel, TrainingArguments, Trainer
from dataset import textDataset, NIQQUD_SIZE, DAGESH_SIZE, SIN_SIZE
from torch import nn
import numpy as np
import sklearn


# import sklearn
MAX_LEN = 100
tokenizer = AutoTokenizer.from_pretrained("tau/tavbert-he")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class MenakBert(torch.nn.Module):
    """
    the model
    """

    def __init__(self):
        super().__init__()
        self.model = AutoModel.from_pretrained("tau/tavbert-he")
        self.linear_D = nn.Linear(768, DAGESH_SIZE)
        self.linear_S = nn.Linear(768, SIN_SIZE)
        self.linear_N = nn.Linear(768, NIQQUD_SIZE)

    def forward(self, x, y1):
        return self.linear_N(self.model(x)['last_hidden_state']) \
            , self.linear_D(self.model(x)['last_hidden_state']) \
            , self.linear_S(self.model(x)['last_hidden_state'])


from datasets import load_metric

metric = load_metric("accuracy")


def compute_metrics(eval_pred):
    print("hello")
    logits = eval_pred.predictions
    labels = eval_pred.label_ids
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)


from dataclasses import dataclass


@dataclass
class DataCollatorWithPadding:

    def __call__(self, features):
        batch = tokenizer([x.get("text") for x in features], padding='max_length', max_length=MAX_LEN,
                          return_tensors="pt")
        features_dict = {}
        features_dict["y1"] = {
            "N": torch.tensor([x.get("y1").get("N") for x in features]).long(),
            "D": torch.tensor([x.get("y1").get("D") for x in features]).long(),
            "S": torch.tensor([x.get("y1").get("S") for x in features]).long(),
        }
        features_dict["x"] = batch.data["input_ids"]
        features_dict["labels"] = batch.data["input_ids"]
        # features_dict["tokens"] = [tokenizer.encode(x.get("text"),return_tensors="pt") for x in features]

        # features_dict["input_ids"] = torch.tensor([pad_sequence_to_length(x, max_len) for x in input_ids]).long()
        # features_dict["attention_masks"] = torch.tensor([pad_sequence_to_length(x, max_len) for x in masks]).long()

        return features_dict

loss_fct1 = nn.CrossEntropyLoss()
loss_fct2 = nn.CrossEntropyLoss()
loss_fct3 = nn.CrossEntropyLoss()
class CustomTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get("y1")
        # forward pass
        outputs = model(**inputs)
        # outputs = [model(**inputs, x=x) for x in inputs.get("tokens")]
        logits = outputs
        # compute custom loss (suppose one has 3 labels with different weights)

        loss = loss_fct1(logits[0].permute((0, 2, 1)), labels["N"]) + \
               loss_fct2(logits[1].permute((0, 2, 1)),
                         labels["D"]) + loss_fct3(logits[2].permute((0, 2, 1)), labels["D"])
        return (loss, outputs[2]) if return_outputs else loss


model = MenakBert()

training_args = TrainingArguments("MenakBert",
                                  num_train_epochs=20,
                                  per_device_train_batch_size=10,
                                  per_device_eval_batch_size=10,
                                  learning_rate=0.05,
                                  save_total_limit=2,
                                  log_level="error",
                                  logging_dir="log",
                                  evaluation_strategy="steps")

# from datasets import load_metric
#
# metric = load_metric("accuracy")
#
# def compute_metrics(eval_pred):
#     logits = eval_pred.predictions
#     labels = eval_pred.label_ids
#     predictions = np.argmax(logits, axis=-1)
#     return metric.compute(predictions=predictions, references=labels)
small_train_dataset = textDataset(tuple(['train1.txt']), MAX_LEN - 1)
small_eval_dataset = textDataset(tuple(['test1.txt']), MAX_LEN - 1)

co = DataCollatorWithPadding()

trainer = CustomTrainer(
    model=model,
    data_collator=co,
    args=training_args,
    callbacks=[
        # YOUR CODE HERE
        # END YOUR END
    ],
    eval_dataset=small_train_dataset,
    train_dataset=small_eval_dataset,
    compute_metrics=compute_metrics,
)
trainer.train()
