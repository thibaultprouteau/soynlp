import os
from collections import namedtuple
from datetime import datetime

from soynlp.utils import DoublespaceLineCorpus, EojeolCounter, LRGraph, get_process_memory


installpath = os.path.abspath(os.path.dirname(__file__))
NounScore = namedtuple('NounScore', 'frequency score')


class LRNonuExtractor():
    def __init__(
        self,
        max_l_length=10,
        max_r_length=9,
        pos_features=None,
        neg_features=None,
        postprocessing=None,
        verbose=True,
        debug_dir=None,
    ):

        self.max_l_length = max_l_length
        self.max_r_length = max_r_length
        self.verbose = verbose
        self.debug_dir = debug_dir
        self.pos, self.neg, self.common = prepare_r_features(pos_features, neg_features)
        self.postprocessing = prepare_postprocessing(postprocessing)

        self.lrgraph = None

    @property
    def is_trained(self):
        return self.lrgraph is not None

    def extract(
        self,
        train_data=None,
        min_noun_score=0.3,
        min_noun_frequency=1,
        min_eojeol_frequency=1,
        min_eojeol_is_noun_frequency=30,
        extract_compounds=True
    ):
        if (not self.is_trained) and (train_data is None):
            raise ValueError('`train_data` must not be `None` if noun extractor has no LRGraph')

        if self.lrgraph is None:
            self.lrgraph = train_lrgraph(
                train_data, min_eojeol_frequency,
                self.max_l_length, self.max_r_length, self.verbose)

        candidates, nouns = extract_nouns(
            self.lrgraph, min_noun_score, min_noun_frequency,
            min_eojeol_is_noun_frequency, self.verbose)

        if extract_compounds:
            nouns = extract_compounds(candidates, nouns, self.verbose)

        nouns = postprocessing(nouns, self)
        nouns = {noun: NounScore(frequency, score) for noun, (frequency, score) in nouns.items()}
        return nouns


def prepare_r_features(pos_features=None, neg_features=None):
    """
    Check `pos_features` and `neg_features`
    If the argument is not defined, soynlp uses default R features

    Args:
        pos_features (collection of str)
        neg_features (collection of str)

    Returns:
        pos_features (set of str) : positive feature set excluding common features
        neg_features (set of str) : negative feature set excluding common features
        common_features (set of str) : feature appeared in both `pos_features` and `neg_features`
    """
    def load_features(path):
        with open(path, encoding='utf-8') as f:
            features = [line.strip() for line in f]
        features = {feature for feature in features if feature}
        return features

    default_feature_dir = f'{installpath}/pretrained_models/'

    if pos_features is None:
        pos_features = load_features(f'{default_feature_dir}/lrnounextractor.features.pos.v2')
    elif isinstance(pos_features, str) and (os.path.exists(pos_features)):
        pos_features = load_features(pos_features)

    if neg_features is None:
        neg_features = load_features(f'{default_feature_dir}/lrnounextractor.features.neg.v2')
    elif isinstance(neg_features, str) and (os.path.exists(neg_features)):
        neg_features = load_features(neg_features)

    if not isinstance(pos_features, set):
        pos_features = set(pos_features)
    if not isinstance(neg_features, set):
        neg_features = set(neg_features)

    common_features = pos_features.intersection(neg_features)
    pos_features = {feature for feature in pos_features if feature not in common_features}
    neg_features = {feature for feature in neg_features if feature not in common_features}
    return pos_features, neg_features, common_features


def print_message(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'[LRNounExtractor] {now}, mem={get_process_memory():.4} GB : {message}')


def prepare_postprocessing(postprocessing):
    # NotImplemented
    return postprocessing


def train_lrgraph(train_data, min_eojeol_frequency, max_l_length, max_r_length, verbose):
    if isinstance(train_data, LRGraph):
        if verbose:
            print_message('input is LRGraph')
        return train_data

    if isinstance(train_data, EojeolCounter):
        lrgraph = train_data.to_lrgraph(max_l_length, max_r_length)
        if verbose:
            print_message('transformed EojeolCounter to LRGraph')
        return lrgraph

    if isinstance(train_data, str) and os.path.exists(train_data):
        train_data = DoublespaceLineCorpus(train_data, iter_sent=True)

    eojeol_counter = EojeolCounter(
        sents=train_data,
        min_count=min_eojeol_frequency,
        max_length=(max_l_length + max_r_length),
        verbose=verbose
    )
    lrgraph = eojeol_counter.to_lrgraph(max_l_length, max_r_length)
    if verbose:
        print_message(f'finished building LRGraph from {len(eojeol_counter)} eojeols')
    return lrgraph


def extract_nouns(lrgraph, min_noun_score, min_noun_frequency, min_eojeol_is_noun_frequency, verbose):
    raise NotImplementedError


def extract_compounds(candidates, nouns, verbose):
    raise NotImplementedError


def postprocessing(nouns, lr_noun_extractor):
    raise NotImplementedError