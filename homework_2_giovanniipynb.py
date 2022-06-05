# -*- coding: utf-8 -*-
"""Homework_2_Giovanniipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1i43xbhwlDEH3K3zytgaqhACapRluwQ4f
"""

import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader

!gdown --id 1iPGTsai4itDYKBgK4ihgGCGEGL-f4I68

!unzip archive.zip

df=pd.read_csv("IMDB Dataset.csv")
df.head()

df_np=df.to_numpy()

#Selecting only the first column which contains the reviews
reviews=df_np[:,0].tolist()

#Adding an "anchor point" at the end of each review so they can be splitted again later on
t = [r + "\n" for r in reviews]

t[:30]

reviews = "".join(t)

#Removing the special character
reviews=reviews.replace("<br /><br />", " ")

#Making all the letters lowercase
reviews=reviews.lower()

reviews[:50]

from string import punctuation
punctuation

#Removing punctuaction
list_characters = [c for c in reviews if c not in punctuation]

list_characters[:200]

rev= "".join(list_characters)

rev[:50]

type(rev)

#Splitting the whole text into single unique reviews
rev= rev.split("\n")

rev[:100]

len(rev)

#Last row deleted since it was an empy string.
rev=rev[:-1]

#Splitting the reviews in single words
reviews = [[w for w in r.split(" ") if len(w)>0] for r in rev]

reviews[10]

# compute the length of each review
reviews_lens = [len(r) for r in reviews]
# print the lenght of the first x reviews
reviews_lens[:10]

# build vocabulary
words = list(set([w for r in reviews for w in r]))
vocab = {words[i]: i+1 for i in range(len(words))} # we reserve i=0 for pad sequences

len(vocab)

vocab

reviews = [[vocab[w] for w in r] for r in reviews]

seq_len = 200

# Clip reviews to max seq_len words
reviews = [r[:seq_len] for r in reviews]

# Print average review length now
review_lens = [len(r) for r in reviews]
print(sum(review_lens)/len(review_lens))

# Pad reviews shorter than seq_len
# TODO test padding at the end
reviews = [[0]*(seq_len -(len(r))) + r for r in reviews]

# Print average review length now
review_lens = [len(r) for r in reviews]
print(sum(review_lens)/len(review_lens))

data = torch.LongTensor(reviews)

data.size()

#Labels
labels=df_np[:,1].tolist()

len(labels)

labels[:10]

#Tranforming labels into 0 or 1
labels = [0 if labels[i]=='negative' else 1 for i in range(len(labels))]

labels[:10]

# Convert sentiments to tensor
labels = torch.LongTensor(labels)

labels.size()

"""**Splitting dataset**"""

# some parameters
frac_train = 0.7 # fraction of data for train
frac_val = 0.2   # fraction of data for val
batch_size = 128

# shuffle dataset
num_data = data.size(0)
shuffle_idx = torch.randperm(num_data)
data = data[shuffle_idx,:]
labels = labels[shuffle_idx]

# split training, validation and test
num_train = int(num_data*frac_train)
num_val = int(num_data*frac_val)
num_test = num_data - num_train - num_val
train_data = data[:num_train,:]
train_labels = labels[:num_train]
val_data = data[num_train:num_train+num_val,:]
val_labels = labels[num_train:num_train+num_val]
test_data = data[num_train+num_val:,:]
test_labels = labels[num_train+num_val:]

print(train_data.size())
print(val_data.size())
print(test_data.size())

# create datasets
train_dataset = TensorDataset(train_data, train_labels)
val_dataset = TensorDataset(val_data, val_labels)
test_dataset = TensorDataset(test_data, test_labels)

# print the first elem of train dataset and its label
print(train_dataset[0])

# Create loaders
loaders = {"train": DataLoader(train_dataset, batch_size=batch_size, shuffle=True,  drop_last=True),
           "val":   DataLoader(val_dataset,   batch_size=batch_size, shuffle=False, drop_last=False),
           "test":  DataLoader(test_dataset,  batch_size=batch_size, shuffle=False, drop_last=False)}

"""**Defining our RNN**

"""

