# -*- coding: utf-8 -*-
"""Experiment Algorithms: Downsample2

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xrzL7_XBdGjKFv52MPjuXaBIXbQladfv

## Import
"""

from psutil import virtual_memory
ram_gb = virtual_memory().total / 1e9
print('Your runtime has {:.1f} gigabytes of available RAM\n'.format(ram_gb))

if ram_gb < 20:
  print('Not using a high-RAM runtime')
else:
  print('You are using a high-RAM runtime!')

!pip3 install emoji

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, emoji, re, json
from typing import List
from string import punctuation
from sklearn.model_selection import train_test_split

CONFIGS = {'project':'transformer_model',
           'run_name':'run_21_10_2023', # run_01_01_2023
           "num_files":10,
           #'imbalance_handle':'upsample', # upsample/downsample
           "vector_size":200,
           "min_count":20,
           'window':10,
           'max_seq_length':100,
           'loss_fn':'categorical_crossentropy',
           'optimizer':'adam',
           'learning_rate':5e-5,
           'val_split':0.1,
           'bidirectional':True,
           'lstm_neurons':200,
           'classifier_actvn':'softmax',
           'max_epochs':500,
           'batch_size':32,
           'embed_dim': 128,  # Embedding size for each token
           "num_heads": 1,  # Number of attention heads
           'ff_dim': 64  # Hidden layer size in feed forward network inside transformer
           }

USE_FRESH_DATA = False

"""## Data Handler and Loading"""

