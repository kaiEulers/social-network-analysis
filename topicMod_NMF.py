#%% -----Imports
import numpy as np
from scipy import stats as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

#%%---------- Topic Modelling using Non-negative Matrix Factorisation(NMF)
# ----- Modelling topics for speeches made in the month of 2017-12
nTOPICS = 3
FILE_NAME = "ssm_cleaned_2017-12.csv"
data = pd.read_csv(f"data/{FILE_NAME}")

# Instantiate Tfidf model
tfidf = TfidfVectorizer(max_df=0.9, min_df=2, stop_words='english')
# Instantiate NMF model
nmf_model = NMF(n_components=nTOPICS)


# ----- Create document term matrix with tfidf model
dtm = tfidf.fit_transform(data['Speech'])

# ----- Extract topics from speeches using NMF
# Apply non-negative matrix factorisation on the document term matrix
nmf_model.fit(dtm)
# nmf_model.transform() returns a matrix with coefficients that shows how much each document belongs to each topic
topic_results_nmf = nmf_model.transform(dtm)

# Store top w words in dataframe topics_nmf
# Number of words that describes topic
w = 15
topics_nmf = pd.DataFrame()
for index,topic in enumerate(nmf_model.components_):
    # Negating an array causes the highest value to be the lowest value and vice versa
    topWordsIndex = (-topic).argsort()[:w]
    topics_nmf = topics_nmf.append(pd.Series([tfidf.get_feature_names()[i] for i in topWordsIndex]), ignore_index=True)
topics_nmf = topics_nmf.transpose()


# ----- Determine difference in coefficient such that speeches can be class as invovling have one or more topics
# Rank the topics that each speech is about
rank = []
for row in topic_results_nmf:
    rank.append(row.argsort())

# Find difference between coefficients
# Small difference means that speech involves 2 or more topics!
diff_12 = pd.Series(np.zeros(len(topic_results_nmf)))
diff_23 = pd.Series(np.zeros(len(topic_results_nmf)))

for i in range(len(topic_results_nmf)):
    # Extract top coefficients
    # max[0] contains the highest coefficient
    # max[1] contains the 2nd highest coefficient ...
    max = pd.Series(np.zeros(nTOPICS))
    for j in range(nTOPICS):
        max[j] = topic_results_nmf[i][rank[i][-j-1]]

    # Compute difference between highest and 2nd highest coeff
    diff_12[i] = max[0]-max[1]
    # Compute difference between 2nd highest and 3rd highest coeff
    diff_23[i] = max[1]-max[2]

# Concat all differences
diff = pd.concat([diff_12, diff_23], axis=1)
diff.columns = 'diff_12 diff_23'.split()


# ----- Determine threshold to class speeches as having more than one topic
SIG_LEVEL = 0.1
stats = diff.describe()
# Depending on the threshold of difference between coefficients, speeeches can be assigned to more than one topics
# thres_12 is the difference in coefficient between the highest and 2nd highest topic for speech to be considered to be about both topics. If the different is this value or less, speech will be about both topics.
# thres_12 is statistically determined, assuming that the difference in topic coefficient exhibits a normal distribution
# TODO: Empirically determine threshold (ie. sort all diff_12 and find the difference at 10% of the data)
mean_12 = stats['diff_12']['mean']
std_12 = stats['diff_12']['std']
coeffDiff_thres = std_12 * st.norm.ppf(SIG_LEVEL) + mean_12


# ----- Assign topic/s to each speech
topic_assigned_nmf = pd.Series(np.empty(len(topic_results_nmf)))
topic_assigned_nmf[:] = np.nan

for i in range(len(topic_results_nmf)):

    if diff_12[i] < coeffDiff_thres:
        topic_assigned_nmf[i] = np.nan
    else:
        topic_assigned_nmf[i] = topic_results_nmf[i].argmax()


# ----- Concat results
speeches = data['Speech']
results = data.drop('Speech', axis=1)
results["Topic_nmf"] = topic_assigned_nmf
results["Speech"] = speeches

# Remove speechs that contains two or more topics
results = results.dropna()

# Save results
results.to_csv(f"data/results/{re.sub('cleaned', 'results_NMF', FILE_NAME)}", index=False)


# ----- Analyse results from NMF topic modelling
# Check percentage of speechCount of each topic
# Expand topic_assigned into a list of all topics assigned
topicList = pd.Series()
for row in topic_assigned_nmf:
    topicList = topicList.append(pd.Series(row), ignore_index=True)

# Count total number of topics all speeches are involved in
analysis_nmf = pd.DataFrame(topicList.value_counts().sort_index(), columns='SpeechCount'.split())
analysis_nmf["Percentage"] = [round(cnt/sum(analysis_nmf["SpeechCount"]), 2) for cnt in analysis_nmf["SpeechCount"]]

# Concat analysis_nmf to topics_nmf
topics_nmf = topics_nmf.append(analysis_nmf["Percentage"])
topics_nmf = topics_nmf.append(analysis_nmf["SpeechCount"])
print(topics_nmf)

# Percentage of speeches with two and three similar topic coefficient values
num_thres = len(diff[diff['diff_12'] < coeffDiff_thres])
num_total = len(topic_results_nmf)
diff_perc = (num_thres) / num_total

print()
print(f'{round(diff_perc * 100, 2)}% of speeches have similar coeff values for their top two topics')

# Save topics and analysis_nmf
topics_nmf.to_csv(f"data/results/{re.sub('cleaned', 'topics_NMF', FILE_NAME)}")


#%% Plots
sns.set_style("darkgrid")
sns.set_context("notebook")

# ----- Plot distribution of coeff difference
fig = plt.figure(dpi=300)

plt.subplot(1, 2, 1)
ax1 = sns.distplot(diff['diff_12'], bins=5, kde=True, norm_hist=False)
plt.subplot(1, 2, 2)
ax2 = sns.distplot(diff['diff_23'], bins=5, kde=True, norm_hist=False)
plt.show()

# fig.savefig(f"/Users/kaisoon/Google Drive/Code/Python/COMP90055_project/figures/{re.sub('cleaned', 'hist_coeffDiff', FILE_NAME)}", dpi=300)
fig.savefig(f"figures/ssm_2017-12_coeffDiff.png", dpi=300)