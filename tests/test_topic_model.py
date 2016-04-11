# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import tempfile
import unittest

import numpy as np
from sklearn.decomposition import NMF, LatentDirichletAllocation, TruncatedSVD

from textacy.representations.vsm import build_doc_term_matrix
from textacy.texts import TextCorpus
from textacy.tm import TopicModel

class TopicModelTestCase(unittest.TestCase):

    def setUp(self):
        texts = ["Mary had a little lamb. Its fleece was white as snow.",
                 "Everywhere that Mary went the lamb was sure to go.",
                 "It followed her to school one day, which was against the rule.",
                 "It made the children laugh and play to see a lamb at school.",
                 "And so the teacher turned it out, but still it lingered near.",
                 "It waited patiently about until Mary did appear.",
                 "Why does the lamb love Mary so? The eager children cry.",
                 "Mary loves the lamb, you know, the teacher did reply."]
        textcorpus = TextCorpus.from_texts('en', texts)
        term_lists = [doc.as_terms_list(words=True, ngrams=False, named_entities=False)
                      for doc in textcorpus]
        self.doc_term_matrix, self.id2term = build_doc_term_matrix(
            term_lists,
            weighting='tf', normalize=False, sublinear_tf=False, smooth_idf=True,
            min_df=1, max_df=1.0, min_ic=0.0, max_n_terms=None)
        self.model = TopicModel('nmf', n_topics=5)
        self.model.fit(self.doc_term_matrix)
        self.tempdir = tempfile.mkdtemp(
            prefix='test_topic_model', dir=os.path.dirname(os.path.abspath(__file__)))

    def test_n_topics(self):
        for model in ['nmf', 'lda', 'lsa']:
            self.assertEqual(TopicModel(model, n_topics=20).n_topics, 20)

    def test_init_model(self):
        expecteds = (NMF, LatentDirichletAllocation, TruncatedSVD)
        models = ('nmf', 'lda', 'lsa')
        for model, expected in zip(models, expecteds):
            self.assertTrue(isinstance(TopicModel(model).model, expected))

    def test_save_load(self):
        filename = os.path.join(self.tempdir, 'model.pkl')
        expected = self.model.model.components_
        self.model.save(filename)
        tmp_model = TopicModel.load(filename)
        observed = tmp_model.model.components_
        self.assertEqual(observed.shape, expected.shape)
        self.assertTrue(np.equal(observed, expected).all())

    def test_transform(self):
        expected = (self.doc_term_matrix.shape[0], self.model.n_topics)
        observed = self.model.transform(self.doc_term_matrix).shape
        self.assertEqual(observed, expected)

    def test_get_doc_topic_matrix(self):
        expected = np.array([1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0])
        observed = self.model.get_doc_topic_matrix(self.doc_term_matrix,
                                                   normalize=True).sum(axis=1)
        self.assertTrue(np.equal(observed, expected).all())

    def test_get_doc_topic_matrix_nonnormalized(self):
        expected = self.model.transform(self.doc_term_matrix)
        observed = self.model.get_doc_topic_matrix(self.doc_term_matrix,
                                                   normalize=False)
        self.assertTrue(np.equal(observed, expected).all())

    def test_top_topic_terms_topics(self):
        self.assertEqual(
            len(list(self.model.top_topic_terms(self.id2term, topics=-1))),
            self.model.n_topics)
        self.assertEqual(
            len(list(self.model.top_topic_terms(self.id2term, topics=0))), 1)
        self.assertEqual(
            [topic_idx for topic_idx, _
             in self.model.top_topic_terms(self.id2term, topics=(1, 2, 3))],
            [1, 2, 3])

    def test_top_topic_terms_top_n(self):
        self.assertEqual(
            len(list(self.model.top_topic_terms(self.id2term, topics=0, top_n=10))[0][1]),
            10)
        self.assertEqual(
            len(list(self.model.top_topic_terms(self.id2term, topics=0, top_n=5))[0][1]),
            5)

    def test_top_topic_terms_weights(self):
        observed = list(self.model.top_topic_terms(self.id2term, topics=-1,
                                                   top_n=10, weights=True))
        self.assertTrue(isinstance(observed[0][1][0], tuple))
        for topic_idx, term_weights in observed:
            for i in range(len(term_weights) - 1):
                self.assertTrue(term_weights[i][1] >= term_weights[i+1][1])

    def tearDown(self):
        for fname in os.listdir(self.tempdir):
            os.remove(os.path.join(self.tempdir, fname))
        os.rmdir(self.tempdir)