class DataHandler:
    def __init__(self, root: str, label_column: str, text_column: str, file_ext: str = "xlsx",
                 old_vocab='/content/drive/MyDrive/Tweet Scraping/vocab.json',
                 min_count:int=200,
                 max_word_len:int=20, min_word_needed:int=3):
        self.root = root
        self.label_column = label_column
        self.text_column = text_column
        self.file_ext = file_ext
        self.vocab = {}
        self.old_vocab_path = old_vocab
        self.min_word_needed = min_word_needed
        self.filter_words = None
        self.min_count = min_count
        self.max_word_len = max_word_len
        if old_vocab is not None:
          with open(old_vocab) as fp:
            self.vocab = json.load(fp)
            less_freq_words = [k for k,v in self.vocab.items() if v<min_count]
            huge_words = [k for k in self.vocab.keys() if len(k)>max_word_len]
            self.filter_words = less_freq_words+huge_words
            self.vocab = {k:v for k,v in self.vocab.items() if k not in self.filter_words}



    def read_files(self, number_of_files: int = 10):
        all_filenames = [file_name for file_name in os.listdir(self.root)if file_name.split(".")[-1] == self.file_ext ][:number_of_files]

        combined_df = pd.concat([pd.read_excel(os.path.join(self.root, f)) for f in all_filenames])
        self.data = combined_df
        print(f"Read {len(all_filenames)} files. Read total {len(self.data)} rows.")
        print(f"Label Counts:\n {self.data[self.label_column].value_counts()}")
        return self



    def preprocess_tweet(self, tweet:str, noise:str, stop_words:List):
        noise = list(noise)

        ntweet = emoji.replace_emoji(tweet)
        pattern = re.compile(u"[\u200c-\u200f\u202a-\u202f\u2066-\u2069]")
        ntweet = pattern.sub('', ntweet)

        nntweet = ''
        for word in ntweet.split(" "):
          if '#' not in word:
            nntweet+=" "+word

        ntweet = nntweet

        for e in noise:
          ntweet = ntweet.lower().replace(e, " ")

        ntweet = re.sub(r'''(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''', " ", ntweet)
        ntweet = re.sub(r'\s', ' ', ntweet)
        tweet_token = [t.replace("\n", " ") for t in ntweet.split(" ")]
        tweet_token = [t for t in tweet_token if len(t.strip())>0]

        tweet_no_noise = tweet_token
        new_tweet = [t for t in tweet_no_noise if t not in stop_words]


        new_tweet = " ".join(new_tweet)
        new_tweet = " ".join([t for t in new_tweet.split(' ') if len(t)>1])


        if '●' in new_tweet:
          print(tweet)
          print(new_tweet)
          print("\n")

        new_tweet = new_tweet.strip()


        if self.old_vocab_path is None:
          for t in new_tweet.split(' '):
            if self.vocab.get(t) is not None:
              self.vocab[t]+=1
            else:
              self.vocab[t]=1


        return new_tweet


    def data_clean(self, stopwords_path: str,apply_filter:bool=False):
        noise = '▬`%´•●=+÷।–][{}*“_…‘’&#\/;@abcdefghijklmnopqrstuvwxyz1234567890०१२३४५६७८९( )-.|!?",:—?।'+"'"
        stop_file = stopwords_path
        stop_words = []
        with open(stop_file) as fp:
          lines = fp.readlines()
          stop_words = list( map(lambda x:x.strip(), lines))

        if apply_filter and len(self.filter_words)>0:
          stop_words+=self.filter_words

        self.data['clean_tokenized_text'] = self.data[self.text_column].apply(lambda x: self.preprocess_tweet(x, noise, stop_words))
        self.data = self.data.drop_duplicates(subset=['clean_tokenized_text'])


        sorted_vocab = sorted(self.vocab.items(), key=lambda x:x[1])
        self.vocab = dict(sorted_vocab)
        if apply_filter:
          if len(self.filter_words)==0:
            less_freq_words = [k for k,v in self.vocab.items() if v<self.min_count]
            huge_words = [k for k in self.vocab.keys() if len(k)>self.max_word_len]
            self.filter_words = less_freq_words+huge_words

            self.data['clean_tokenized_text'] = self.data.clean_tokenized_text.apply(lambda x: self.filter_txt(x, self.filter_words))
            self.vocab = {k:v for k,v in self.vocab.items() if k not in self.filter_words}

        self.vocab = {k:v for k,v in self.vocab.items() if k not in self.filter_words}

        self.data = self.data[self.data.clean_tokenized_text.apply(lambda x: len(x.strip(" "))>=self.min_word_needed)]
        print(f"Cleaned data: {len(self.data)}, Vocab: {len(self.vocab)}")

        return self

    def filter_txt(self, text, filter_words):
      for w in filter_words:
        text = text.replace(w,'')


      return text.strip()


    def train_test_split(self, train_ratio:float=0.8, test_ratio:float=0.1,
                         valid_ratio:float=0.1):

        data=self.data
        labels = np.array(data_handler.data.label.to_list())
        X_train, X_test, Y_train, Y_test = train_test_split(data['clean_tokenized_text'],
                                                        labels,
                                                        random_state=0, train_size=train_ratio)
        X_valid, X_test, Y_valid, Y_test = train_test_split(X_test, Y_test, train_size=valid_ratio)

        return X_train, X_test, X_valid, Y_train, Y_test, Y_valid

    def handle_imbalance(self, how="downsample", labels=[1,2]):
      temp_df = self.data[self.data.label.isin(labels)].copy()

      majority_class = temp_df.label.mode().tolist()[0]
      print(f'\nMajority class is: {majority_class}.')

      major_df = temp_df[temp_df.label==majority_class]
      minor_df = temp_df[temp_df.label!=majority_class]
      num_diff = len(minor_df)
      print(f"Majority samples: {len(major_df)} and Minority Samples: {len(minor_df)}")



      if how=='downsample':
        redf = major_df.sample(n=num_diff)
        tdf = pd.concat([redf, minor_df])
      elif how=='upsample':
        redf = minor_df.sample(n=len(major_df)-num_diff)
        tdf = pd.concat([redf, minor_df, major_df])
      else:
        print('Handling imbalance not recognized. Step skipped.')
        return self

      self.data=tdf
      print(f'After handling imbalance by {how}: {self.data.label.value_counts()}')
      return self

    def convert_label(self, kind:str='ohe', labels=[1,2], ref={1:0, 2:1}):
        self.data = self.data[self.data.label.isin(labels)]
        self.label_ref = ref
        if ref is not None:
            self.data.label = self.data.label.apply(ref.get)
        else:
            if kind=='ohe':
                ohe = {}
                for i,l in enumerate(labels):
                    ohl = np.zeros(len(labels))
                    ohl[i] = 1
                    ohe[l]=ohl
                self.data.label = self.data.label.apply(ohe.get)
        return self

    def __iter__(self):
      for i, row in self.data.iterrows():
        yield row.clean_tokenized_text.split(' ')

    # def iter_xy(self, seq_length:int=100):
    #   for i, row in self.data.iterrows():
    #     words = np.array([word2token(w) for w in row.clean_tokenized_text[:seq_length]])

    #     yield words, row.label

