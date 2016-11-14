from collections import OrderedDict

import numpy as np
import pandas as pd
import sklearn.metrics as skm

from .data import CPG_NAN
from .utils import get_from_module


def cor(y, z):
    return np.corrcoef(y, z)[0, 1]


def mad(y, z):
    return np.mean(np.abs(y - z))


def mse(y, z):
    return np.mean((y - z)**2)


def rmse(y, z):
    return np.sqrt(mse(y, z))


def rrmse(y, z):
    return 1 - rmse(y, z)


def auc(y, z, round=True):
    if round:
        y = y.round()
    if len(y) == 0 or len(np.unique(y)) < 2:
        return np.nan
    return skm.roc_auc_score(y, z)


def acc(y, z, round=True):
    if round:
        y = np.round(y)
        z = np.round(z)
    return skm.accuracy_score(y, z)


def tpr(y, z, round=True):
    if round:
        y = np.round(y)
        z = np.round(z)
    return skm.recall_score(y, z)


def tnr(y, z, round=True):
    if round:
        y = np.round(y)
        z = np.round(z)
    c = skm.confusion_matrix(y, z)
    return c[0, 0] / c[0].sum()


def mcc(y, z, round=True):
    if round:
        y = np.round(y)
        z = np.round(z)
    return skm.matthews_corrcoef(y, z)


def f1(y, z, round=True):
    if round:
        y = np.round(y)
        z = np.round(z)
    return skm.f1_score(y, z)


def cat_acc(y, z):
    return np.mean(y.argmax(axis=1) == z.argmax(axis=1))


CLA_METRICS = [auc, acc, tpr, tnr, f1, mcc]

REG_METRICS = [mse, mad, cor]

CAT_METRICS = [cat_acc]


def evaluate(y, z, mask=CPG_NAN, metrics=CLA_METRICS):
    y = y.ravel()
    z = z.ravel()
    if mask is not None:
        t = y != mask
        y = y[t]
        z = z[t]
    p = OrderedDict()
    for metric in metrics:
        p[metric.__name__] = metric(y, z)
    p['n'] = len(y)
    return p


def evaluate_cat(y, z, metrics=CAT_METRICS,
                 binary_metrics=None):
    idx = y.sum(axis=1) > 0
    y = y[idx]
    z = z[idx]
    p = OrderedDict()
    for metric in metrics:
        p[metric.__name__] = metric(y, z)
    if binary_metrics:
        for i in range(y.shape[1]):
            for metric in binary_metrics:
                p['%s_%d' % (metric.__name__, i)] = metric(y[:, i], z[:, i])
    p['n'] = len(y)
    return p


def get_output_metrics(output_name):
    if output_name.startswith('cpg'):
        metrics = CLA_METRICS
    elif output_name.startswith('bulk'):
        metrics = REG_METRICS + CLA_METRICS
    elif output_name in ['stats/diff', 'stats/mode', 'stats/cat2_var']:
        metrics = CLA_METRICS
    elif output_name == 'stats/mean':
        metrics = REG_METRICS + CLA_METRICS
    elif output_name == 'stats/var':
        metrics = REG_METRICS
    else:
        raise ValueError('Invalid output name "%s"!' % output_name)
    return metrics


def evaluate_outputs(outputs, preds):
    perf = []
    for output_name in outputs.keys():
        if output_name in ['stats/cat_var']:
            tmp = evaluate_cat(outputs[output_name],
                               preds[output_name],
                               binary_metrics=[auc])
        else:
            metrics = get_output_metrics(output_name)
            tmp = evaluate(outputs[output_name],
                           preds[output_name],
                           metrics=metrics)
        tmp = pd.DataFrame({'output': output_name,
                            'metric': list(tmp.keys()),
                            'value': list(tmp.values())})
        perf.append(tmp)
    perf = pd.concat(perf)
    perf = perf[['metric', 'output', 'value']]
    perf.sort_values(['metric', 'value'], inplace=True)
    return perf


def unstack_report(report):
    index = list(report.columns[~report.columns.isin(['metric', 'value'])])
    report = pd.pivot_table(report, index=index, columns='metric',
                            values='value')
    report.reset_index(index, inplace=True)
    report.columns.name = None

    # Sort columns
    columns = list(report.columns)
    sorted_columns = []
    for fun in CAT_METRICS + CLA_METRICS + REG_METRICS:
        for i, column in enumerate(columns):
            if column.startswith(fun.__name__):
                sorted_columns.append(column)
    sorted_columns = index + sorted_columns
    sorted_columns += [col for col in columns if col not in sorted_columns]
    report = report[sorted_columns]
    order = []
    if 'auc' in report.columns:
        order.append(('auc', False))
    elif 'mse' in report.columns:
        order.append(('mse', True))
    elif 'acc' in report.columns:
        order.append(('acc', False))
    report.sort_values([x[0] for x in order],
                       ascending=[x[1] for x in order],
                       inplace=True)
    return report


def get(name):
    return get_from_module(name, globals())
