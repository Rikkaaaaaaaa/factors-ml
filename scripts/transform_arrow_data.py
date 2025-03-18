import os.path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds

import glob

def save_15s_bars(date):
    tables = None
    data_path = './local_data/wind1/202311/factor_202311.csv'
    data = pd.read_csv(data_path, engine='pyarrow')
    data = data.query('date==@date')
    pq_name = data_path.split('/')[-1].split('.')[0]
    pq.write_table(pa.Table.from_pandas(data), f"./{pq_name}.parquet")


def save_all_factor_by_month(data_root, month, save_root='../local_parquet_factor'):
    for indus_type in range(1,12):
        for data_path in glob.glob(f'{data_root}/{month}/*data*{month}*indus_{indus_type}*'):
            data = pd.read_csv(data_path, engine='pyarrow')
            phase_name = data_path.split('/')[-1].split('_')[0]

            save_path = f"{save_root}/{month}"
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            save_path = f"{save_path}/{phase_name}_data_{month}_indus_{indus_type}.parquet"
            pq.write_table(pa.Table.from_pandas(data), save_path)
            print(f"file has been saved at {save_path}")

if __name__ == '__main__':
    #save_15s_bars(20231101)
    # read by batches
    data_path = '../local_parquet_factor/202311/test_data_202311_indus_1.parquet'
    dataset = ds.dataset(data_path)
    print(dataset.files)
    table = dataset.to_table()
    print(len(table))
    count = 0
    for batch in dataset.to_batches(batch_size=10000):
        print(len(batch))
        data = batch.to_pandas()
        print(data.head(3))
        count += len(batch)

    print('final', count)

    # save all factors by month
    #save_all_factor_by_month(data_root='../local_factor', month=202311)