# import json

# with open('vocab.json', 'w', encoding='utf8') as fp:
#   json.dump(data_handler.vocab, fp,ensure_ascii=False)

data_handler = DataHandler(root='/content/drive/MyDrive/Tweet Scraping/Label', label_column='label', text_column='text', min_count=2)

# data_handler.read_files(10).convert_label().data_clean(stopwords_path= "/content/drive/MyDrive/Tweet Scraping/Resources/nepali_stop_words.txt")

# OHE for labels
# data_handler.read_files(CONFIGS['num_files']).convert_label(ref={1:[1, 0], 2:[0, 1]}).data_clean(stopwords_path= "/content/drive/MyDrive/Tweet Scraping/Resources/nepali_stop_words.txt")

#
if USE_FRESH_DATA:
  data_handler.read_files(CONFIGS['num_files']).convert_label(ref={1:0, 2:1}).data_clean(apply_filter=True,  stopwords_path= "/content/drive/MyDrive/Tweet Scraping/Resources/stop_words_nepali_25_10_2023.txt") #.handle_imbalance(labels=[0,1])
  import json
  with open('/content/drive/MyDrive/Tweet Scraping/temp_vocab.json', 'w', encoding='utf8') as fp:
    json.dump(data_handler.vocab, fp,ensure_ascii=False)

  data_handler.data.to_csv('/content/drive/MyDrive/Tweet Scraping/temp_clean_data.csv')

else:
  import json
  with open("/content/drive/MyDrive/Tweet Scraping/temp_vocab.json") as fp:
    vocab = json.load(fp)

  filtered_data = pd.read_csv("/content/drive/MyDrive/Tweet Scraping/temp_clean_data.csv")
  data_handler.data = filtered_data
  data_handler.vocab = vocab
  data_handler = data_handler.handle_imbalance(labels=[0,1])



# purge max repeated words
num_max_repeated_words = 100000
max_repeated_words = [k for k,v in data_handler.vocab.items() if v>num_max_repeated_words]
filtered_data = data_handler.data.copy()
new_vocab = {k:v for k, v in data_handler.vocab.items() if k not in max_repeated_words}
filtered_data['clean_tokenized_text'] = filtered_data.clean_tokenized_text.apply(lambda x: data_handler.filter_txt(x, max_repeated_words))

filtered_data = filtered_data[filtered_data.clean_tokenized_text.apply(lambda x: len(x.split(' ')))>1]



"""### Vocab
Legth of vocab and least/most popular vocab.
"""

vocab = new_vocab #data_handler.vocab
print(f"Total number of words in vocabulary: {len(vocab)}")



vdf = pd.DataFrame([[k, v] for k, v in vocab.items()] , columns=['word', 'counts'], index = np.arange(len(vocab)))
vdf = vdf.sort_values('counts')
vdf





fname = ['nepali_stop_words.txt', 'NLP_stop_words.txt', 'stop_words_nepali_25_10_2023.txt'][2]
with open('/content/drive/MyDrive/Tweet Scraping/Resources/'+fname) as fp:
  stop_words = [s.strip() for s in fp.readlines()]



"""# Using TFiDF"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Create TF-IDF Vectorizer
tfidf_vectorizer = TfidfVectorizer(tokenizer=lambda x: x.split(" "),
                                         sublinear_tf=True, encoding='utf-8',
                                         decode_error='ignore',
                                         stop_words=stop_words,
                                          # vocabulary=vocab.keys()
                                   )


# get tfidf of all data
X_tfidf = tfidf_vectorizer.fit_transform(filtered_data['clean_tokenized_text'])

len(tfidf_vectorizer.vocabulary_), len(data_handler.vocab)

# now do split
X_train_tfidf, X_test_tfidf, Y_train, Y_test = train_test_split(X_tfidf,
                                                        filtered_data['label'],
                                                        random_state=111, train_size=0.8)

"""## TFIDF Feature Vectors"""

feature_names = tfidf_vectorizer.get_feature_names_out()
feature_names[0]

tfidf_df = pd.DataFrame(X_tfidf.toarray(), index=filtered_data['clean_tokenized_text'], columns=feature_names)
tfidf_df

"""## Train Logistic Regression"""

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report

# Train Logistic Regression Classifier
classifier = LogisticRegression()
classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred_train = classifier.predict(X_train_tfidf)
y_pred = classifier.predict(X_test_tfidf)


