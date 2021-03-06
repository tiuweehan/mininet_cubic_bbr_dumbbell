import pandas as pd
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.model_selection import train_test_split
from sklearn.tree import export_graphviz
from sklearn.externals.six import StringIO
from sklearn import metrics
from pprint import pprint
import csv
from IPython.display import Image
import pydotplus
import statistics
import matplotlib
matplotlib.use('agg')
import seaborn as sns
import matplotlib.pyplot as plt
import math
import numpy as np
from mininet_iperf import convertSize
import sys
import collections

#expName = "tbf-exp-190403_205516"  # 10 Exp 1000 combinations(old)
#expName = "tbf-exp-190402_200224"  # 10 Exp 1000 combinations(old)
#expName = "tbf-exp-190421_030753"
#expName = "tbf-exp-190421_123813"
#expName = "tbf-exp-190421_190312" # 1s Exp 1000 combinations
#expName = "tbf-exp-190422_032331"  # 10 Exp 1000 combinations
#expName = "tbf-exp-190422_192316"  # 30s Exp 640 combinations
#expName = "tbf-exp-190425_164949" # 60s Exp 640 combiantions
#expName = "tbf-exp-190426_034928"

expName = "tbf-exp-190505_130854"
#expName = "lan"
#expName = "tbf-exp-190506_000828"

csvname = expName + "-DecisionTree.csv"

df = pd.read_csv(expName + ".csv", header=0)

bbrBw, cubicBw = {}, {}  # Store the goodput of each config
bbrLoss, cubicLoss = {}, {}
dTree = {}  # The decision of common configs

# Show the data size
rows, cols = df.shape
print('Data size: ' + str(df.shape))

# Class Label: 0->bbr, 1->cubic, 2->equal
label = {}
label['bbr'] = 0
label['cubic'] = 1
#label['equal'] = 2

features = ['Delay', 'BW', 'Limit']
featuresLabel = ['RTT', 'BW', 'BufSize']
error = []

limits = set()

# Get each config's Goodput/Retr values
def mapping():
    for i in range(rows):
        rowData = df.iloc[i]
        delay, bw, buf = rowData['Delay'], rowData['BW'], rowData['Limit']
        key = str(delay) + "-" + str(bw) + "-" + str(buf)
        limits.add(buf)

        if rowData['CC'] == 'bbr':
            bbrBw[key] = rowData['Goodput']
            bbrLoss[key] = rowData['Retr']
        elif rowData['CC'] == 'cubic':
            cubicBw[key] = rowData['Goodput']
            cubicLoss[key] = rowData['Retr']


# Make decisions
def treeCSV():
    commonKeys = []  # Use an array to ensure the order
    threshold = 0.00

    for key in bbrBw.keys():
        if key in cubicBw.keys():
            bBw, cBw = bbrBw[key], cubicBw[key]
            bLoss, cLoss = bbrLoss[key], cubicLoss[key]

            if not bBw or not cBw:
                continue
            
            commonKeys.append(key)
            diff = bBw - cBw
            diffPct = (bBw - cBw) / cBw * 100
            diffLoss = bLoss - cLoss
            
            # Record diff values in tuple
            tup = (bBw, cBw, diff, diffPct, bLoss, cLoss, diffLoss)

            if bBw > (1 + threshold) * cBw:
                dTree[key] = (label['bbr'], )
            elif cBw > (1 + threshold) * bBw:
                dTree[key] = (label['cubic'], )
            else:
                if bLoss <= cLoss:
                    dTree[key] = (label['bbr'], )
                else:
                    dTree[key] = (label['cubic'], )
            
            # dTree is decision followed by diff values
            dTree[key] += tup

    # Write to csv
    csvfile = open(csvname, 'w')
    writer = csv.writer(csvfile)
    header = features + ['Decision', 'bBw', 'cBw', 'diff', 'diffPct', 'bLoss', 'cLoss', 'diffLoss']
    writer.writerow(header)
    for key in commonKeys:
        record = []
        tokens = key.split('-')
        for i in range(len(tokens)):
            record.append(tokens[i])
        for j in range(len(dTree[key])):
            record.append(dTree[key][j])

        writer.writerow(record)

    csvfile.close()
    print('Decision tree nodes: ' + str(len(dTree)))


# Creating the decision tree (model)
def dtModel(filename, seed):
    df_Dtree = pd.read_csv(filename, header=0)
    
    X = df_Dtree[features]
    y = df_Dtree.Decision

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True, random_state=seed)
    clf = DecisionTreeClassifier(
            splitter='best',
            max_features=3,
            max_depth=4
            )

    clf = clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    
    print("Model accuracy: " + str(metrics.accuracy_score(y_test, y_pred)))
    error.append(metrics.accuracy_score(y_test, y_pred))
    return clf


