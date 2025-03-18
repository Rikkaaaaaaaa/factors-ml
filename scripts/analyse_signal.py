import numpy as np
import pandas as pd
import glob


def get_gru_signal(signal_root):
    signals = []

    for indus_type in range(1,12):
        for signal_path in glob.glob(f"{signal_root}/*indus{indus_type}*/*"):
            #print(signal_path)
            data = pd.read_csv(signal_path, engine='pyarrow')
            data['indus'] = indus_type

            signals.append(data)
    signals = pd.concat(signals)

    return signals

def get_gru_indus(signal_root):
    df_indus = pd.DataFrame(columns=['ticker', 'indus'])
    df_indus.set_index('ticker', inplace=True)
    for indus_type in range(1, 12):
        for signal_path in glob.glob(f"{signal_root}/*indus{indus_type}*/*"):
            # print(signal_path)
            ticker_name = signal_path.split('/')[-1].strip('.csv')
            df_indus.loc[ticker_name, 'indus'] = indus_type

    return df_indus



def get_signal(signal_root):
    signals = []
    for data_path in glob.glob(f"{signal_root}/*csv"):
        data = pd.read_csv(data_path, engine='pyarrow')
        signals.append(data)
    signals = pd.concat(signals)

    return signals


def compute_corr(signal1, signal1_col, signal2, signal2_col):
    merger_cols = ['ticker', 'date', 'time']
    signal1 = signal1[merger_cols + [signal1_col]]
    signal2 = signal2[merger_cols + [signal2_col]]
    merge_signal = signal2.merge(signal1, on=['ticker', 'date', 'time'])

    ticker_list = list(merge_signal.ticker.unique())
    corr = pd.DataFrame(columns=['ticker', 'corr'])
    corr['ticker'] = ticker_list
    corr.set_index('ticker', inplace=True)
    for ticker in ticker_list:
        ticker_signal = merge_signal.query('ticker==@ticker')
        ticker_corr = ticker_signal[[signal1_col]+[signal2_col]].corr()
        corr.loc[ticker, 'corr'] = ticker_corr.iloc[0,1]
    corr.reset_index(inplace=True)
    return corr

def compute_overlap(signal1, signal1_col, signal2, signal2_col):
    merger_cols = ['ticker', 'date', 'time']
    signal1 = signal1[merger_cols + [signal1_col]]
    signal2 = signal2[merger_cols + [signal2_col]]
    merge_signal = signal2.merge(signal1, on=['ticker', 'date', 'time'])

    ticker_list = list(merge_signal.ticker.unique())
    overlap = pd.DataFrame(columns=['ticker', 'overlap'])
    overlap['ticker'] = ticker_list
    overlap.set_index('ticker', inplace=True)
    for ticker in ticker_list:
        ticker_signal = merge_signal.query('ticker==@ticker')
        equal_num = (ticker_signal[signal1_col] == ticker_signal[signal2_col]).sum()
        overlap.loc[ticker, 'overlap'] = equal_num / len(ticker_signal)

        #overlap_num = (ticker_signal[signal1_col] == ticker_signal[signal2_col] & ticker_signal[signal1_col]!=0 & ticker_signal[signal2_col]!=0).sum()
        #overlap.loc[ticker, 'overlap_rate'] = overlap_num / len(ticker_signal)
    overlap.reset_index(inplace=True)
    return overlap