print("Traning Performance")
accuracy = accuracy_score(Y_train, y_pred_train)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_train, y_pred_train)
f1 = f1_score(Y_train, y_pred_train)
recall = recall_score(Y_train, y_pred_train)
confusion = confusion_matrix(Y_train, y_pred_train)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_train, y_pred_train)

print("Classification Report:\n", report)






# Evaluate the Model

print("Testing Performance")
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_test, y_pred)

print("Classification Report:\n", report)

"""## Train Decision Tree"""

from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report


# Train Decision Tree Classifier
classifier = DecisionTreeClassifier()
classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred_train = classifier.predict(X_train_tfidf)
y_pred = classifier.predict(X_test_tfidf)


print("Traning Performance")
accuracy = accuracy_score(Y_train, y_pred_train)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_train, y_pred_train)
f1 = f1_score(Y_train, y_pred_train)
recall = recall_score(Y_train, y_pred_train)
confusion = confusion_matrix(Y_train, y_pred_train)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_train, y_pred_train)

print("Classification Report:\n", report)






# Evaluate the Model

print("Testing Performance")
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_test, y_pred)

print("Classification Report:\n", report)

"""## Train NaiveBayes"""

from sklearn.naive_bayes import BernoulliNB
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report


# Train Binary Naive Bayes Classifier
classifier = BernoulliNB()
classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred_train = classifier.predict(X_train_tfidf)
y_pred = classifier.predict(X_test_tfidf)


print("Traning Performance")
accuracy = accuracy_score(Y_train, y_pred_train)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_train, y_pred_train)
f1 = f1_score(Y_train, y_pred_train)
recall = recall_score(Y_train, y_pred_train)
confusion = confusion_matrix(Y_train, y_pred_train)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_train, y_pred_train)

print("Classification Report:\n", report)

# Evaluate the Model

print("Testing Performance")
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_test, y_pred)

print("Classification Report:\n", report)

"""## Train Random Forest"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report


# Train Random Forest Classifier
classifier = RandomForestClassifier(n_estimators=100, random_state=42)
classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred_train = classifier.predict(X_train_tfidf)
y_pred = classifier.predict(X_test_tfidf)


print("Traning Performance")
accuracy = accuracy_score(Y_train, y_pred_train)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_train, y_pred_train)
f1 = f1_score(Y_train, y_pred_train)
recall = recall_score(Y_train, y_pred_train)
confusion = confusion_matrix(Y_train, y_pred_train)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_train, y_pred_train)

print("Classification Report:\n", report)


# Evaluate the Model

print("Testing Performance")
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_test, y_pred)

print("Classification Report:\n", report)



"""## Train SVM"""

from sklearn.svm import SVC
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report


# Train SVM Classifier
classifier = SVC(kernel='linear', C=1.0, random_state=42)
classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred_train = classifier.predict(X_train_tfidf)
y_pred = classifier.predict(X_test_tfidf)


print("Traning Performance")
accuracy = accuracy_score(Y_train, y_pred_train)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_train, y_pred_train)
f1 = f1_score(Y_train, y_pred_train)
recall = recall_score(Y_train, y_pred_train)
confusion = confusion_matrix(Y_train, y_pred_train)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_train, y_pred_train)

print("Classification Report:\n", report)

# Evaluate the Model

print("Testing Performance")
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")


precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_test, y_pred)

print("Classification Report:\n", report)

"""## SVM RBF"""

from sklearn.svm import SVC
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report

# Train SVM Classifier
classifier = SVC(kernel='linear', C=1.5, gamma='auto', random_state=42)
classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred = classifier.predict(X_test_tfidf)

# Evaluate the Model
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")
precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)

report = classification_report(Y_test, y_pred)
print("Classification Report:\n", report)

"""## KN Classifier"""

from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report
classifier = KNeighborsClassifier(n_neighbors=5)

classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred = classifier.predict(X_test_tfidf)

# Evaluate the Model
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")

precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)


report = classification_report(Y_test, y_pred)
print("Classification Report:\n", report)

"""## Gradient Boosting"""

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report

classifier = GradientBoostingClassifier(n_estimators=100, learning_rate=.05, max_depth=5, random_state=42)


classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred = classifier.predict(X_test_tfidf)

# Evaluate the Model
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")
precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)