# Define model
class Model(nn.Module):
    
    def __init__(self, num_embed, embed_size, rnn_size):
        # params: 
        # num_embed: the number of the input vocabulary
        # embed_size: the size of the feature embedding
        # rnn_size: the number of neurons in the recurrent layer

        # Call parent constructor
        super().__init__()
        # Store values
        self.rnn_size = rnn_size
        # Define modules
        self.embedding = nn.Embedding(len(vocab)+1, embed_size)
        self.rnn = nn.RNNCell(embed_size, rnn_size) #RNNCell represents only a single time step
        self.output = nn.Linear(rnn_size, 2)
        
    def forward(self, x):
        # Embed data
        x = self.embedding(x)
        # Initialize state
        h = torch.zeros(x.shape[0], self.rnn_size).to(x.device.type) # the state of the cell
        
        # Input is: B x T x F
        # Process each time step
        for t in range(x.shape[1]):
            # Input at time t
            x_t = x[:,t,:]
            # Forward RNN and get new state
            h = self.rnn(x_t, h)
        # Classify final state
        x = self.output(h)
        return x

# Setup device
dev = torch.device("cuda")
#if torch.cuda.is_available() else "cpu"

# Model parameters
embed_size = 1024
rnn_size = 256

# Create model
model = Model(len(vocab)+1, embed_size, rnn_size).to(dev)

# Test model output
model.eval()
test_input = train_dataset[0][0].unsqueeze(0).to(dev)
print("Model output size:", model(test_input).size())

optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=5e-4)

# Define a loss 
criterion = nn.CrossEntropyLoss()

# Start training
from tqdm import tqdm
for epoch in range(100):
    # Initialize accumulators for computing average loss/accuracy
    epoch_loss_sum = {'train': 0, 'val': 0, 'test': 0}
    epoch_loss_cnt = {'train': 0, 'val': 0, 'test': 0}
    epoch_accuracy_sum = {'train': 0, 'val': 0, 'test': 0}
    epoch_accuracy_cnt = {'train': 0, 'val': 0, 'test': 0}
    # Process each split
    for split in ["train", "val", "test"]:
        # Set network mode
        if split == "train":
            model.train()
            torch.set_grad_enabled(True)
        else:
            model.eval()
            torch.set_grad_enabled(False)
        # Process all data in split
        for input, target in tqdm(loaders[split]):
            # Move to device
            input = input.to(dev)
            target = target.to(dev)
            # Reset gradients
            optimizer.zero_grad()
            # Forward
            output = model(input)
            loss = criterion(output, target)
            # Update loss sum
            epoch_loss_sum[split] += loss.item()
            epoch_loss_cnt[split] += 1
            # Compute accuracy
            _,pred = output.max(1)
            correct = pred.eq(target).sum().item()
            accuracy = correct/input.size(0)
            # Update accuracy sum
            epoch_accuracy_sum[split] += accuracy
            epoch_accuracy_cnt[split] += 1
            # Backward and optimize
            if split == "train":
                loss.backward()
                optimizer.step()
    # Compute average epoch loss/accuracy
    avg_train_loss = epoch_loss_sum["train"]/epoch_loss_cnt["train"]
    avg_train_accuracy = epoch_accuracy_sum["train"]/epoch_accuracy_cnt["train"]
    avg_val_loss = epoch_loss_sum["val"]/epoch_loss_cnt["val"]
    avg_val_accuracy = epoch_accuracy_sum["val"]/epoch_accuracy_cnt["val"]
    avg_test_loss = epoch_loss_sum["test"]/epoch_loss_cnt["test"]
    avg_test_accuracy = epoch_accuracy_sum["test"]/epoch_accuracy_cnt["test"]
    print(f"Epoch: {epoch+1}, TrL={avg_train_loss:.4f}, TrA={avg_train_accuracy:.4f},",
                            f"VL={avg_val_loss:.4f}, VA={avg_val_accuracy:.4f}, ",
                            f"TeL={avg_test_loss:.4f}, TeA={avg_test_accuracy:.4f}")

#Confusion matrix
y_pred = []
y_true = []

import seaborn as sns
from sklearn.metrics import confusion_matrix 
import os 
import numpy as np 
from matplotlib import pyplot as plt

# iterate over test data
for inputs, labels in tqdm(loaders["test"]):
  inputs, labels = inputs.cuda(), labels.cuda()
  output = model(inputs) # Feed Network
  output = (torch.max(torch.exp(output), 1)[1]).data.cpu().numpy()
  y_pred.extend(output) # Save Prediction
  
  labels = labels.data.cpu().numpy()
  y_true.extend(labels) # Save Truth

# constant for classes
classes = [0, 1]

# Build confusion matrix
cm = confusion_matrix(y_true, y_pred)
cmn = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
fig, ax = plt.subplots(figsize=(17,10))
sns.heatmap(cmn, annot=True, xticklabels=classes, yticklabels=classes)
plt.ylabel('Actual')
plt.xlabel('Predicted')
plt.show(block=False)