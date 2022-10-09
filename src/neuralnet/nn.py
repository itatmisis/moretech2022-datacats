import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns; sns.set()
import pickle
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from gensim.models import FastText
import torch
import transformers as ppb
from transformers import AutoTokenizer, AutoModel
from datetime import datetime, timedelta

data = pd.read_csv('dataset.csv')
with open('director1.txt', encoding='utf-8') as f:
    director = f.read()

with open('бухгалтер.txt', encoding='utf-8') as f:
    accountant = f.read()

class Model():
    def __init__(self, dataset, director, accountant):
        self.dataset = dataset
        self.df_train = dataset
        self.director = director
        self.accountant = accountant

    def tokenize_text(self, dataset, drop=True, stop_w=True):

        from string import punctuation, digits, ascii_letters
        punctuation += '—' + '«' + '»' + digits + ascii_letters
        punctuation = punctuation.replace('-', '')
        for p in (punctuation + '-'):
             dataset = dataset.replace(p, ' ')

        dataset = dataset.lower()
        tokens = word_tokenize(dataset)
        stop_words = set(stopwords.words('russian'))
        if(stop_w):
            tokens = [w for w in tokens if not w in stop_words]
        if (drop):
            stemmer = SnowballStemmer("russian")
            tokens = [stemmer.stem(i) for i in tokens]
        tokens = [i for i in tokens if len(i) > 2 ]

        return tokens

    def train_director(self):
        from string import punctuation, digits, ascii_letters
        punctuation += '—' + '«' + '»' + digits + ascii_letters
        punctuation = punctuation.replace('-', '')
        empl1 = pd.DataFrame([{'title': self.director.split(' ')[0], 'body': self.director}])
        empl2 = pd.DataFrame([{'title': self.accountant.split(' ')[0], 'body': self.accountant}])
        empl = pd.concat([empl1, empl2])
        empl.index = np.arange(0, empl.shape[0])
        employees_new = empl.copy()
        self.dataset = self.dataset[pd.to_datetime(self.dataset.timestamp).dt.year > 2018]
        self.dataset.loc[self.dataset[self.dataset.body.str.startswith('МОСКВА')].index, 'body'] =\
            self.dataset[self.dataset.body.str.startswith('МОСКВА')].body.str.split('.').str[1:].str.join(' ')
        self.dataset.index = self.dataset.id
        self.dataset.drop(columns=['id'], inplace=True)
        self.dataset.index.name = 'id'
        self.dataset.timestamp = pd.to_datetime(self.dataset.timestamp)
        self.dataset.drop(self.dataset[self.dataset.body.str.len() < 10].index, axis=0, inplace=True)
        dataset2 = self.dataset.copy()
        dataset2 = pd.concat([dataset2, employees_new])
        dataset2 = dataset2.fillna('')
        dataset2.body = dataset2.title + ' ' + dataset2.preamble + ' ' + dataset2.tldr + ' ' + dataset2.body

        vectorizer = TfidfVectorizer(tokenizer= lambda x: self.tokenize_text(x), max_features=30000)
        body = vectorizer.fit_transform(dataset2.body)
        df = pd.DataFrame(body.toarray(), columns=vectorizer.get_feature_names(), index=dataset2.index)
        dataset1 = dataset2.drop(columns=['title', 'preamble', 'tldr', 'body', 'source', 'topic', 'timestamp'])
        dataset1 = pd.merge(dataset1, df, left_index=True, right_index=True)
        tsvd = TruncatedSVD(n_components=min(dataset1.shape[0], 2000))
        tf_idf_vectors = tsvd.fit_transform(dataset1)

        nn = NearestNeighbors(n_neighbors=400)
        nn.fit(tf_idf_vectors[:-2])
        ids = nn.kneighbors(tf_idf_vectors[-2:], n_neighbors=400)[1]
        data_director = dataset.iloc[ids[0]]
        data_accountant = dataset.iloc[ids[1]]
        data_director = data_director.append(employees_new.iloc[0])
        data_accountant = data_accountant.append(employees_new.iloc[1])

        model_class, tokenizer_class, pretrained_weights = (
        ppb.DistilBertModel,
        ppb.DistilBertTokenizer,
        'distilbert-base-uncased'
        )

        tokenizer = tokenizer_class.from_pretrained(pretrained_weights)
        model = model_class.from_pretrained(pretrained_weights)
        data = data_director.copy()
        data['first_sentence'] = data.tldr
        data.loc[data[data['first_sentence'].isna()].index, 'first_sentence'] = data[data['first_sentence'].isna()].body.str.split(' ').str[:50].str.join(' ')
        data['data'] = data.body.apply(lambda x: self.tokenize_text(str(x), drop=False, stop_w=False))
        train = data['data'].apply(lambda x: embed_bert_cls(x, model, tokenizer))

        array = []
        for tr in train.values:
            array.append(tr)

        array = np.array(array)
        df_train = pd.DataFrame(array)
        nn = NearestNeighbors(n_neighbors=50)
        nn.fit(df_train[:-1])
        knnPickle = open('knnpickle_director', 'wb')

        # source, destination
        pickle.dump(nn, knnPickle)

        # close the file
        knnPickle.close()
        self.df_train = df_train

    def test_director(self):
        loaded_model = pickle.load(open('knnpickle_file', 'rb'))
        result = loaded_model.predict(self.df_train[-1:])
        data_first = data.iloc[ids[0]]
        return data_first.id

    def train_accountant(self):
        from string import punctuation, digits, ascii_letters
        punctuation += '—' + '«' + '»' + digits + ascii_letters
        punctuation = punctuation.replace('-', '')
        empl1 = pd.DataFrame([{'title': self.director.split(' ')[0], 'body': self.director}])
        empl2 = pd.DataFrame([{'title': self.accountant.split(' ')[0], 'body': self.accountant}])
        empl = pd.concat([empl1, empl2])
        empl.index = np.arange(0, empl.shape[0])
        employees_new = empl.copy()
        self.dataset = pd.read_csv('dataset.csv')
        self.dataset = self.dataset[pd.to_datetime(self.dataset.timestamp).dt.year > 2018]
        self.dataset.loc[self.dataset[self.dataset.body.str.startswith('МОСКВА')].index, 'body'] =\
            self.dataset[self.dataset.body.str.startswith('МОСКВА')].body.str.split('.').str[1:].str.join(' ')
        self.dataset.index = self.dataset.id
        self.dataset.drop(columns=['id'], inplace=True)
        self.dataset.index.name = 'id'
        self.dataset.timestamp = pd.to_datetime(self.dataset.timestamp)
        self.dataset.drop(self.dataset[self.dataset.body.str.len() < 10].index, axis=0, inplace=True)
        dataset2 = self.dataset.copy()
        dataset2 = pd.concat([dataset2, employees_new])
        dataset2 = dataset2.fillna('')
        dataset2.body = dataset2.title + ' ' + dataset2.preamble + ' ' + dataset2.tldr + ' ' + dataset2.body

        vectorizer = TfidfVectorizer(tokenizer= lambda x: self.tokenize_text(x), max_features=30000)
        body = vectorizer.fit_transform(dataset2.body)
        df = pd.DataFrame(body.toarray(), columns=vectorizer.get_feature_names(), index=dataset2.index)
        dataset1 = dataset2.drop(columns=['title', 'preamble', 'tldr', 'body', 'source', 'topic', 'timestamp'])
        dataset1 = pd.merge(dataset1, df, left_index=True, right_index=True)
        tsvd = TruncatedSVD(n_components=min(dataset1.shape[0], 2000))
        tf_idf_vectors = tsvd.fit_transform(dataset1)

        nn = NearestNeighbors(n_neighbors=400)
        nn.fit(tf_idf_vectors[:-2])
        ids = nn.kneighbors(tf_idf_vectors[-2:], n_neighbors=400)[1]
        data_director = dataset.iloc[ids[0]]
        data_accountant = dataset.iloc[ids[1]]
        data_director = data_director.append(employees_new.iloc[0])
        data_accountant = data_accountant.append(employees_new.iloc[1])

        model_class, tokenizer_class, pretrained_weights = (
        ppb.DistilBertModel,
        ppb.DistilBertTokenizer,
        'distilbert-base-uncased'
        )

        tokenizer = tokenizer_class.from_pretrained(pretrained_weights)
        model = model_class.from_pretrained(pretrained_weights)
        data = data_accountant.copy()
        data['first_sentence'] = data.tldr
        data.loc[data[data['first_sentence'].isna()].index, 'first_sentence'] = data[data['first_sentence'].isna()].body.str.split(' ').str[:50].str.join(' ')
        data['data'] = data.body.apply(lambda x: self.tokenize_text(str(x), drop=False, stop_w=False))
        train = data['data'].apply(lambda x: embed_bert_cls(x, model, tokenizer))

        array = []
        for tr in train.values:
            array.append(tr)

        array = np.array(array)
        df_train = pd.DataFrame(array)
        nn = NearestNeighbors(n_neighbors=50)
        nn.fit(df_train[:-1])
        self.df_train = df_train
    def test_director(self):
        loaded_model = pickle.load(open('knnpickle_file', 'rb'))
        result = loaded_model.predict(self.df_train[-1:])
        data_first = data.iloc[ids[0]]
        return data_first.id
