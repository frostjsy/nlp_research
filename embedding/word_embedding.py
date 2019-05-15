import gensim
import sys,os
ROOT_PATH = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(ROOT_PATH)
import numpy as np
from itertools import chain
import tensorflow as tf
from utils.preprocess import *
from common.layers import get_initializer
import collections
import pickle
import pandas as pd
import pdb


class WordEmbedding():
    def __init__(self, text_list, dict_path, vocab_dict, random = False,\
                 maxlen = 20, embedding_size = 128, **kwargs):
        self.embedding_path = kwargs['conf']['word_embedding_path']
        self.maxlen= maxlen
        self.dict_path = dict_path
        self.size = embedding_size
        self.embedding = tf.get_variable("embeddings",
                                         shape = [len(vocab_dict), self.size],
                                         initializer=get_initializer('xavier'),
                                         trainable = True)
        if not random:
            tf.assign(self.embedding, self._get_embedding(vocab_dict))
        self.input_ids = {}

    def __call__(self, name = "word_embedding"):
        """define placeholder"""
        self.input_ids[name] = tf.placeholder(dtype=tf.int32, shape=[None,
                                                                     self.maxlen], name = name)
        return tf.nn.embedding_lookup(self.embedding, self.input_ids[name])

    def feed_dict(self, input_x, name = 'word_embedding'):
        feed_dict = {}
        feed_dict[self.input_ids[name]] = input_x
        return feed_dict

    def pb_feed_dict(self, graph, input_x, name = 'word_embedding'):
        feed_dict = {}
        input_x_node = graph.get_operation_by_name(name).outputs[0]
        feed_dict[input_x_node] = input_x
        return feed_dict

    @staticmethod
    def build_dict(dict_path, text_list = None,  mode = "train"):
        if not os.path.exists(dict_path) or mode == "train":
            assert text_list != None, "text_list can't be None in train mode"
            words = list()
            for content in text_list:
                for word in word_tokenize(clean_str(content)):
                    words.append(word)

            word_counter = collections.Counter(words).most_common()
            vocab_dict = dict()
            vocab_dict["<pad>"] = 0
            vocab_dict["<unk>"] = 1
            for word, _ in word_counter:
                vocab_dict[word] = len(vocab_dict)

            with open(dict_path, "wb") as f:
                pickle.dump(vocab_dict, f)
        else:
            with open(dict_path, "rb") as f:
                vocab_dict = pickle.load(f)

        return vocab_dict

    def text2id(self, text_list, vocab_dict,  need_preprocess = True):
        """
        文本id化
        """
        if need_preprocess:
            pre = Preprocess()
            text_list = [pre.get_dl_input_by_text(text) for text in text_list]
        x = list(map(lambda d: word_tokenize(clean_str(d)), text_list))
        x_len = [len(text) for text in x]
        x = list(map(lambda d: list(map(lambda w: vocab_dict.get(w, vocab_dict["<unk>"]), d)), x))
        x = list(map(lambda d: d[:self.maxlen], x))
        x = list(map(lambda d: d + (self.maxlen - len(d)) * [vocab_dict["<pad>"]], x))
        return text_list, x, x_len

    def _get_embedding(self, vocab_dict):
        """get embedding vector by dict and embedding_file"""
        model = self._load_embedding_file(self.embedding_path)
        embedding = []
        dict_rev = {vocab_dict[word]:word for word in vocab_dict}
        for idx in range(len(vocab_dict)):
            word = dict_rev[idx]
            if word in model:
                embedding.append(model[word])
            else:
                embedding.append(self._get_rand_embedding())
        return tf.convert_to_tensor(np.array(embedding), tf.float32)

    def _get_rand_embedding(self):
        """random embedding"""
        return np.random.randn(self.size)

    def _load_embedding_file(self, path):
        """
        模型格式有两种bin和model，使用方式：
        a. bin模式：model = gensim.models.KeyedVectors.load_word2vec_format(model_path, binary=True)
        b. model模式：model = gensim.models.Word2Vec.load(model_path)
        model from https://www.jianshu.com/p/ae5b45e96dbf
        """
        model = gensim.models.KeyedVectors.load_word2vec_format(path,
                                                                binary=False)
        return model

if __name__ == '__main__':
    embedding = WordEmbedding()
