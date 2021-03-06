import pytest
import numpy as np
import os
import pandas as pd
from pathlib import Path
import pyldl.mapping as pm
import xarray as xr

TEST_ROOT = Path(__file__).parent
RESOURCES = TEST_ROOT / 'resources'

infl = pd.DataFrame({'word'  :['walk','walk','walks','walked'],
                     'lemma' :['walk','walk','walk' ,'walk'  ],
                     'person':['1'   ,'2'   ,'1/2/3','3'     ],
                     'tense': ['pres','pres','pres' ,'past'  ]})

pars_to_ngram = [
    (1,True,True,  ['#','a','b']),
    (1,True,False, ['#','a','b']),
    (1,False,True, ['#','a','b','a','b','a','#']),
    (1,False,False,['#','#','a','a','a','b','b']),
    (2,True,True,  ['#a','ab','ba','a#']),
    (2,True,False, ['#a','a#','ab','ba']),
    (2,False,True, ['#a','ab','ba','ab','ba','a#']),
    (2,False,False,['#a','a#','ab','ab','ba','ba']),
    (3,True,True,  ['#ab','aba','bab','ba#']),
    (3,True,False, ['#ab','aba','ba#','bab']),
    (3,False,True, ['#ab','aba','bab','aba','ba#']),
    (3,False,False,['#ab','aba','aba','ba#','bab'])]
@pytest.mark.parametrize('gram, unique, keep_order, result', pars_to_ngram)
def test_to_ngram (gram, unique, keep_order, result):
    assert pm.to_ngram('ababa', gram=gram, unique=unique, keep_order=keep_order) == result

grams = [2,3]
diffs = [True, False]
pars = [ (i,j) for i in grams for j in diffs ]
pars = [ (i,*j) for i,j in enumerate(pars) ]
@pytest.mark.parametrize('ind, gram, diff', pars)
def test_gen_cmat (ind, gram, diff):
    _cmat = '{}/cmat_{:02d}.nc'.format(RESOURCES, ind)
    _cmat = xr.open_dataarray(_cmat)
    cmat = pm.gen_cmat(words=infl.word, gram=gram, differentiate_duplicates=diff)
    assert cmat.identical(_cmat)

frms = [None, 'word', 'lemma']
seps = [None, '/']
dims = [3, 5]
mns  = [0, 100]
sds  = [1, 100]
incl = [True, False]
difs = [True, False]
seds = [10]
pars_gen_smat_sim = [ (i,j,k,l,m,n,o,p) for i in frms for j in seps for k in dims for l in mns for m in sds for n in incl for o in difs for p in seds ]
pars_gen_smat_sim = pars_gen_smat_sim + [('word', '/', 5, 0, 1, True, True, None)]
pars_gen_smat_sim = [ (i,*j) for i,j in enumerate(pars_gen_smat_sim) ]
@pytest.mark.parametrize('ind, form, sep, dim_size, mn, sd, incl, diff, seed', pars_gen_smat_sim)
def test_gen_smat_sim (ind, form, sep, dim_size, mn, sd, incl, diff, seed):
    if (form is None) and (not incl):
        with pytest.raises(ValueError) as e_info:
            smat = pm.gen_smat_sim(infl, form, sep, dim_size, mn, sd, incl, diff, seed)
            assert e_info == 'Specify which column to drop by the argument "form" when "include_form" is False.'
    else:
        _smat = '{}/smat_sim_{:03d}.nc'.format(RESOURCES, ind)
        _smat = xr.open_dataarray(_smat)
        smat = pm.gen_smat_sim(infl, form, sep, dim_size, mn, sd, incl, diff, seed)
        if seed is None:
            assert not smat.identical(_smat)
        else:
            assert smat.identical(_smat)


def test_gen_fmat():
    cmat = pm.gen_cmat(infl.word, cores=1)
    smat = pm.gen_smat_sim(infl, form='word', sep='/', dim_size=5, seed=10)
    fmat = pm.gen_fmat(cmat, smat)
    _fmat = '{}/fmat.nc'.format(RESOURCES)
    _fmat = xr.open_dataarray(_fmat)
    assert fmat.identical(_fmat)

def test_gen_gmat():
    cmat = pm.gen_cmat(infl.word, cores=1)
    smat = pm.gen_smat_sim(infl, form='word', sep='/', dim_size=5, seed=10)
    gmat = pm.gen_gmat(cmat, smat)
    _gmat = '{}/gmat.nc'.format(RESOURCES)
    _gmat = xr.open_dataarray(_gmat)
    assert gmat.identical(_gmat)

cmat = pm.gen_cmat(infl.word, cores=1)
smat = pm.gen_smat_sim(infl, form='word', sep='/', dim_size=5, seed=10)
fmat = pm.gen_fmat(cmat, smat)
hmat = np.array(np.matmul(np.matmul(np.array(cmat),np.linalg.pinv(np.matmul(np.array(cmat).T,np.array(cmat)))),np.array(cmat).T))
hmat = xr.DataArray(hmat, coords={'word':cmat.word.values, 'wordc':cmat.word.values})
pars_gen_shat = [(1, cmat, fmat, None, None),
                 (2, cmat, None, smat, None),
                 (3, None, None, smat, hmat),
                 (4, None, fmat, smat, None)]
@pytest.mark.parametrize('ind, cmat, fmat, smat, hmat', pars_gen_shat)
def test_gen_shat (ind, cmat, fmat, smat, hmat):
    if ind==4:
        with pytest.raises(ValueError) as e_info:
            shat = pm.gen_shat(cmat, fmat, smat, hmat)
            assert e_info == '(C, F), (C, S), or (H, S) is necessary.'
    else:
        shat = pm.gen_shat(cmat, fmat, smat, hmat)
        _shat = '{}/shat.nc'.format(RESOURCES)
        _shat = xr.open_dataarray(_shat)
        if ind==3: # Rounding due to rounding errors when producing hmat.
            shat  = shat.round(10)
            _shat = _shat.round(10)
        assert shat.identical(_shat)


gmat = pm.gen_gmat(cmat, smat)
hmat = np.array(np.matmul(np.matmul(np.array(smat),np.linalg.pinv(np.matmul(np.array(smat).T,np.array(smat)))),np.array(smat).T))
hmat = xr.DataArray(hmat, coords={'word':smat.word.values, 'wordc':smat.word.values})
pars_gen_chat = [(1, smat, gmat, None, None),
                 (2, smat, None, cmat, None),
                 (3, None, None, cmat, hmat),
                 (4, None, gmat, cmat, None)]
@pytest.mark.parametrize('ind, smat, gmat, cmat, hmat', pars_gen_chat)
def test_gen_chat (ind, smat, gmat, cmat, hmat):
    if ind==4:
        with pytest.raises(ValueError) as e_info:
            chat = pm.gen_chat(smat, gmat, cmat, hmat)
            assert e_info == '(S, G), (S, C), or (H, C) is necessary.'
    else:
        chat = pm.gen_chat(smat, gmat, cmat, hmat)
        _chat = '{}/chat.nc'.format(RESOURCES)
        _chat = xr.open_dataarray(_chat)
        if ind==3: # Rounding due to rounding errors when producing hmat.
            chat  = chat.round(10)
            _chat = _chat.round(10)
        assert chat.identical(_chat)


