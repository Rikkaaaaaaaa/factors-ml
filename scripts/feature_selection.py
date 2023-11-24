import lightgbm as lgb
from lightgbm import plot_importance
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

exp_name = 'all_factor_lgbm_300s_highprice_hs300'
test_month = 202304
indus_type = 1
root = f'../experiments/{exp_name}/{test_month}'
model_path = f'{root}/ckpt/lgbm_indus{indus_type}.txt'

model = lgb.Booster(model_file=model_path)
fi = model.feature_importance()
fn = model.feature_name()

feature_importance = pd.DataFrame(data={'factor_name': fn, 'score': fi})
folder_path = f'{root}/feature_importance'
if not os.path.exists(folder_path):
    os.makedirs(folder_path)
feature_importance.to_csv(f'{folder_path}/{exp_name}_{test_month}_indus{indus_type}.csv')

# selection
max_num_features = min(model.num_feature(), 30)# only show 30
feature_importance = feature_importance.sort_values('score', ascending=False).iloc[:max_num_features, :]

# plot bar rank
#plot_importance(model, max_num_features=30, ax=ax)
fig, ax = plt.subplots(figsize=(16,12))
sns.barplot(data=feature_importance, x='score', y='factor_name',orient='h', ax=ax)
plt.title(f'{exp_name}_{test_month}_indus{indus_type}')
# plot data label
offset = 2 # for visual quality
for p in ax.patches:
    ax.text(p.get_width()+offset, p.get_y()+p.get_height()/2,
            '{:.1f}'.format(p.get_width()),
            va='center') # center text
plt.savefig(f'{folder_path}/{exp_name}_{test_month}_indus{indus_type}.jpg')