def main():
    '''
    main function 1
    '''
    res_path = './attn_gru_signal_analysis.xlsx'
    gru_signal_root = '/home/ciccinfra/Downloads/GRU_signal/gru_15s'
    thres_path = f"{gru_signal_root}/total_stats BIGRU_15s.csv"

    gru_signal_root = '/home/ciccinfra/Downloads/GRU_signal/gru_att_15s'
    thres_path = f"{gru_signal_root}/total_stats AttnBIGRU_15S.csv"


    gru_signal = get_gru_signal(gru_signal_root)
    df_indus = get_gru_indus(gru_signal_root)

    # change signal
    gru_signal.reset_index(inplace=True)
    threshold = pd.read_csv(thres_path)[['ticker', 'up_thres', 'down_thres']]
    for ticker in threshold.ticker.unique():
        _signal = gru_signal.query('ticker==@ticker')['prob'].copy()
        tmp_signal = np.zeros(len(_signal))
        up_thres = threshold.query('ticker==@ticker')['up_thres'].values[0]
        down_thres = threshold.query('ticker==@ticker')['down_thres'].values[0]
        tmp_signal[_signal>=up_thres] = 1
        tmp_signal[_signal<=down_thres] = -1
        gru_signal.loc[_signal.index, 'pred'] = tmp_signal



    ml_signal_root = "../experiments/batch4_factor_genetic_div_open_hs300_highprice_lgbm_15s/202311/signal"
    ml_signal = get_signal(ml_signal_root)

    lr_signal_root = "../experiments/batch4_factor_genetic_div_open_no_reverse_hs300_highprice_lr_15s/202311/signal"
    lr_signal = get_signal(lr_signal_root)

    gru_signal.rename(columns={'prob': 'gru_proba'}, inplace=True)
    gru_signal.rename(columns={'pred': 'gru_signal'}, inplace=True)

    ml_signal.rename(columns={'proba': 'ml_proba'}, inplace=True)
    ml_signal.rename(columns={'signal': 'ml_signal'}, inplace=True)

    lr_signal.rename(columns={'proba': 'lr_proba'}, inplace=True)
    lr_signal.rename(columns={'signal': 'lr_signal'}, inplace=True)

    # analysis ml and gru signal
    proba_corr = compute_corr(gru_signal, 'gru_proba', ml_signal, 'ml_proba')
    signal_corr = compute_corr(gru_signal, 'gru_signal', ml_signal, 'ml_signal')
    signal_overlap = compute_overlap(gru_signal, 'gru_signal', ml_signal, 'ml_signal')

    result = signal_corr.merge(signal_overlap, on=['ticker'])
    result = result.merge(df_indus, on=['ticker'])
    result['proba_corr'] = proba_corr['corr'].values

    writer = pd.ExcelWriter(res_path)
    result.to_excel(writer, sheet_name= 'gru_ml',index=False)
    result.groupby('indus').mean().to_excel(writer, sheet_name='gru_ml by indus', )
    result.mean().to_excel(writer, sheet_name='gru_ml mean value')

    # analysis lr and gru signal
    proba_corr = compute_corr(gru_signal, 'gru_proba', lr_signal, 'lr_proba')
    signal_corr = compute_corr(gru_signal, 'gru_signal', lr_signal, 'lr_signal')
    signal_overlap = compute_overlap(gru_signal, 'gru_signal', lr_signal, 'lr_signal')
    result = signal_corr.merge(signal_overlap, on=['ticker'])
    result = result.merge(df_indus, on=['ticker'])
    result['proba_corr'] = proba_corr['corr'].values
    # to excel
    result.to_excel(writer, sheet_name='gru_lr', index=False)
    result.groupby('indus').mean().to_excel(writer, sheet_name='gru_lr by indus')
    result.mean().to_excel(writer, sheet_name='gru_lr mean value')
    writer.save()


    # analysis lr and ml signal
    res_path = './lr_ml_signal_analysis.xlsx'
    proba_corr = compute_corr(lr_signal, 'lr_proba', ml_signal, 'ml_proba')
    signal_corr = compute_corr(lr_signal, 'lr_signal', ml_signal, 'ml_signal')
    signal_overlap = compute_overlap(lr_signal, 'lr_signal', ml_signal, 'ml_signal')

    writer = pd.ExcelWriter(res_path)
    result = signal_corr.merge(signal_overlap, on=['ticker'])
    result = result.merge(df_indus, on=['ticker'])
    result['proba_corr'] = proba_corr['corr'].values
    result.to_excel(writer, sheet_name= 'lr & ml',index=False)
    # group by indus
    result.groupby('indus').mean().to_excel(writer, sheet_name='by indus',  index=False)
    result.mean().to_excel(writer, sheet_name='mean value')
    writer.save()

if __name__ == '__main__':
    main()