# Plot the heatmaps
def plotHeatMap(filename, metric):
    #colors = ['RdBu_r', 'vlag', 'PuOr_r', 'coolwarm', 'bwr'] 
    for limit in limits:
        df_Dtree = pd.read_csv(filename, header=0)
        
        xMetric = 'Delay'
        yMetric = 'BW'

        # df_Dtree['BDP'] = ((df_Dtree.BW * 1e6 / 8) * (df_Dtree.Delay / 1000)).apply(alignWithBuf)
        df_Dtree['BDP'] = (df_Dtree.BW * 1e6 / 8) * (df_Dtree.Delay / 1000) 
        
        # Filter rows 
        df_Dtree_filtered = df_Dtree.loc[
                (df_Dtree['Limit'] == limit) & \
                (df_Dtree['Delay'] >= 5) & \
                #(df_Dtree['Delay'] <= 100) & \
                #(df_Dtree['BW'] <= 500) & \
                (df_Dtree['BW'] >= 10)
                ]
        
        # Create another dataframe for visualizing heatmap/scatter plot
        heatMapCols = [yMetric, xMetric, metric]
        heatMapDf = df_Dtree_filtered[heatMapCols]    
        
        # Heatmap Matrix
        mat = heatMapDf.pivot_table(index=yMetric, columns=xMetric, values=metric).sort_index(ascending=False)
        
        xlabel = [str(v) for v in mat.columns.values]
        ylabel = [str(v) for v in mat.index.values]
     
        vmin, vmax = min(heatMapDf[metric]), max(heatMapDf[metric])

        color = 'RdBu_r'        

        fig, ax = plt.subplots()
        sns.heatmap(mat, annot=True, fmt='.0f', cmap=color, square=True, cbar=False, 
            center=0, vmin=vmin, vmax=vmax, linewidths=0.1, linecolor='k', 
            xticklabels=xlabel, yticklabels=ylabel)
        plt.tight_layout()
        plt.xlabel(r'RTT (ms) $\rightarrow$', fontsize=20)
        plt.ylabel(r'Bandwidth (Mbps) $\rightarrow$', fontsize=20)
        plt.xticks(rotation=30, fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig('-'.join([expName, metric, 'buf', str(limit), 'Heatmap.png']), bbox_inches='tight')
        plt.close() 


# Plot
def plotTree(clf, seed):
    dot_data = StringIO()
    export_graphviz(clf, out_file=dot_data, proportion=False, node_ids=True,
                    filled=True, rounded=True, impurity=False, special_characters=True,
                    leaves_parallel=False,
                    feature_names=featuresLabel,
                    #class_names=['bbr', 'cubic', 'equal'],
                    class_names=['bbr', 'cubic']
                    )
    
    graph = pydotplus.graph_from_dot_data(dot_data.getvalue())
    
    graph.write_png(expName + '-' + str(seed) + '-DecisionTree.png')
    Image(graph.create_png())


# Check LAN results
def validateLAN(clf, lanFile):
    df = pd.read_csv(lanFile)
    rows, cols = df.shape

    cc = {}
    cc[0] = 'bbr'
    cc[1] = 'cubic'
    #cc[2] = 'equal'
    correct, total = 0, 0
    dic = collections.defaultdict(int)
    
    X, z = [], []
    for i in range(rows):
        rowData = df.iloc[i]
        buf, bw, rtt, lanRes= rowData['Limit'], rowData['BW'], rowData['Delay'], int(rowData['Decision']) 
        X.append([rtt, bw, buf])
        z.append(lanRes)
    
    # y is the Mininet Classification
    # z is the LAN decision
    y = clf.predict(X)    
    indices = clf.apply(X)
    
    for i in range(len(z)):
        if y[i] == z[i]:
            correct += 1
        else:
            #TODO log some information about wrong predictions
            dic[indices[i]] += 1
        total += 1

    print(correct, total)
    print(dic)
    accuracy = correct * 1.0 / total * 100
    print('Correctness: ' + str(accuracy) + '%')



if __name__ == "__main__":

    mapping()
    
    seeds = list(range(10))

    # Build decision tree and visualize
    for seed in seeds:
        print('\nRandom seed: ' + str(seed))
        
        treeCSV()
        clf = dtModel(filename=csvname, seed=seed)
        plotTree(clf=clf, seed=seed)
        validateLAN(clf, 'lan-DecisionTree.csv')

    plotHeatMap(filename=csvname, metric='diffPct')
    plotHeatMap(filename=csvname, metric='bLoss')
    plotHeatMap(filename=csvname, metric='cLoss')
    plotHeatMap(filename=csvname, metric='diffLoss')

    print(statistics.median(error))
    print(statistics.mean(error))