report = classification_report(Y_test, y_pred)
print("Classification Report:\n", report)

"""## Adaboost"""

from sklearn.ensemble import AdaBoostClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report

classifier = AdaBoostClassifier(n_estimators=50, learning_rate=0.1, random_state=42)


classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred = classifier.predict(X_test_tfidf)

# Evaluate the Model
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")
precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)


report = classification_report(Y_test, y_pred)
print("Classification Report:\n", report)

"""## XGBoost"""

from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report

classifier = XGBClassifier()

classifier.fit(X_train_tfidf, Y_train)

# Make Predictions
y_pred = classifier.predict(X_test_tfidf)

# Evaluate the Model
accuracy = accuracy_score(Y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")
precision = precision_score(Y_test, y_pred)
f1 = f1_score(Y_test, y_pred)
recall = recall_score(Y_test, y_pred)
confusion = confusion_matrix(Y_test, y_pred)
print("Precision: " , precision)
print("F1 score: ",f1)
print("Recall score: ", recall)
print("Confusion Matrix:\n ", confusion)


report = classification_report(Y_test, y_pred)
print("Classification Report:\n", report)

# just to make sure not run below.
sadgfsadf





"""# Using Word2Vec"""



"""## Logistic Regression"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from gensim.models import Word2Vec
from gensim.models.doc2vec import TaggedDocument
from nltk.tokenize import word_tokenize
import nltk
from tqdm import tqdm

# Download NLTK resources if not already downloaded
nltk.download('punkt')

# Split the dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(filtered_data['clean_tokenized_text'],filtered_data['label'], test_size=0.2, random_state=42)

# Tokenize the text using NLTK
tokenized_train = [word_tokenize(text.lower()) for text in tqdm(X_train, desc="Tokenizing Train Data")]
tokenized_test = [word_tokenize(text.lower()) for text in tqdm(X_test, desc="Tokenizing Test Data")]

# Train Word2Vec model
w2v_model = Word2Vec(sentences=tokenized_train, vector_size=10000, window=15, min_count=1, workers=4)

# Function to calculate document vectors using Word2Vec model
def calculate_doc_vector(model, tokenized_text):
    vector_sum = np.zeros(model.vector_size)
    for word in tokenized_text:
        if word in model.wv:
            vector_sum += model.wv[word]
    return vector_sum / len(tokenized_text)

# Create document vectors for training and testing sets
X_train_w2v = np.array([calculate_doc_vector(w2v_model, tokenized_text) for tokenized_text in tqdm(tokenized_train, desc="Creating Train Vectors")])
X_test_w2v = np.array([calculate_doc_vector(w2v_model, tokenized_text) for tokenized_text in tqdm(tokenized_test, desc="Creating Test Vectors")])

# Train a logistic regression classifier
clf = LogisticRegression(random_state=42)
clf.fit(X_train_w2v, y_train)

# Predictions on the test set
y_pred = clf.predict(X_test_w2v)

# Evaluate the model
print(classification_report(y_test, y_pred))
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

"""## Decision Tree"""

from sklearn.tree import DecisionTreeClassifier

# Train Decision Tree Classifier
clf = DecisionTreeClassifier()
clf.fit(X_train_w2v, y_train)

# Predictions on the test set
y_pred = clf.predict(X_test_w2v)

# Evaluate the model
print(classification_report(y_test, y_pred))
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

"""## Naive Bayes"""

from sklearn.naive_bayes import BernoulliNB

# Train Binary Naive Bayes Classifier
clf = BernoulliNB()
clf.fit(X_train_w2v, y_train)

# Predictions on the test set
y_pred = clf.predict(X_test_w2v)

# Evaluate the model
print(classification_report(y_test, y_pred))
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

"""## Random Forest"""

from sklearn.ensemble import RandomForestClassifier

# Train Random Forest Classifier
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train_w2v, y_train)

# Predictions on the test set
y_pred = clf.predict(X_test_w2v)

# Evaluate the model
print(classification_report(y_test, y_pred))
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

"""## SVM"""

from sklearn.svm import SVC

# Train SVM Classifier
clf = SVC(kernel='linear', C=1.0, random_state=42)
clf.fit(X_train_w2v, y_train)

# Predictions on the test set
y_pred = clf.predict(X_test_w2v)

# Evaluate the model
print(classification_report(y_test, y_pred))
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

"""# Count Vectorizer"""

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split

# X_train, X_test, X_valid, Y_train, Y_test, Y_valid = data_handler.train_test_split()

vectorizer = CountVectorizer(ngram_range=(1, 3), vocabulary=list(vocab.keys())).fit(list(vocab.keys()))

X = vectorizer.transform(filtered_data['clean_tokenized_text']).toarray()
y = filtered_data['label'].to_numpy()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

X.shape, y.shape

vectorizer.get_feature_names_out()[1000:1005]

filtered_data.label.unique() # problem yehi ho.... only one label of data is there

"""## MultinomialNB"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Create a CountVectorizer to convert text to a bag-of-words
vectorizer = CountVectorizer()  # You can adjust max_features based on your dataset size

train_data, test_data, train_labels, test_labels = X_train, X_test, y_train, y_test

# Fit and transform on the training data
#train_features = vectorizer.fit_transform(train_data)

# Transform the test data
#test_features = vectorizer.fit_transform(test_data)

# Create a Naive Bayes classifier
classifier = MultinomialNB()

# Train the classifier
classifier.fit(train_data, train_labels)

# Make predictions on the test set
predictions = classifier.predict(test_data)

# Evaluate accuracy
accuracy = accuracy_score(test_labels, predictions)
print(f'Accuracy: {accuracy:.2f}')

# Display classification report and confusion matrix
print('\nClassification Report:')
print(classification_report(test_labels, predictions))

print('\nConfusion Matrix:')
print(confusion_matrix(test_labels, predictions))

# see now its different?

"""## Train Logistic Regression"""

from sklearn.linear_model import LogisticRegression  # or any other classifier you prefer
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, recall_score, precision_score



clf = LogisticRegression(random_state=0).fit(X_train, y_train)

train_score = clf.score(X_train, y_train)
test_score = clf.score(X_test, y_test)


print(f"Train Score: {train_score}, Test Score: {test_score}")

Y_pred = clf.predict(X_test)
f1 = f1_score(y_test, Y_pred)
recall = recall_score(y_test, Y_pred)
precision = precision_score(y_test, Y_pred)
print(f1)
print(recall)
print(precision)

"""## RandomForest"""

# Data Processing
import pandas as pd
import numpy as np

# Modelling
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, ConfusionMatrixDisplay
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from scipy.stats import randint

# Tree Visualisation
from sklearn.tree import export_graphviz
from IPython.display import Image
import graphviz

rf = RandomForestClassifier(bootstrap=True,criterion='entropy',)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)

f1 = f1_score(y_test, y_pred)

recall = recall_score(y_test, y_pred)

precision = precision_score(y_test, y_pred)


print("F1 Score:", f1)
print("Recall:", recall)
print("Precision:", precision)

"""## SVM"""

from sklearn import model_selection, svm

SVM = svm.SVC(C=1.0, kernel='linear', degree=3, gamma='auto')
SVM.fit(X_train, y_train)
# predict labels
predictions_SVM = SVM.predict(X_test)
#get the accuracy
print("Accuracy: ",accuracy_score(predictions_SVM, y_test)*100)

f1 = f1_score(y_test, predictions_SVM)

recall = recall_score(y_test, predictions_SVM)
precision = precision_score(y_test, predictions_SVM)
print(f1)
print(recall)
print(precision)

"""## NaiveBayes"""

from sklearn.naive_bayes import GaussianNB
from sklearn import metrics
gnb = GaussianNB()
gnb.fit(X_train, y_train)

# making predictions on the testing set
y_pred = gnb.predict(X_test)

print("Gaussian Naive Bayes model accuracy(in %):", metrics.accuracy_score(y_test, y_pred)*100)

f1 = f1_score(Y_test, y_pred)


recall = recall_score(Y_test, y_pred)


precision = precision_score(Y_test, y_pred)
print(f1)
print(recall)
print(precision)

"""## Decision Tree"""

from sklearn.tree import DecisionTreeClassifier
clf_gini = DecisionTreeClassifier(criterion='entropy', max_depth=10, random_state=0)
clf_gini.fit(X_train, y_train)

y_pred_gini = clf_gini.predict(X_test)

from sklearn.metrics import accuracy_score

print('Model accuracy score with criterion gini index: {0:0.4f}'. format(accuracy_score(y_test, y_pred_gini)))

